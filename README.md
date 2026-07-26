# CareerPilot

Local-first job application assistant. Stage 0–1 includes the API health
boundary and a safe, database-independent Excel tracker engine.

## Project status

- Completed: Stage 0–3
- Next: Stage 4 — local Web, Markdown, and manual Summary
- Planned: Stage 0–8

Start with the [execution handoff](plan/EXECUTION-HANDOFF.md), then use the
[implementation index](plan/implementation/README.md) and
[stage plans](plan/stages/) for scope, ordering, tests, and exit gates. The
[approved framework design](docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
defines the product and architecture boundaries.

## Windows development

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
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

## 163 mail sync

Store the client authorization code in Windows Credential Manager without
putting it in shell history:

```powershell
.\.venv\Scripts\python.exe -m careerpilot.secrets personal your-address@163.com
```

Start the API, open `http://127.0.0.1:9998/docs`, then use:

```text
POST /api/v1/mail-accounts/test
POST /api/v1/mail-sync-jobs
GET  /api/v1/applications
```

The mailbox adapter uses IMAP TLS, identifies the client to 163, selects
`INBOX` read-only, and fetches with `BODY.PEEK[]`. Runtime output is written to
`data/careerpilot.db` and `data/tracker.xlsx`.

Runtime data belongs in `data/` and must not be committed. Docker support is
deferred to Stage 4.
