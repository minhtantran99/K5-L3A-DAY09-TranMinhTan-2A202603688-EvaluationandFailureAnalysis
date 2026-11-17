"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math
    problems: list[str] = []

    # 1. any metric value in pr["metrics"] that is NaN or inf
    for m, v in pr.get("metrics", {}).items():
        if v is None:
            continue
        if isinstance(v, (int, float)):
            if math.isnan(v) or math.isinf(v):
                problems.append(f"metric {m} is NaN or inf ({v})")

    # 2. len(pr["rows"]) != manifest items x len(manifest seeds) (dropped / duplicated rows)
    items_count = pr.get("manifest", {}).get("items", 0)
    seeds_count = len(pr.get("manifest", {}).get("seeds", []))
    expected_count = items_count * seeds_count
    if len(pr.get("rows", [])) != expected_count:
        problems.append(f"row count {len(pr.get('rows', []))} != manifest items x seeds ({expected_count})")

    pr_item_seeds = [(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])]
    if len(pr_item_seeds) != len(set(pr_item_seeds)):
        problems.append("duplicate (item_id, seed) pairs found in pr rows")

    # 3. the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
    base_item_seeds = [(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])]
    if set(pr_item_seeds) != set(base_item_seeds):
        diff = set(pr_item_seeds) ^ set(base_item_seeds)
        problems.append(f"(item_id, seed) set differs from baseline ({len(diff)} difference(s))")

    # 4. pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is None
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s) recorded")

    graded_metrics = {m["id"] for m in spec.get("metrics", []) if m.get("grader") != "lab8.metrics.summarize" and m.get("kind") in ("safety", "capability")}
    for r in pr.get("rows", []):
        for m in graded_metrics:
            if m in r and r[m] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} has None for graded metric {m}")
                break
        else:
            continue
        break

    # 5. base_spec given and a threshold in spec is LOOSER than in base_spec for the same eval-set version
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        spec_metrics = {m["id"]: m for m in spec.get("metrics", [])}

        for b_id, b_m in base_metrics.items():
            if b_id not in spec_metrics:
                problems.append(f"metric {b_id} from base_spec is missing in spec")
            else:
                s_m = spec_metrics[b_id]
                if b_m.get("blocking") and not s_m.get("blocking"):
                    problems.append(f"metric {b_id} blocking was relaxed from True to False")
                b_th = b_m.get("threshold", {})
                s_th = s_m.get("threshold", {})
                if "max" in b_th and s_th.get("max", b_th["max"]) > b_th["max"]:
                    problems.append(f"metric {b_id} max threshold relaxed ({b_th['max']} -> {s_th.get('max')})")
                if "min" in b_th and s_th.get("min", b_th["min"]) < b_th["min"]:
                    problems.append(f"metric {b_id} min threshold relaxed ({b_th['min']} -> {s_th.get('min')})")
                if "max_increase" in b_th and s_th.get("max_increase", b_th["max_increase"]) > b_th["max_increase"]:
                    problems.append(f"metric {b_id} max_increase relaxed")
                if b_th.get("no_significant_drop") and not s_th.get("no_significant_drop"):
                    problems.append(f"metric {b_id} dropped no_significant_drop requirement")

        base_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        spec_slices = {s["name"]: s for s in spec.get("slices", [])}
        for b_name, b_s in base_slices.items():
            if b_name not in spec_slices:
                problems.append(f"slice {b_name} from base_spec is missing in spec")
            else:
                s_s = spec_slices[b_name]
                if b_s.get("blocking") and not s_s.get("blocking"):
                    problems.append(f"slice {b_name} blocking was relaxed")
                if "min" in b_s and s_s.get("min", b_s["min"]) < b_s["min"]:
                    problems.append(f"slice {b_name} min relaxed ({b_s['min']} -> {s_s.get('min')})")
                if b_s.get("no_significant_drop") and not s_s.get("no_significant_drop"):
                    problems.append(f"slice {b_name} dropped no_significant_drop requirement")

    # 6. an item's slice tags in PR rows differ from the baseline's (relabelling)
    base_slice_map: dict[str, set[str]] = {}
    for r in base.get("rows", []):
        base_slice_map[r.get("item_id")] = set(r.get("slices") or [])

    for r in pr.get("rows", []):
        item_id = r.get("item_id")
        if item_id in base_slice_map:
            if set(r.get("slices") or []) != base_slice_map[item_id]:
                problems.append(f"item {item_id} slices {r.get('slices')} differ from baseline {list(base_slice_map[item_id])}")
                break

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name = s["name"]
        metric = s.get("metric", "pass_rate")
        min_val = s.get("min")
        blocking = s.get("blocking", False)
        no_drop = s.get("no_significant_drop", False)

        pr_items = per_item(pr, metric, slice_name=name)
        val = (sum(pr_items.values()) / len(pr_items)) if pr_items else None

        verdict = "ok"
        note = ""
        th_dict = {k: s[k] for k in ("min", "no_significant_drop") if k in s}

        if val is None:
            verdict = "missing"
        elif min_val is not None and val < min_val:
            verdict = "fail"

        if no_drop and val is not None:
            base_items = per_item(base, metric, slice_name=name)
            keys = sorted(set(pr_items) & set(base_items))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        slice_id = f"slice:{name}/{metric}"
        if verdict != "ok" and blocking:
            blocked.append(slice_id)

        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if blocking else "warn")
        lines.append(f"  {slice_id:<22} {val!s:<8} {json.dumps(th_dict):<40} {note:<28} {label}")

    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
