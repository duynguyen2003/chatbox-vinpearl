# Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m scripts.ingest_data
python -m scripts.check_chroma
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

http://127.0.0.1:5500
