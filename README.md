python -m scripts.ingest_data
python -m scripts.check_chroma
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install r- requirements.txt
#FAST_API
python -m uvicorn src.main:app --reload --port 8000 
#FE
python -m http.server 5500