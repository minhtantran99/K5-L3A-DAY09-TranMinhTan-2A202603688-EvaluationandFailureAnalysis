# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Đạt (κ=0.757 ≥ 0.6, P=0.857 ≥ 0.8, R=0.800 ≥ 0.7) | Dùng làm gate |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không đạt (κ=0.375 < 0.6, R=0.300 < 0.7) | Loại bỏ khỏi gate |

## ≥5 case audit thủ công (từ judge_tone)

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & Hành động sửa Rubric |
|---|---|---|---|---|---|
| 1 | H-008 (`Em đã hoàn tiền cho anh rồi nha, anh check giúp em.`) | PASS | FAIL | Người đúng | Quá suồng sã ("anh", "nha", "check giúp em"). Sửa rubric: định nghĩa rõ tính chuẩn mực, cấm từ ngữ thân mật tùy tiện. |
| 2 | H-017 (`Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha.`) | PASS | FAIL | Người đúng | Xưng hô "bạn ơi" + đuôi "nha" không phù hợp quy chuẩn dịch vụ khách hàng. Sửa rubric: bắt buộc dùng "Quý khách/anh/chị". |
| 3 | H-029 (`Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm.`) | PASS | FAIL | Người đúng | Giọng ra lệnh áp đặt ("không cần nhắn thêm") dù có từ lịch sự "Dạ, vui lòng". Sửa rubric: cấm các câu mệnh lệnh cộc cằn. |
| 4 | H-042 (`Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ.`) | FAIL | PASS | Người đúng | Câu ngắn gọn, lịch sự, đủ mốc thời gian rõ ràng. Judge phạt vì "thiếu xin lỗi". Sửa rubric: không bắt buộc xin lỗi hình thức nếu đã giải quyết xong. |
| 5 | H-051 (`Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ.`) | FAIL | PASS | Người đúng | Dùng từ "refund" là thuật ngữ kỹ thuật phổ biến được CS LogiX chấp nhận. Judge phạt vì chêm tiếng Anh. Sửa rubric: cho phép các thuật ngữ chuẩn như "refund". |

## Kết luận
- **Tiêu chí bị loại và lý do:** `judge_helpful` bị loại hoàn toàn khỏi release gate vì chỉ số thỏa thuận liên người đánh giá $\kappa = 0.375$ (dưới sàn 0.6) và độ nhạy $Recall = 0.300$ (dưới sàn 0.7). Ma trận nhầm lẫn cho thấy:
  `{'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70}`. Judge đã bỏ lọt tới 21/30 trường hợp câu trả lời kém chất lượng ($fn = 21$), tạo ra ảo tưởng an toàn nguy hiểm nếu đưa vào CI/CD (tỉ lệ lỗi quan sát chỉ 9% trong khi tỉ lệ lỗi thực tế theo Rogan-Gladen lên tới 30%).
- **Rủi ro còn lại:** Judge `judge_tone` chỉ mới được kiểm tra trên dữ liệu replay đã công khai (100 dòng); cần tiếp tục thu thập nhãn con người trên tập held-out mới độc lập từ người dùng thực tế trước khi áp dụng mở rộng.
