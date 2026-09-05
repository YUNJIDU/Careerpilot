# CareerPilot

Local-first job application assistant with a Web tracker, read-only mail sync,
Excel reconciliation, evidence timelines, and recoverable jobs.

## Project status and scope

The recorded baseline includes Stage 0–3, Stage 4A–4B, multi-resume management, Excel snapshot import, mail reconciliation, Web-to-Excel export and Windows CMD launchers. Stage 4C and the revised behavior must be verified against the current acceptance plan; documentation is not evidence of a passing release.

Excel is the authoritative store for application fields. Mail contributes field-level updates; ambiguous conflicts preserve manual values. Confirmed snapshot deletion permanently removes the application and its derived records. The current resume means the submitted resume.

Next: validate the existing data loop, establish evaluation fixtures, then deliver the original four Stage 5 groups (shared research, A–G evaluation, resume advice, comprehensive interview preparation), followed by the Orchestrator harness. Resume advice does not include replacement text unless requested. Interview preparation does not assume the interview type.

Near-term career-ops reuse covers requirement importance/evidence, company research/interview workflows and model-comparison methodology. Application-answer drafts (H), cover letters, offer support and analytics remain optional later modules. We do not import the upstream scanner, PDF pipeline or separate tracker.

Start with the [current policy](plan/CURRENT-POLICY.md), [overall plan](plan/总规划/03-mvp-plan.md), [handoff](plan/EXECUTION-HANDOFF.md), [harness](plan/stages/stage-06-agent-orchestration.md) and [evaluation plan](plan/EVALUATION.md). The [documentation index](docs/README.md) distinguishes current requirements from historical implementation records. Only documentation has been updated for the September 5 requirements; new evaluation results are not claimed.

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
