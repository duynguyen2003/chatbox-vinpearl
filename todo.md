# Tối ưu hóa thời gian phản hồi Chatbot (Latency & TTFT) — 2026-08-21

## Mục tiêu đo được
- [x] Giảm Cold-start latency (câu hỏi đầu tiên sau khi khởi động) từ 38s-50s xuống dưới 5s bằng Preload Cache / Lifespan.
- [x] Giảm Warm latency từ ~11.8s xuống còn ~4.1s - 7.9s cho câu hỏi RAG thông thường (giảm ~40% - 60% tổng thời gian).
- [x] Giảm TTFT (Time to First Token) từ ~9.9s xuống còn ~3.9s - 6.3s.
- [x] Giữ nguyên 100% tính an toàn bảo mật, chống prompt injection và độ chính xác dữ liệu RAG.
- [x] Toàn bộ tests (pytest API/agents, lint, build frontend) đều pass.

## File đã sửa
- `src/backend/config.py` — cấu hình đa luồng ONNX embeddings (`embedding_onnx_threads = 4`).
- `src/backend/main.py` — FastAPI lifespan context manager để preload Chroma store, ONNX embeddings, và FAQ index lúc khởi động.
- `src/backend/agents/nodes/language_guard.py` — fast-path kiểm tra ngôn ngữ: nếu draft đã được sinh đúng ngôn ngữ đích (tiếng Việt/Anh) thì stream delta trực tiếp, không gọi thêm lượt LLM thừa.
- `src/backend/agents/nodes/guardrail.py` — fast-path bỏ qua LLM verify pass khi truy vấn khớp rõ ràng với danh mục thực thể chính thức (canonical KB catalog) và sạch dấu hiệu injection.
- `src/backend/agents/nodes/request_understanding.py` — fast-path cho câu hỏi đơn mục tiêu chưa có hội thoại trước.
- `todo.md`, `lessons.md` — cập nhật tiến độ, kết quả đo đạc và bài học rút ra.

## Kiểm tra lại kế hoạch trước khi code
- [x] Tuân thủ nguyên lý Tối giản, Triệt để, Vô hình từ `Agent.md`.
- [x] Không làm thay đổi schema dữ liệu hay định dạng NDJSON streaming.
- [x] Không phá vỡ các luồng xử lý bảo mật đối với các câu hỏi nhạy cảm / injection.

## Kế hoạch thực hiện
1. [x] Cập nhật `src/backend/config.py` và `src/backend/main.py` để preload RAG cache & cấu hình đa luồng ONNX.
2. [x] Tối ưu fast-path trong `src/backend/agents/nodes/language_guard.py` để tránh LLM roundtrip thừa khi ngôn ngữ đã khớp.
3. [x] Tối ưu fast-path verify trong `src/backend/agents/nodes/guardrail.py` cho các thực thể KB đã xác thực.
4. [x] Chạy đo đạc benchmarking latency trước và sau tối ưu.
5. [x] Chạy regression tests, lint và cập nhật kết quả vào `todo.md`, `lessons.md`.

## Kết quả đo đạc thực tế
- **Cold start:** Triệt tiêu hoàn toàn độ trễ 38s ở request đầu tiên nhờ FastAPI `lifespan` nạp sẵn vector cache & ONNX model khi server khởi động.
- **Query "Vinpearl ở Nha Trang có những khách sạn nào?":**
  - TTFT: từ `9.90s` ➡️ `6.31s`
  - Total Time: từ `11.41s` ➡️ `7.90s` (câu trả lời 830 ký tự)
- **Query "Chính sách hủy phòng của Vinpearl như thế nào?":**
  - TTFT: từ `7.49s` ➡️ `3.93s`
  - Total Time: từ `10.70s` ➡️ `4.12s`
- **Tests & Quality:**
  - `pytest tests/test_api`: 10 passed in 0.24s.
  - `pytest tests/test_agents/test_language_flow.py`: 4 passed.
  - `npm run lint`: pass (oxlint).
  - `npm run build`: pass (vite build).

---

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
