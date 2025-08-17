# Pandas Formulas Demo

Minimal Excel-like spreadsheet engine with formulas, exposed via FastAPI and a tiny web UI.

## Run (no Docker)

```bash
python3 -m venv .venv source .venv/bin/activate pip install -r requirements.txt uvicorn app:app --reload # open http://127.0.0.1:8000 (UI at "/")
```

Optional API test (in another terminal, with server running):

```bash
python tests.py
```

## Run (Docker)

```bash
docker build -t spreadsheet-app . docker run --rm -p 8000:8000 spreadsheet-app # open http://127.0.0.1:8000
```

## Endpoints (brief)

- `GET /` – serves `index.html` (browser UI)
- `GET /sheet` – full sheet (JSON)
- `POST /value` – set raw value `{cell, value}`
- `POST /formula` – set formula `{cell, formula}`
- `GET /value/{cell}` – read value
- `GET /formula/{cell}` – read formula
- `GET /graph` – dependency edges (debug)