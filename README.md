# P-013 — Vinpearl Multilingual Travel Agent

## LINK ARCHITECTURE DIAGRAM

https://docs.google.com/document/d/1R3XtwiKt8Pi7U_XpSM57luqbYPXar0SjAWXT3rkGi4Q/edit?usp=sharing

## LINK SCHEMAS

https://docs.google.com/document/d/16cShLOudthj6GhOQR3O3OCOQw256Ucpg9pu6E7KQSgY/edit?tab=t.0#heading=h.xaz1qb3z4105

## LINK DEPLOY
https://frontend-production-48c1.up.railway.app/\

## LINK VIDEO DEMO
https://drive.google.com/drive/folders/1fvTKIMYq9dfHjMOreMvhl0TB5pmFCzdV

## LNIK WORKFLOW
https://docs.google.com/document/d/1kOYRXs0noKdzSWT_Hqm0gXm0XnzzzgErYjTdLjcHwIs/edit?tab=t.wi74v9yh9pbt

## 1. Setup môi trường local

### Tạo virtual environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
```

### Cài dependencies

```powershell
python -m pip install -r requirements.txt 
```

---

## 2. PostgreSQL

### Kiểm tra ORM metadata

```powershell
python -c "from src.db import Base; print(len(Base.metadata.tables)); print(list(Base.metadata.tables.keys()))"
```

### Tạo PostgreSQL user

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -U postgres `
  -c "CREATE USER vinpearl WITH PASSWORD '<POSTGRES_PASSWORD>';"
