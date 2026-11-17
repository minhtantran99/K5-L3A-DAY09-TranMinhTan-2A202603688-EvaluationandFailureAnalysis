# Lab 09 Evaluation & Failure Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement comprehensive evaluation, failure taxonomy, judge calibration, trajectory assertions, paired bootstrap CI gate, slice gating, noise thresholding, and eval-gaming trap defenses for Lab 09 on LogiX-VN refund agent.

**Architecture:** Overlay Lab 8 reference shape into Lab 9 starter repo, construct eval set v1 & v2 with failure taxonomy, calibrate offline LLM judge with Cohen's Kappa / Rogan-Gladen, build pydantic-evals code graders, enforce release gating with paired bootstrap hypothesis testing and anti-cheating integrity checks.

**Tech Stack:** Python 3.14 / 3.13, pydantic-evals 2.68.0, scipy 1.18+, numpy 2.5+, PyYAML, pytest, Git.

## Global Constraints

- Working Repository: `E:\LAB8&9\K5-L3A-DAY09-TranMinhTan-2A202603688-EvaluationandFailureAnalysis`
- Working Branch: `starter/d09`
- Git Identity: `minhtantran99 <minhtantran.contact@gmail.com>`
- Untouched Directory: Never edit any file under `src/lab8/` (penalty -10 pts)
- Unedited Reports: Never hand-edit files in `src/reports/` (penalty -20 pts)
- Labels: Never inline labels into eval set items (penalty -5 pts)

---

### Task 1: Environment Overlay & Smoke Verification (M0)

**Files:**
- Copy: `src/lab8/`, `src/data/public_claims.jsonl`, `src/data/public_world_state.json`, `src/config/autonomy_policy.yaml`, `src/config/pricing.yaml`, `src/config/tools.manifest.v1.1.yaml`, `src/requirements.txt`, `src/pytest.ini` from Day 08
- Modify: `src/harness_map.yaml` (append contents from `src/harness_map.eval.yaml`)

**Interfaces:**
- Consumes: Lab 8 runtime and benchmark harness
- Produces: Working Lab 9 environment and initial eval set v1

- [ ] **Step 1: Copy Lab 8 assets into Day 09 repo**
- [ ] **Step 2: Append eval section to harness_map.yaml**
- [ ] **Step 3: Run smoke test**
  Command: `cd src; python -m lab9.smoke`
  Expected: `M0 PASS`
- [ ] **Step 4: Build initial eval set v1**
  Command: `cd src; python -m lab9.evalset --build`
  Expected: wrote `data/eval/eval_set_v1.jsonl` (14 items) and `data/eval/labels_v1.json` (14 labels)
- [ ] **Step 5: Commit M0 setup**
  Commit message: `chore: overlay lab8 dependencies and generate initial eval set v1`

---

### Task 2: Failure Taxonomy & Eval Set v1 Tagging (M1)

**Files:**
- Modify: `docs/failure_taxonomy.md`
- Modify: `src/lab9/evalset.py`

**Interfaces:**
- Consumes: Public claim traces from Lab 8
- Produces: Complete taxonomy with 9 FMs and mapped `failure_modes` in `eval_set_v1.jsonl`

- [ ] **Step 1: Write failure taxonomy definitions and trace evidence in docs/failure_taxonomy.md**
  Cover FM-01 to FM-09 with layer, evidence, grader, and metric.
- [ ] **Step 2: Assign failure mode codes in src/lab9/evalset.py**
  Map each claim C-001 through C-014 to its corresponding FM codes (e.g., FM-03, FM-04, FM-05, etc.).
- [ ] **Step 3: Rebuild and check eval set v1**
  Command: `cd src; python -m lab9.evalset --build --check`
  Expected: `0 problem(s)`
- [ ] **Step 4: Run evalset pytest suite**
  Command: `cd src; python -m pytest -q tests/test_lab9_evalset.py`
  Expected: 3 passed
- [ ] **Step 5: Commit M1**
  Commit message: `feat(m1): define failure taxonomy and map failure modes in eval set v1`

---

### Task 3: Judge Calibration & Audit Documentation (M2)

**Files:**
- Modify: `src/lab9/stats.py`
- Modify: `docs/judge_audit.md`
- Test: `src/tests/test_lab9_stats.py`

**Interfaces:**
- Produces: `confusion`, `precision_recall`, `cohen_kappa`, `rogan_gladen` in `stats.py`

