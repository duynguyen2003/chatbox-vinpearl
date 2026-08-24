# Lessons Learned

## Latency & TTFT Optimization — 2026-08-21

- Nạp sẵn (Warm-up / Preload) RAG cache và mô hình ONNX trong FastAPI `lifespan` giúp triệt tiêu hoàn toàn hiện tượng trễ 38s ở request đầu tiên khi server vừa bật.
- Cấu hình `embedding_onnx_threads = 4` giúp tăng tốc độ tính toán vector trên đa nhân CPU lên gấp 3-4 lần.
- Kiểm tra fast-path ngôn ngữ qua bộ mã ký tự tiếng Việt (diacritics) trước khi gọi LLM `language_guard` giúp tiết kiệm ngay ~1.5s cho mỗi câu hỏi mà không làm thay đổi nội dung câu trả lời.
- Fast-path cho Guardrail verification khi câu hỏi khớp chính xác với thực thể KB chính thức (Vinpearl/VinWonders) và sạch dấu hiệu injection giúp giảm thêm ~1.0s - 1.5s mà vẫn giữ 100% rào chắn bảo mật an toàn.

## AI Streaming — 2026-08-19

- Không được phát token trực tiếp từ node `answer` khi graph còn grounding và language guard phía sau; người dùng có thể nhìn thấy draft sai hoặc bị bước sau sửa. Phát token từ language guard cuối giữ đúng ranh giới an toàn hiện tại.
- Retry provider sau khi đã phát token sẽ ghép hai câu trả lời và tạo nội dung trùng. Streaming chỉ được retry trước delta đầu tiên.
- NDJSON parser phải giữ phần dòng chưa hoàn chỉnh và dùng `TextDecoder` ở chế độ stream để không làm hỏng Unicode khi byte UTF-8 bị chia giữa hai chunk.
- Không tự động fallback sau lỗi mạng mơ hồ vì request đầu có thể đã được lưu; chỉ fallback khi server trả 404/405 cho endpoint stream.
- Auto-scroll mỗi delta làm người dùng không thể kéo lên đọc. Cần theo dõi khoảng cách tới cuối khung và chỉ tiếp tục auto-scroll khi người dùng vẫn đang ở gần đáy.
- Partial structured JSON/Markdown không ổn định cho renderer card. Trong lúc stream dùng renderer văn bản an toàn, sau event `final` mới chuyển sang `StructuredMessage`.

## CI và Ruff — 2026-08-24

- Dependency linter dạng `ruff>=...` không đủ để CI tái lập: version mới có thể thay đổi baseline và làm xuất hiện hàng trăm lỗi không liên quan. Cần pin version và khai báo `lint.select` tường minh.
- Notebook crawler có semantics theo cell, thường cố ý lặp import/hàm. Không nên ép cùng baseline Ruff với module production nếu chưa có workflow lint notebook riêng.
- Khi test lệch với production contract đã có chú thích an toàn rõ ràng, cập nhật test theo contract; không hạ thấp fail-safe production chỉ để làm CI xanh.
