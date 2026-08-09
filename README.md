# Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

data to posgre
check
python -c "from src.db import Base; print(len(Base.metadata.tables)); print(list(Base.metadata.tables.keys()))"
create
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE USER vinpearl WITH PASSWORD '210303';"
alembic current
alembic upgrade head
python -m scripts.seed_destinations
python -m scripts.load_core

chunk data posgre

python -m src.backend.services.ingest_postgres --reset

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


# User đầu
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