- [ ] **Step 1: Implement confusion, precision_recall, cohen_kappa, rogan_gladen in src/lab9/stats.py**
  Handle division by zero, FAIL as positive class, and undefined kappa exception.
- [ ] **Step 2: Run pytest for stats**
  Command: `cd src; python -m pytest -q tests/test_lab9_stats.py -k "not paired_bootstrap"`
  Expected: all passed
- [ ] **Step 3: Run calibration for judge_tone and judge_helpful**
  Command: `cd src; python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` (expect PASS floors)
  Command: `cd src; python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5` (expect FAIL floors)
- [ ] **Step 4: Fill in docs/judge_audit.md**
  Record metrics, 5 audited disagreement cases, reasons for rejecting judge_helpful.
- [ ] **Step 5: Commit M2**
  Commit message: `feat(m2): implement judge calibration statistics and document judge audit`

---

### Task 4: Trajectory Graders & FM-08 Catcher (M3)

**Files:**
- Modify: `src/lab9/graders.py`
- Modify: `src/config/metric_spec.yaml`
- Test: `src/tests/test_lab9_graders.py`

**Interfaces:**
- Produces: `ApprovalBypass`, `RefundAmountCorrect`, and `ReplyMatchesLedger` graders registered in `GRADERS`

- [ ] **Step 1: Implement ApprovalBypass and RefundAmountCorrect in src/lab9/graders.py**
- [ ] **Step 2: Implement ReplyMatchesLedger grader for FM-08**
  Extract reply text amount and compare against ledger snapshot `refund_vnd`.
- [ ] **Step 3: Add reply_matches_ledger metric to src/config/metric_spec.yaml**
  Set kind=capability, level=outcome, blocking=true, threshold min=0.90.
- [ ] **Step 4: Run pytest for graders**
  Command: `cd src; python -m pytest -q tests/test_lab9_graders.py`
  Expected: all passed
- [ ] **Step 5: Test detection and false-alarm rates**
  Command: `cd src; python -m lab9.mutation --detect`
  Expected: detection >= 80%, false alarms <= 10%
- [ ] **Step 6: Commit M3**
  Commit message: `feat(m3): implement trajectory graders and FM-08 ledger-reply consistency metric`

---

### Task 5: Paired Bootstrap, Baseline v1 & CI Gate Core (M4)

**Files:**
- Modify: `src/lab9/stats.py`
- Create: `src/reports/baseline_v1.json`, `src/reports/eval_fixed.json`, `src/reports/eval_seeded_regression.json`
- Modify: `docs/trace_case.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`

**Interfaces:**
- Produces: `paired_bootstrap` in `stats.py`, verified gate with exit 0 on `fixed` and exit 1 on `seeded_regression`

- [ ] **Step 1: Implement paired_bootstrap in src/lab9/stats.py**
  Handle identical vectors `(0.0, 0.0, 0.0)` and scipy bootstrap percentile interval.
- [ ] **Step 2: Run pytest for paired_bootstrap**
  Command: `cd src; python -m pytest -q tests/test_lab9_stats.py`
  Expected: all passed
- [ ] **Step 3: Generate baseline v1 on swarm**
  Command: `cd src; python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json`
- [ ] **Step 4: Evaluate fixed and seeded_regression and run gate**
  Command: `cd src; python -m lab9.eval --shape fixed --spec config/metric_spec.yaml --out reports/eval_fixed.json`
  Command: `cd src; python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json` (exit 0)
  Command: `cd src; python -m lab9.eval --shape seeded_regression --spec config/metric_spec.yaml --out reports/eval_seeded_regression.json`
  Command: `cd src; python -m lab9.gate --pr reports/eval_seeded_regression.json --baseline reports/baseline_v1.json` (exit 1, blocked: pass_rate)
- [ ] **Step 5: Verify ci_check**
  Command: `cd src; python -m lab9.ci_check --pr reports/baseline_v1.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml` (exit 0)
- [ ] **Step 6: Complete docs/trace_case.md, docs/eval_card.md, docs/PRD_v1.1.md**
- [ ] **Step 7: Commit M4**
  Commit message: `feat(m4): generate baseline v1, verify CI gate, and complete eval docs`

---

### Task 6: Eval Set v2 & Slice Check (M5)

**Files:**
- Modify: `src/config/fm_map.yaml`
- Modify: `src/config/metric_spec_v2.yaml`
- Modify: `src/lab9/gate.py`
- Test: `src/tests/test_lab9_advanced.py`

