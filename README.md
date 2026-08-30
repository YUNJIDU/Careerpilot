# CareerPilot

Local-first job application assistant with a Web tracker, read-only mail sync,
Excel reconciliation, evidence timelines, and recoverable jobs.

## Project status

- Completed: Stage 0–3, Stage 4A–4B, multi-resume management, and Excel source-of-truth sync
- Current: streamlined Stage 4C-Windows — welcome UI, local security, and Windows release baseline
- Later release work: Docker, authentication, HTTPS, auto-update, and installer packaging
- Planned: Stage 0–8

Start with the [execution handoff](plan/EXECUTION-HANDOFF.md), then use the
[implementation index](plan/implementation/README.md) and
[stage plans](plan/stages/) for scope, ordering, tests, and exit gates. The
[approved framework design](docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
defines the product and architecture boundaries.

## Windows development

After installing the dependencies below, start both services and open the welcome page with:

```powershell
.\start-careerpilot.ps1
```

You can also double-click `启动CareerPilot.cmd` to start both services and
`关闭CareerPilot.cmd` to stop only the recorded CareerPilot processes.

The command can be run again when CareerPilot is already running. Logs are written to
`data/logs/`. If ports `9998` or `9999` belong to another program, the command stops
and reports the conflicting port instead of starting a second service.

Run the local release checks with:

```powershell
.\check-release.ps1
```

Initial dependency setup:

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

The Web workspace provides Overview, Applications, Application Detail, Mail,
Excel, Jobs, and Settings pages. Non-secret settings are stored in
`data/settings.json`; secret inputs are write-only and stored in Windows
Credential Manager.

Terminal results are shown as `已结束（<环节>未通过）`. Existing values such as
`笔试挂` are recognized immediately; Web, Excel, and mail updates use the same
normalization while preserving the timeline.

## Manual Summary

In Settings, save a Brave Search API key plus an OpenAI-compatible model
endpoint, model name, and optional model API key. On an application detail
page, confirm that data may leave the machine and choose **生成新 Summary**.

Each run searches two focused queries, keeps the first five unique public
sources, writes an immutable Summary version, and atomically refreshes
`data/markdown/<application-id>.md`. Failed jobs can resume from their latest
checkpoint without repeating completed search or fetch work.

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

Runtime data belongs in `data/` and must not be committed. Docker and the wider
release packaging are intentionally deferred until the core product features are stable.
