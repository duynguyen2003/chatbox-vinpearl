# Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

data to posgre
check
python -c "from src.data_postgre.db import CORE_TABLES, APP_TABLES; print(len(CORE_TABLES), 'core +', len(APP_TABLES), 'app'); print(sorted(CORE_TABLES))"
create
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE USER vinpearl WITH PASSWORD '210303';"
alembic current
alembic upgrade head
python -m scripts.seed_destinations
python -m scripts.load_core

chunk data posgre

python -m src.backend.services.ingest_postgres --reset

```

Lược đồ chia ba schema — chi tiết ở [docs/DATABASE.md §18](docs/DATABASE.md):

| Schema | Nội dung |
|---|---|
| `core` | 36 bảng nghiệp vụ + vận hành nạp |
| `app` | 7 bảng hội thoại, ticket, nhật ký |
| `api` | 11 view đọc đã gộp sẵn — `core.*` là bảng, `api.*` là cùng thứ đó đã join |

`search_path` mặc định là `public, core, app, api` nên SQL không ghi schema vẫn chạy.

```powershell
# xem nhanh trong terminal
docker compose exec db psql -U vinpearl -d vinpearl -c "SELECT * FROM api.destination"
```

# FAST_API

```powershell
python -m uvicorn src.backend.main:app --reload --port 8000
```

# FE

```powershell
cd D:\Demo-day\P-013
npm install
npm run dev
```


# User đầu (admin)
```powershell
$body = @{
  name = "P013 Admin"
  email = "admin@example.com"
  phone = $null
  password = "ChangeThisPassword123!"
  locale = "vi"
  bootstrap_key = "lay trong env ra"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/auth/bootstrap-admin" `
  -ContentType "application/json" `
  -Body $body
```
# web admin /admin/staff