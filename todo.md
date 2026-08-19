# AI Streaming cho Chatbot — 2026-08-19

### File và kế hoạch

- `src/Frontend/components/SourcePills.jsx` — chuẩn hóa URL/nhãn và fallback an toàn.
- `src/Frontend/styles/components/StructuredMessage.css` — giới hạn chiều rộng, ellipsis.
- `tests/frontend_streaming_page_contract.mjs` — contract URL nguồn.
- [x] Cập nhật contract, lint/build/test và ghi kết quả.

### Kết quả kiểm tra

- Contract, lint, build và `git diff --check`: pass.
- Build vẫn có cảnh báo baseline JavaScript chunk lớn hơn 500 kB.
## Mục tiêu đo được

- [x] Thêm `POST /api/v1/chat/stream` trả NDJSON theo thứ tự `start/status/delta/final` hoặc `error`.
- [x] Giữ nguyên `POST /api/v1/chat` để tương thích và làm fallback.
- [x] Chatbot page và ChatWidget hiển thị câu trả lời tăng dần, không tạo message trùng.
- [x] Có nút dừng generation; request bị hủy khi đổi phiên hoặc component unmount.
- [x] StructuredMessage chỉ render sau event `final`; partial text dùng renderer an toàn.
- [x] ChatWidget có vùng đọc lớn hơn, cuộn nội dung độc lập và có link mở toàn màn hình.
- [x] Lint/build FE, test API/streaming và contract frontend đều pass.

## File dự kiến thêm/sửa

- `src/backend/api/routes.py` — endpoint streaming, auth/session và response headers.
- `src/backend/services/llm.py` — iterator token dùng LiteLLM streaming.
- `src/backend/agents/nodes/answer.py` — tách prompt và phát token qua callback theo request.
- `src/backend/services/chat_stream.py` — request-scoped event sink và NDJSON encoder.
- `src/backend/models/chat.py` — schema/type event nếu cần.
- `src/Frontend/services/api.js` — client đọc NDJSON và fallback API cũ.
- `src/Frontend/pages/Chatbot.jsx` — placeholder message, cập nhật delta, stop/final/error.
- `src/Frontend/components/ChatWidget.jsx` — cùng contract streaming và mở full chat.
- `src/Frontend/styles/pages/Chatbot.css`, `src/Frontend/styles/components/ChatWidget.css` — trạng thái streaming/stop và vùng đọc.
- `tests/test_api/test_chat_stream.py`, `tests/frontend_streaming_api.mjs`, `tests/frontend_streaming_page_contract.mjs` — regression tests.
- `todo.md`, `lessons.md` — kế hoạch, kết quả và bài học.

## Kiểm tra lại kế hoạch trước khi code

- [x] Branch `feature/ai-streaming` được tạo từ `integration/fe-be-ver002` sạch.
- [x] Dùng fetch streaming + NDJSON; không thêm WebSocket hoặc dependency frontend.
- [x] Không stream chain-of-thought, prompt, debug node hay dữ liệu nội bộ.
- [x] Không parse structured JSON dang dở; chỉ chuyển renderer khi nhận `final`.
- [x] Không sửa logic RAG/routing ngoài phần cần thiết để phát token.
- [x] Không xóa hoặc reset worktree cũ `D:\Demo-day\P-013`.

## Kế hoạch thực hiện

1. [x] Viết test contract backend/frontend ở trạng thái đỏ.
2. [x] Thêm primitive LLM token stream và event sink request-scoped.
3. [x] Thêm endpoint `/api/v1/chat/stream`, giữ nguyên endpoint cũ.
4. [x] Thêm client NDJSON có buffering, abort và fallback.
5. [x] Tích hợp Chatbot page, sau đó ChatWidget và UX vùng đọc.
6. [x] Chạy test, lint, build; sửa nguyên nhân gốc nếu có lỗi.
7. [x] Ghi kết quả và bài học; kiểm tra diff cuối.

## Giải thích thay đổi

- **Backend:** thêm event sink theo request và worker riêng để LiteLLM/LangGraph đồng bộ không chặn luồng gửi NDJSON. Chỉ language guard cuối phát token vì draft trước grounding chưa an toàn để hiển thị.
- **API:** endpoint stream xác thực quyền session trước khi gửi response header, không lộ exception nội bộ và giữ `/chat` cũ làm compatibility path.
- **Frontend client:** parser giữ buffer qua nhiều network chunk, giải mã Unicode streaming, gom delta trong 40 ms để tránh render mỗi token và chỉ fallback khi backend chắc chắn chưa có route.
- **Chat UI:** cập nhật đúng một assistant placeholder, dùng plain renderer trong lúc stream, chuyển structured renderer khi final, có Stop và không ép auto-scroll khi người dùng đang đọc phía trên.
- **Widget:** tăng vùng đọc theo viewport, để thread cuộn độc lập; form và link mở full chat luôn nhìn thấy.

## Kết quả kiểm tra

- Backend/API/LLM scoped tests: `15 passed` (bao gồm route cũ, stream event order, auth, language guard và LiteLLM delta).
- Frontend NDJSON + page/widget contract: pass.
- `npm run lint`: pass.
- `npm run build`: pass; còn cảnh báo baseline bundle lớn hơn 500 kB.
- Full pytest: `169 passed, 6 failed`; 6 lỗi baseline nằm ở graph fallback và scope destination tests, không có file streaming trong stack lỗi.
- Ruff chọn `E9,F,I`: pass; `git diff --check`: pass.
- Visual QA chưa chạy được vì phiên hiện tại không có in-app browser/Chrome được kết nối; không thay thế bằng browser tool ngoài skill đã chọn.
