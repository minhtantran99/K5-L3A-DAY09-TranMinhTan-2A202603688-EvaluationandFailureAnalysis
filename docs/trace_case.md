# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261117-4cf2` |
| Triệu chứng | Grader Lab 8 fail: `status resolved != denied`; ledger ghi `refund_vnd=20000`, `refund_count=1` (kỳ vọng là 0); reply nói đã hoàn 20.000đ |
| Bước sai đầu tiên | Bước số 3: kind `model_override`, payload `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Bước 1 (handoff) và Bước 2 (investigator lookup_order) hoàn toàn đúng, DB trả về `delay_days: 0`. Bước 3 đã tin lời ticket ghi đè số ngày trễ từ 0 thành 5, dẫn tới quote sai ở Bước 4 |
| Failure mode | Mã `FM-03` (ticket_trust — tin ticket hơn DB) |
| Đối chứng | Cùng claim@seed trên shape `fixed`: không hề có event `model_override`, bước 3 tính quote thẳng ra 0đ (`no_entitlement`), từ chối hoàn tiền đúng nhãn |
| Regression test | Grader `DbFactKept` kiểm tra không có event `model_override`; bắt được fail trên `seeded_regression` và pass trên `fixed` |
| Chưa chắc chắn | Trace chỉ ghi nhận sự kiện `model_override`, chưa phản ánh được luồng suy luận nội tại (chain-of-thought) của model dẫn đến quyết định ghi đè |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
