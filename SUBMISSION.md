# Nộp bài (hạn 23:59 cùng ngày)
PR từ `starter/d09` → `main` của repo nhóm. Chấm commit cuối trước 23:59; commit sau hạn không tính.

## Core (nên xong trước 17:00)
- [x] `src/lab9/{stats,graders,evalset}.py` đã hoàn thành TODO M1–M4
- [x] `src/data/eval/eval_set_v1.jsonl` có `failure_modes`, `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `docs/trace_case.md` (1 case + regression test), `docs/judge_audit.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`
- [x] `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` (sinh bằng script)
- [x] `harness_map.yaml` có section `eval` (mẫu: `src/harness_map.eval.yaml`)
- [x] Job `eval-gate` xanh; dán output gate exit 1 của `seeded_regression` vào mô tả PR

## Advanced / Expert (tới 23:59)
- [x] `config/fm_map.yaml`, `config/metric_spec_v2.yaml` (slices, `pass_hat_5`, metric FM-08), `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check`
- [x] `src/data/eval/eval_set_v2.jsonl` + `labels_v2.json` (sinh bằng `evalset --v2 --build`)
- [x] `src/reports/baseline_v2.json` (sinh bằng script) → job `eval-gate-v2` chạy và xanh
- [x] Mô tả PR: output `lab9.mutation` (scorecard + `--aa`) và 4 dòng `exit 1` của các trap
- [x] `docs/eval_card.md` thêm mục v2: ngưỡng chọn từ A/A, slice nào bắt lỗi nào, và giới hạn cỡ mẫu (bug 1/3 seed không phát hiện ổn định với 5 seed)

---

## Mẫu nội dung dán vào mô tả Pull Request (PR Description)

### 1. Output gate exit 1 của `seeded_regression` (M4)
```text
gate: PR E-seeded_regression-20261117-4cf2 vs main E-swarm-20261117-4cf2 · eval set 4cf2c0aa896f
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.7857   {"min": 0.95, "no_significant_drop": true} Δ -0.200 CI [-0.414, +0.000] BLOCK
  reply_matches_ledger   0.7857   {"min": 0.95, "no_significant_drop": true} Δ -0.214 CI [-0.429, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
exit 1 — blocked: refund_amount_correct, reply_matches_ledger, pass_rate
```

### 2. Output `lab9.mutation` (Scorecard + A/A Noise) (M6)
```text
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
  fixed                expect merge got merge ok          
  honest_refactor      expect merge got merge ok          
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_matches_ledger, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

```text
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_matches_ledger          1.0        1.0  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

### 3. 4 dòng exit 1 của các traps qua gate (M7)
```text
$ python -m lab9.gate --pr reports/traps/evaluator_errors_as_nan.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
gate: PR E-slice_regression-20261117-471e vs main E-swarm-20261117-471e · eval set 471e280aaaef
  INTEGRITY row E-014@11 has None for graded metric pass_rate
exit 1 — blocked: integrity

$ python -m lab9.gate --pr reports/traps/dropped_failing_rows.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
gate: PR E-slice_regression-20261117-471e vs main E-swarm-20261117-471e · eval set 471e280aaaef
  INTEGRITY row count 131 != manifest items x seeds (140)
  INTEGRITY (item_id, seed) set differs from baseline (9 difference(s))
exit 1 — blocked: integrity

$ python -m lab9.gate --pr reports/traps/cherry_picked_seeds.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
gate: PR E-slice_regression-20261117-471e vs main E-swarm-20261117-471e · eval set 471e280aaaef
  INTEGRITY (item_id, seed) set differs from baseline (84 difference(s))
exit 1 — blocked: integrity

$ python -m lab9.gate --pr reports/traps/loosened_spec.json --baseline reports/baseline_v2.json --spec reports/traps/loosened_spec.spec.yaml --base-spec config/metric_spec_v2.yaml
gate: PR E-slice_regression-20261117-471e vs main E-swarm-20261117-471e · eval set 471e280aaaef
  INTEGRITY metric db_fact_kept min threshold relaxed (0.95 -> 0.65)
  INTEGRITY metric refund_amount_correct min threshold relaxed (0.9 -> 0.6)
  INTEGRITY metric refund_amount_correct dropped no_significant_drop requirement
  INTEGRITY metric pass_rate min threshold relaxed (0.85 -> 0.55)
  INTEGRITY metric pass_rate dropped no_significant_drop requirement
  INTEGRITY metric pass_hat_5 min threshold relaxed (0.8 -> 0.5)
  INTEGRITY metric reply_matches_ledger min threshold relaxed (0.9 -> 0.6)
  INTEGRITY metric reply_matches_ledger dropped no_significant_drop requirement
  INTEGRITY slice money_movement from base_spec is missing in spec
  INTEGRITY slice adversarial from base_spec is missing in spec
  INTEGRITY slice denial from base_spec is missing in spec
exit 1 — blocked: integrity
```