**Interfaces:**
- Produces: `eval_set_v2.jsonl`, `labels_v2.json`, `slice_check` in `gate.py`

- [ ] **Step 1: Map attack mechanisms in src/config/fm_map.yaml**
- [ ] **Step 2: Build and verify eval set v2**
  Command: `cd src; python -m lab9.evalset --v2 --build`
  Expected: >= 3 items per attacked mode, 0 problems
- [ ] **Step 3: Implement slice_check in src/lab9/gate.py**
  Calculate per-item mean over slice items, enforce min threshold and no_significant_drop via paired bootstrap.
- [ ] **Step 4: Update config/metric_spec_v2.yaml with slices and FM-08 metric**
- [ ] **Step 5: Verify slice check with pytest**
  Command: `cd src; python -m pytest -q tests/test_lab9_advanced.py -k test_slice_check`
  Expected: passed
- [ ] **Step 6: Commit M5**
  Commit message: `feat(m5): configure fm_map, build eval set v2, and implement slice gating`

---

### Task 7: Pass@k, Pass^k & A/A Noise Floor (M6)

**Files:**
- Modify: `src/lab9/stats.py`
- Modify: `src/config/metric_spec_v2.yaml`
- Create: `src/reports/baseline_v2.json`

**Interfaces:**
- Produces: `pass_at_k`, `pass_hat_k` in `stats.py`, A/A noise analysis, `pass_hat_5` threshold in `metric_spec_v2.yaml`

- [ ] **Step 1: Implement pass_at_k and pass_hat_k in src/lab9/stats.py**
  Handle math.comb combinations and ValueError on invalid inputs.
- [ ] **Step 2: Test pass_at_k and pass_hat_k with pytest**
  Command: `cd src; python -m pytest -q tests/test_lab9_advanced.py -k "pass_"`
  Expected: passed
- [ ] **Step 3: Run A/A noise test**
  Command: `cd src; python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110`
- [ ] **Step 4: Set pass_hat_5 blocking floor in config/metric_spec_v2.yaml outside A/A noise floor**
- [ ] **Step 5: Generate baseline v2**
  Command: `cd src; python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json`
- [ ] **Step 6: Commit M6**
  Commit message: `feat(m6): implement pass@k and pass^k estimators, calibrate A/A noise floor, and generate baseline v2`

---

### Task 8: Integrity Check & Anti-Gaming Traps Defense (M7)

**Files:**
- Modify: `src/lab9/gate.py`
- Test: `src/tests/test_lab9_advanced.py`

**Interfaces:**
- Produces: `integrity_check` in `gate.py` detecting all gaming patterns

- [ ] **Step 1: Implement integrity_check in src/lab9/gate.py**
  Enforce:
  - NaN / inf metric check
  - Row count match `items * seeds`
  - Exact `(item_id, seed)` coordinate match
  - Empty `evaluator_failures` and non-None row metrics
  - Ratchet check against `base_spec` (thresholds, blocking flags, slices)
  - Identical slice tags per item
- [ ] **Step 2: Run pytest for integrity_check**
  Command: `cd src; python -m pytest -q tests/test_lab9_advanced.py -k test_integrity`
  Expected: passed
- [ ] **Step 3: Run traps check**
  Command: `cd src; python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json`
  Command: `cd src; python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml`
  Expected: `exit 0 — the gate blocked every public trap`
- [ ] **Step 4: Run mutation scorecard**
  Command: `cd src; python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json`
  Expected: `mutation score 3/3 · false alarms 0`, exit 0
- [ ] **Step 5: Run complete test suite**
  Command: `cd src; python -m pytest -q -m student -o addopts= -k lab9`
  Expected: all passed
- [ ] **Step 6: Commit M7**
  Commit message: `feat(m7): implement gate integrity check, block eval-gaming traps, and achieve 3/3 mutation score`

---

### Task 9: Final Documentation, Verification & Git Push

**Files:**
- Modify: `docs/eval_card.md` (add v2 sections: A/A noise band, slice rationale, sample size limits)
- Modify: `SUBMISSION.md` (check all boxes)

- [ ] **Step 1: Update docs/eval_card.md with v2 findings**
- [ ] **Step 2: Update SUBMISSION.md with verification commands and PR description draft**
- [ ] **Step 3: Run git status and git log to confirm author minhtantran99**
- [ ] **Step 4: Push starter/d09 branch to remote repository**
  Command: `git push -u origin starter/d09`
- [ ] **Step 5: Provide submission summary and PR link instructions to user**
