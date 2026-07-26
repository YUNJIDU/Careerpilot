# CareerPilot

Local-first job application assistant. Stage 0–1 includes the API health
boundary and a safe, database-independent Excel tracker engine.

## Project status

- Completed: Stage 0–1
- Next: Stage 2 — Application Core and persistence
- Planned: Stage 0–8

Start with the [execution handoff](plan/EXECUTION-HANDOFF.md), then use the
[implementation index](plan/implementation/README.md) and
[stage plans](plan/stages/) for scope, ordering, tests, and exit gates. The
[approved framework design](docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
defines the product and architecture boundaries.

## Windows development

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .\backend[dev]
.\.venv\Scripts\python -m pytest .\backend\tests
.\.venv\Scripts\python -m uvicorn careerpilot.api:app --app-dir .\backend\src --host 127.0.0.1
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Runtime data belongs in `data/` and must not be committed. Docker support is
deferred to Stage 4.