```

> Nếu user `vinpearl` đã tồn tại thì bỏ qua bước này. Mật khẩu thật nên lấy từ `.env`, không ghi trực tiếp vào README khi commit Git.

### Kiểm tra migration hiện tại

```powershell
alembic current
```

### Chạy migrations

```powershell
alembic upgrade head
```

### Seed destination data

```powershell
python -m scripts.seed_destinations
```

### Load dữ liệu Core vào PostgreSQL

```powershell
python -m scripts.load_core
```

---

## 3. Tạo Chroma Vector Store từ PostgreSQL

Sau khi PostgreSQL đã có dữ liệu:

```powershell
python -m src.backend.services.ingest_postgres --reset
```

Lệnh này sẽ đọc dữ liệu business từ PostgreSQL, chunk dữ liệu, tạo embedding, ghi vectors vào Chroma và lưu tại `storage/chroma_local`.

---

## 4. Chạy Backend FastAPI local

```powershell
python -m uvicorn src.backend.main:app --reload --port 8000
```

Backend local:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Health check:

```text
GET /health
```

Readiness check:

```text
GET /ready
```

---

## 5. Chạy Frontend local

Nếu frontend nằm tại `src/frontend`:

```powershell
cd D:\vinuni\T013\main\P-013\src\frontend
npm install
npm run dev
```

Frontend thường chạy tại:

```text
http://localhost:5173
```

Frontend gọi backend thông qua:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 6. Tạo Admin đầu tiên

Lấy giá trị `ADMIN_BOOTSTRAP_KEY` từ `.env`.

```powershell
$body = @{
  name = "P013 Admin"
  email = "admin@example.com"
  phone = $null
  password = "ChangeThisPassword123!"
  locale = "vi"
  bootstrap_key = "LAY_ADMIN_BOOTSTRAP_KEY_TRONG_ENV"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/auth/bootstrap-admin" `
  -ContentType "application/json" `
  -Body $body
```

Sau khi tạo admin thành công:

```text
/admin/staff
```

---

## 7. Docker

Project đã đóng gói Backend + Redis bằng Docker.

### Build image

```powershell
docker compose build
```

Image backend:

```text
p-013-agent:latest
```

### Chạy Docker Compose

```powershell
docker compose up
```

Kiến trúc local hiện tại:

```text
Frontend Vite
     |
     v
FastAPI Backend (Docker)
     |
     +--> PostgreSQL trên Windows host
     |
     +--> Redis container
     |
     +--> Chroma Docker Volume
```

PostgreSQL Windows được container truy cập bằng:

```text
host.docker.internal:5432
```

Redis được backend truy cập bằng:

```text
redis://redis:6379/0
```

Chroma trong Docker dùng:

```text
/app/storage/chroma_local
```

---

## 8. Kiểm tra Docker

### Health

```powershell
python -c "import httpx; r=httpx.get('http://localhost:8000/health'); print(r.status_code); print(r.text)"
```

Kỳ vọng:

```text
200
{"status":"ok"}
```

### Ready

```powershell
python -c "import httpx; r=httpx.get('http://localhost:8000/ready'); print(r.status_code); print(r.text)"
```

Kỳ vọng:

```text
200
{"status":"ready"}
```

### Test Agent API

Có API key:

```powershell
python -c "import httpx; r=httpx.post('http://localhost:8000/ask', headers={'X-API-Key':'dev-local-secret-key'}, json={'question':'Xin chào'}); print(r.status_code); print(r.text)"
```

Kỳ vọng HTTP `200` và response có `answer` cùng `session_id`.

---

## 9. Biến môi trường

### `.env`

Dùng cho môi trường local.

Ví dụ:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-3.5-flash-lite

LOCAL_EMBEDDING_MODEL=intfloat/multilingual-e5-small
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=128

DATABASE_URL=postgresql+pg8000://vinpearl:<POSTGRES_PASSWORD>@localhost:5432/vinpearl

CHROMA_DIR=./storage/chroma_local
CHROMA_COLLECTION=vinpearl_multilingual_e5_small

VITE_API_BASE_URL=http://localhost:8000

ADMIN_BOOTSTRAP_KEY=<ADMIN_BOOTSTRAP_KEY>
AGENT_API_KEY=dev-local-secret-key
```

> Không commit `.env` có secret thật lên GitHub.

### `.env.railway.example`

Chỉ là file mẫu tham khảo cho Railway.

- Không dùng trực tiếp cho local
- Không chứa secret thật
- Khi deploy Railway sẽ khai báo Variables trên Railway Dashboard

---

## 10. Các lệnh thường dùng

### Setup đầy đủ từ đầu

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

alembic current
alembic upgrade head

python -m scripts.seed_destinations
python -m scripts.load_core

python -m src.backend.services.ingest_postgres --reset
```

### Chạy backend không Docker

```powershell
python -m uvicorn src.backend.main:app --reload --port 8000
```

### Chạy Docker

```powershell
docker compose build
docker compose up
```

### Dừng Docker

```powershell
docker compose down
```

---


## 11. Deploy Railway

Project hiện đã được triển khai trên Railway với các service:

- Backend FastAPI
- Frontend React/Vite
- PostgreSQL
- Redis
- Railway Volume cho Chroma Vector Store

### Backend Railway

Public Backend URL:

```text
https://backend-production-9576.up.railway.app
```

Swagger:

```text
https://backend-production-9576.up.railway.app/docs
```

Readiness check:

```text
https://backend-production-9576.up.railway.app/ready
```

Kỳ vọng:

```json
{"status":"ready"}
```

Backend sử dụng `Dockerfile` ở root project.

`railway.toml` cho Backend:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/ready"
healthcheckTimeout = 180
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

Backend Railway cần cấu hình các Variables tương ứng với môi trường production. Các secret như API key, database password và bootstrap key không ghi trực tiếp vào README.

Một số biến production đang sử dụng:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-3.5-flash-lite

LOCAL_EMBEDDING_MODEL=intfloat/multilingual-e5-small
EMBEDDING_BACKEND=onnx_int8
EMBEDDING_ONNX_FILE=onnx/model_qint8_avx512_vnni.onnx
EMBEDDING_ONNX_PROVIDER=CPUExecutionProvider
EMBEDDING_ONNX_THREADS=1
EMBEDDING_BATCH_SIZE=4
EMBEDDING_MAX_LENGTH=512

CHROMA_DIR=/app/storage/chroma_local
CHROMA_COLLECTION=vinpearl_multilingual_e5_small_prod

TOP_K=5
MIN_RELEVANCE_SCORE=0.35

RAILWAY_RUN_UID=0
```

Database và Redis được cấu hình bằng Railway Variables / service references, không hard-code credential production trong source.

### Railway PostgreSQL

Dữ liệu PostgreSQL local đã được migrate lên Railway PostgreSQL.

Backend production sử dụng PostgreSQL Railway thông qua `DATABASE_URL`.

Alembic migration được chạy khi Backend khởi động để đồng bộ schema:

```powershell
alembic upgrade head
```

Có thể kiểm tra migration hiện tại:

```powershell
alembic current
```

### Railway Redis

Redis được triển khai thành service riêng trên Railway.

Backend production kết nối Redis thông qua Railway internal networking / Variables.

### Railway Volume cho Chroma

Chroma Vector Store production được lưu tại:

```text
/app/storage/chroma_local
```

Collection production:

```text
vinpearl_multilingual_e5_small_prod
```

Collection production đã được ingest từ PostgreSQL và hiện chứa dữ liệu RAG dùng bởi Backend.

Khi cần ingest lại Chroma trên Railway:

```powershell
python -m src.backend.services.ingest_postgres --reset
```

Không nên chạy `--reset` trên production nếu chưa xác định đúng `CHROMA_COLLECTION`.

### Frontend Railway

Public Frontend URL:

```text
https://frontend-production-4ca5.up.railway.app
```

Frontend production sử dụng:

```env
VITE_API_BASE_URL=https://backend-production-9576.up.railway.app
```

`VITE_API_BASE_URL` là biến build-time của Vite. Nếu thay đổi giá trị trên Railway thì cần rebuild/redeploy Frontend.

Frontend sử dụng `Dockerfile.frontend`.

Ví dụ `railway.frontend.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.frontend"

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 180
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

Frontend service cần trỏ Config-as-code tới:

```text
/railway.frontend.toml
```

### CORS giữa Frontend và Backend

Do Frontend và Backend chạy trên hai domain Railway khác nhau, Backend phải cho phép Frontend origin.

Biến Backend:

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://frontend-production-4ca5.up.railway.app
```

Không thêm dấu `/` ở cuối origin.

CORS được đọc từ:

```text
src/backend/config.py
src/backend/main.py
```

và áp dụng bằng `CORSMiddleware`.

### Kiểm tra API production

Swagger:

```text
https://backend-production-9576.up.railway.app/docs
```

Ví dụ API đăng ký user:

```text
POST /api/v1/auth/register
```

Response đăng ký thành công:

```text
201 Created
```

Ví dụ test RAG production:

```json
{
  "message": "VinWonders Phú Quốc có gì?",
  "session_id": "test-session",
  "user_id": "admin"
}
```

Response thành công có thể gồm:

```text
route = rag
language = vi
sources != []
```

### Quy trình deploy sau khi sửa source

Sau khi test local:

```powershell
git status
git add .
git commit -m "update deployment"
git push
```

Railway sẽ build/deploy lại service tương ứng nếu service đang theo dõi branch Git hiện tại.

Nếu thay đổi Backend:

1. Railway build Backend image.
2. Backend chạy migration nếu entrypoint đã cấu hình `alembic upgrade head`.
3. Healthcheck `/ready` phải trả `200`.
4. Kiểm tra Swagger và API cần thiết.

Nếu thay đổi Frontend:

1. Railway build bằng `Dockerfile.frontend`.
2. Vite sử dụng `VITE_API_BASE_URL` tại build-time.
3. Healthcheck `/` phải thành công.
4. Kiểm tra Frontend gọi được Backend và không bị lỗi CORS.

---

```

## Giải thích luồng

1. `load_conversation_memory`: tải các lượt hội thoại gần đây và context đã lưu của session hiện tại.
2. `enforce_input_guardrail`: kiểm tra an toàn, phạm vi và làm sạch request trước khi cho đi tiếp.
   - `safety_action = block` → `sensitive_content_response`.
   - `scope_action != allow` → `out_of_scope_response`.
   - Còn lại → `detect_language_and_translate`.
3. `detect_language_and_translate`: xác định ngôn ngữ trả lời, tạo `rag_query`, coarse route và safety decision.
   - Nếu `safety_action = block` → `sensitive_content_response`.
   - Còn lại → `resolve_conversation_context`.
4. `resolve_conversation_context`: giải quyết destination/entity/reference dựa trên message hiện tại và memory.
5. `classify_input`: xác định `route`.
   - `greeting` → `greeting_response`.
   - `conversation_context` → `conversation_context_response`.
   - `out_of_scope` → `out_of_scope_response`.
   - `rag` → `retrieve_context`.
6. `retrieve_context`: lấy evidence/context từ RAG cho câu hỏi.
7. `analyze_support_request`: phân loại support.
   - `resolution_mode = human_required` → `create_ticket`.
   - Còn lại → `assess_information`.
8. `assess_information`: đánh giá evidence có đủ để trả lời hay không.
9. `route_after_assessment`:
   - `resolution_mode = human_required` → `create_ticket` (fail-safe có khai báo trong graph).
   - `enough_information = true` → `generate_answer`.
   - Còn lại → `no_data_response`.
10. `generate_answer` → `validate_grounding`: sinh câu trả lời rồi kiểm tra claim có bám evidence hay không.
11. Tất cả nhánh trả lời người dùng (`sensitive`, `out_of_scope`, `greeting`, `conversation_context`, `ticket`, `no_data`, `grounding`) đều đi qua `enforce_response_language`.
12. `save_conversation_memory`: lưu lượt hội thoại hiện tại.
13. Sau `save_conversation_memory` là `END`.


