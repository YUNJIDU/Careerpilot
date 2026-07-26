# CareerPilot

Local-first job application assistant. Stage 0–1 includes the API health
boundary and a safe, database-independent Excel tracker engine.

## Windows development

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .\backend[dev]
.\.venv\Scripts\python -m pytest .\backend\tests
.\.venv\Scripts\python -m uvicorn careerpilot.api:app --app-dir .\backend\src --host 127.0.0.1 --port 9998
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:9999` and calls the backend at
`http://127.0.0.1:9998`.

Runtime data belongs in `data/` and must not be committed. Docker support is
deferred to Stage 4.

