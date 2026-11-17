"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id("single", claim_id, seed)
    trace = Trace(run_id)

    claim = get_claim_view(conn, claim_id)
    budget.add_tool(tool_cost())
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    trace.add("claim", {"claim_id": claim_id, "order_id": claim.get("order_id")})

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        c = seen.get("claim") or {}
        if not c.get("order_id"):
            complete(budget, seed=seed, purpose="decide", prompt="missing_order_id")
            trace.add("react_step", {"action": "needs_info"})
            return {"final": {"status": "needs_info", "reason": "missing_order_id"}}

        last_tool = seen.get("last_tool")
        if not last_tool:
            complete(budget, seed=seed, purpose="decide", prompt=f"lookup_order:{c.get('order_id')}")
            trace.add("react_step", {"action": "lookup_order"})
            return {
                "tool": "lookup_order",
                "args": {"order_id": c.get("order_id"), "principal_id": c.get("principal_id")},
            }

        if last_tool == "lookup_order":
            order_view = seen.get("last_result") or {}
            trace.add(
                "lookup_order",
                {"visible": order_view.get("visible"), "reason": order_view.get("reason")},
            )
            if not order_view.get("visible"):
                complete(budget, seed=seed, purpose="decide", prompt="order_not_visible")
                trace.add("react_step", {"action": "escalated"})
                return {"final": {"status": "escalated", "reason": order_view.get("reason")}}

            order = order_view.get("order") or {}
            complete(budget, seed=seed, purpose="decide", prompt=f"compute_compensation:{order.get('order_id')}")
            trace.add("react_step", {"action": "compute_compensation"})
            return {"tool": "compute_compensation", "args": {"order": order}}

        if last_tool == "compute_compensation":
            quote_payload = seen.get("last_result") or {}
            trace.add("quote", quote_payload)
            proposal_val = int(quote_payload.get("amount_vnd", 0))
            complete(budget, seed=seed, purpose="decide", prompt=f"proposal={proposal_val}")
            if proposal_val <= 0:
                trace.add("react_step", {"action": "denied"})
                return {
                    "final": {
                        "status": "denied",
                        "proposal": 0,
                        "reason": quote_payload.get("reason"),
                    }
                }
            trace.add("react_step", {"action": "propose_refund"})
            return {
                "final": {
                    "status": "resolved",
                    "proposal": proposal_val,
                    "reason": None,
                }
            }

        return {"final": {"status": "failed", "error_reason": "unknown_state"}}

    # Bounded ReAct loop (max 8 steps, worker=True prevents write tools)
    outcome = run_react(
        conn,
        budget,
        observation={"claim": claim},
        decide=decide,
        max_steps=8,
        worker=True,
    )

    if outcome.get("stopped") == "step_cap":
        trace.add("error", {"reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = outcome.get("final") or {}
    status_candidate = final.get("status")
    proposal = int(final.get("proposal", 0))

    if status_candidate == "needs_info":
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason"),
        )

    if status_candidate == "escalated":
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason"),
        )

    if status_candidate == "denied" or proposal <= 0:
        complete(budget, seed=seed, purpose="draft", prompt="denied")
        trace.add("decision", {"status": "denied"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason"),
        )

    # After the loop, the host validates the quote and is the only writer
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    # TODO CP3 (student): truyền crash_at vào durability.issue_refund, không bắt InjectedCrash.
    try:
        refund_outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not refund_outcome["ok"]:
        status = "failed" if refund_outcome["conflict"] else "denied"
        trace.add("decision", {"status": status, "reason": refund_outcome["reason"]})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=refund_outcome["reason"],
        )

    trace.add("decision", {"status": "resolved", "proposal_amount": proposal})
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
