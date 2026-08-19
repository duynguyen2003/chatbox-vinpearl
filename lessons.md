# Lessons Learned

## AI Streaming — 2026-08-19

- Không được phát token trực tiếp từ node `answer` khi graph còn grounding và language guard phía sau; người dùng có thể nhìn thấy draft sai hoặc bị bước sau sửa. Phát token từ language guard cuối giữ đúng ranh giới an toàn hiện tại.
- Retry provider sau khi đã phát token sẽ ghép hai câu trả lời và tạo nội dung trùng. Streaming chỉ được retry trước delta đầu tiên.
- NDJSON parser phải giữ phần dòng chưa hoàn chỉnh và dùng `TextDecoder` ở chế độ stream để không làm hỏng Unicode khi byte UTF-8 bị chia giữa hai chunk.
- Không tự động fallback sau lỗi mạng mơ hồ vì request đầu có thể đã được lưu; chỉ fallback khi server trả 404/405 cho endpoint stream.
- Auto-scroll mỗi delta làm người dùng không thể kéo lên đọc. Cần theo dõi khoảng cách tới cuối khung và chỉ tiếp tục auto-scroll khi người dùng vẫn đang ở gần đáy.
- Partial structured JSON/Markdown không ổn định cho renderer card. Trong lúc stream dùng renderer văn bản an toàn, sau event `final` mới chuyển sang `StructuredMessage`.
