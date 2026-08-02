# CareerPilot

Local-first job application assistant with a Web tracker, read-only mail sync,
Excel reconciliation, evidence timelines, and recoverable jobs.

## Project status

- Local release candidate: Stage 0–7, including P0.5 resources, evidence
  intelligence, the bounded single-Agent approval loop, guarded external
  integrations, Docker packaging, CI and security gates
- Package version: `0.1.0`; local delivery is not yet pushed or tagged
- Planned: P4 Stage 8 productization

Start with the [execution handoff](plan/EXECUTION-HANDOFF.md), then use the
[implementation index](plan/implementation/README.md) and
[stage plans](plan/stages/) for scope, ordering, tests, and exit gates. The
[approved framework design](docs/superpowers/specs/2026-07-26-careerpilot-framework-design.md)
defines the product and architecture boundaries.

For installation, Docker, credentials, backup, acceptance, and troubleshooting,
use the [Stage 4C release guide](docs/STAGE4C_RELEASE.md).
Stage 5 contracts, evidence rules, APIs, and recovery are in the
[Stage 5 evidence guide](docs/STAGE5_EVIDENCE.md).
Stage 6 tools, approval flow, budgets, recovery, and troubleshooting are in the
[Stage 6 Agent guide](docs/STAGE6_AGENT.md); its measured results and
Multi-Agent decision are in the [Stage 6 evaluation](docs/STAGE6_EVALUATION.md).
Gmail/Outlook OAuth, reminders, ICS, notifications, and guarded browser prefill
are documented in the [Stage 7 integration guide](docs/STAGE7_INTEGRATIONS.md).
Measured local results and the remaining real-provider acceptance condition are
in the [Stage 7 evaluation](docs/STAGE7_EVALUATION.md).

The complete delta from the original GitHub baseline, architecture, installation,
usage, data handling, GitHub Flow, release and rollback process is in the
[P0–P3 delivery guide](docs/DELIVERY_P0_P3.md). Use the [documentation
index](docs/README.md) for all guides. Repository governance is defined by the
[changelog](CHANGELOG.md), [contribution guide](CONTRIBUTING.md), [security
policy](SECURITY.md), and [privacy notice](PRIVACY.md).

## Windows development

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r .\backend\requirements\windows-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .\backend
.\.venv\Scripts\python.exe -m pytest .\backend\tests
.\.venv\Scripts\python.exe -m uvicorn careerpilot.api:create_app --factory --app-dir .\backend\src --host 127.0.0.1 --port 9998
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend runs at `http://127.0.0.1:9999` and calls the backend at
`http://127.0.0.1:9998`.

The Web workspace provides Overview, Applications, Application Detail, Evidence
Analysis, Agent Assistance, Mail, Resumes, External Integrations, Excel, Jobs,
and Settings pages. Non-secret settings are stored in
`data/settings.json`; secret inputs are write-only and stored in Windows
Credential Manager.

Terminal results are shown as `已结束（<环节>未通过）`. Existing values such as
`笔试挂` are recognized immediately; Web, Excel, and mail updates use the same
normalization while preserving the timeline.

## Manual Summary

In Settings, save a Tavily Search API key plus an OpenAI-compatible model
endpoint, model name, and optional model API key. On an application detail
page, confirm that data may leave the machine and choose **生成新 Summary**.

Each run searches two focused queries, keeps the first five unique public
sources, writes an immutable Summary version, and atomically refreshes
`data/markdown/<application-id>.md`. Failed jobs can resume from their latest
checkpoint without repeating completed search or fetch work.

## Stage 5 evidence intelligence

Open an application and choose **证据分析**. The page keeps immutable JD,
company-research, and resume–JD mapping versions. Every generated conclusion
must carry a quote and locator from the JD, selected resume, or fetched public
page. Mapping status is limited to `matched`, `partial`, `missing`, and
`unknown`; the product does not calculate a candidate score or hiring
probability. Model calls require explicit data-leaving confirmation, while gap
analysis is deterministic and the final review remains a human action.

## Stage 6 controlled Agent

Open an application and choose **Agent 协助**. Every run is bound to that one
application and uses a small built-in tool whitelist. Read tools may run within
the selected limits; the only Stage 6 write tool can append a note and always
pauses on an exact preview until the user approves it. Refreshing or restarting
the service preserves pending approvals, while optimistic locking and stable
idempotency keys prevent stale or duplicate writes.

The default limits are 8 steps, 6 model calls, 8 tool calls, 2 write-approval
candidates, and 180 seconds of active run time. Stage 0–5 services and pages do
not depend on the Agent and continue to work independently.

## Stage 7 external integrations

Open **外部集成** to connect Gmail or Outlook with read-only OAuth, create local
reminders, export ICS, and enable browser notifications. The optional unpacked
extension in `browser-extension/` maps only an allowlist of profile fields on
the active HTTPS tab, previews every difference, stops when CAPTCHA is present,
and never submits the form. OAuth tokens remain in the system SecretStore.

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
available through the root `Dockerfile`; see the
[release guide](docs/STAGE4C_RELEASE.md) before starting it. The current API has
no authentication or tenant isolation, so keep it bound to the local loopback
interface until Stage 8 production controls are implemented.
