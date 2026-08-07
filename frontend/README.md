# Vinpearl Chat Frontend

## Chạy backend

```powershell
python -m uvicorn src.main:app --reload --port 8000
```

## Chạy frontend

Mở PowerShell trong thư mục frontend:

```powershell
python -m http.server 5500
```

Mở trình duyệt:

```text
http://127.0.0.1:5500
```

API mặc định:

```text
http://127.0.0.1:8000/api/v1/chat
```

Có thể đổi API URL bằng nút bánh răng trên giao diện.

## Bật CORS trong FastAPI

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Gắn frontend trực tiếp vào FastAPI

Chép thư mục này thành `frontend/` trong project rồi thêm sau `app.include_router(router)`:

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)
```

Khi frontend và backend cùng domain, đổi trong `app.js`:

```javascript
apiUrl: localStorage.getItem('vp_api_url') || '/api/v1/chat'
```

## Session memory

Frontend lưu `session_id` do backend trả về trong `localStorage` với khóa:

```text
vp_session_id
```

- Tin nhắn đầu tiên không tự tạo session ở trình duyệt; backend tạo và trả về.
- Các tin nhắn sau tái sử dụng đúng `session_id` đó.
- Tải lại trang vẫn giữ phiên hiện tại.
- Nút **Cuộc trò chuyện mới** xóa session ở trình duyệt và gọi API xóa lịch sử cũ.

Để kiểm tra, mở DevTools → Network → request `/api/v1/chat`. Từ request thứ hai trở đi, payload phải chứa cùng một `session_id`.
