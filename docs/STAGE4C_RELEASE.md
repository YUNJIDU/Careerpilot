# CareerPilot Stage 4C release guide

Stage 4C packages the existing local MVP as one Docker image and adds the
Windows, browser, security, and Docker checks required for a first release.
It does not add new product features. The same release foundation now packages
the completed P0.5 and Stage 5–7 features; see the
[current P0–P3 delivery guide](DELIVERY_P0_P3.md) for the complete scope.

## Windows quick start

Run every command below from the repository root, not from `frontend`.
Python 3.11 or newer and Node.js 22 or newer are required.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r .\backend\requirements\windows-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .\backend
cd frontend
npm.cmd ci
cd ..
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn careerpilot.api:create_app --factory --app-dir .\backend\src --host 127.0.0.1 --port 9998
```

In a second terminal, start the Web workspace:

```powershell
cd frontend
npm.cmd run dev
```

Open `http://127.0.0.1:9999`. The API documentation is at
`http://127.0.0.1:9998/docs`.

### Windows credentials

Web settings store non-secret values in `data/settings.json`. Secret values are
write-only and go to Windows Credential Manager. To enter the 163 authorization
code without placing it in shell history:

```powershell
.\.venv\Scripts\python.exe -m careerpilot.secrets personal your-address@163.com
```

The Tavily Search and model API keys can be entered on the Settings page. APIs
return only whether a secret exists, never the value.

## Docker quick start

Docker Desktop must be installed and running. Build from the repository root:

```powershell
docker build --tag careerpilot:local .
New-Item -ItemType Directory -Force .\data
docker run --detach --name careerpilot --publish 9998:9998 --publish 9999:9998 --mount "type=bind,source=$((Resolve-Path .\data).Path),target=/app/data" careerpilot:local
```

Open `http://127.0.0.1:9999`; the API remains available on port `9998`.
Startup automatically upgrades the SQLite database, and this command reports
container health:

```powershell
docker inspect --format "{{json .State.Health}}" careerpilot
```

The runtime process uses an unprivileged user. `/app/data` is the only
persistent application volume; the built frontend is served by FastAPI.

### Docker credentials

Docker secrets are injected at startup and are read-only in the Settings page.
Each secret can be supplied directly with an environment variable or through a
mounted text file. File injection avoids placing the value in the image or
command history.

| Purpose | Environment variable | Secret-file variable |
|---|---|---|
| 163 authorization code | `CAREERPILOT_MAIL_SECRET` | `CAREERPILOT_MAIL_SECRET_FILE` |
| Model API key | `CAREERPILOT_MODEL_SECRET` | `CAREERPILOT_MODEL_SECRET_FILE` |
| Tavily Search API key | `CAREERPILOT_TAVILY_SECRET` | `CAREERPILOT_TAVILY_SECRET_FILE` |

Gmail/Outlook OAuth client configuration and account tokens use dynamic
`CAREERPILOT_SECRET_<NAME>` / `_FILE` variables. Exact names and callbacks are
listed in the [Stage 7 integration guide](STAGE7_INTEGRATIONS.md). Prefer Secret
files; never copy OAuth JSON into the image, repository, SQLite or logs.

Create an ignored local `secrets` directory and place only the needed
single-line secret files inside it. Restrict access to that directory. Then:

```powershell
$careerData = (Resolve-Path .\data).Path
$careerSecrets = (Resolve-Path .\secrets).Path
docker run --detach --name careerpilot `
  --publish 9998:9998 `
  --publish 9999:9998 `
  --mount "type=bind,source=$careerData,target=/app/data" `
  --mount "type=bind,source=$careerSecrets,target=/run/secrets,readonly" `
  --env CAREERPILOT_MAIL_SECRET_FILE=/run/secrets/mail `
  --env CAREERPILOT_MODEL_SECRET_FILE=/run/secrets/model `
  --env CAREERPILOT_TAVILY_SECRET_FILE=/run/secrets/tavily `
  careerpilot:local
```

Only configure variables for files that exist. Non-secret settings such as the
mail address, model endpoint, and model name are still saved through the Web
Settings page.

## Persistent data and backup

All runtime files are beneath `data/`:

- `careerpilot.db`: canonical applications, evidence, jobs, and Summary versions;
- `tracker.xlsx`: portable Excel tracker;
- `settings.json`: non-secret settings;
- `markdown/`: generated per-application documents;
- `mail-samples/`, `attachments/`, and `resumes/`: content-addressed user files.

Secrets are not included. For a consistent backup, stop API writes (or stop the
container), copy the entire `data` directory to a dated backup, then restart.
Restore only while the application is stopped and keep the original backup
until the restored instance passes its health and data checks.

## Release acceptance

Local commands:

```powershell
.\.venv\Scripts\python.exe -m pytest .\backend\tests -q
.\.venv\Scripts\python.exe -m ruff check .\backend
cd frontend
npm.cmd run check
npm.cmd run build
npm.cmd run e2e
```

GitHub Actions repeats backend and frontend checks on both Windows and Linux,
runs the browser E2E on Windows, audits Python and npm dependencies, reports
licenses, scans tracked history for secrets, and builds, vulnerability-scans,
and smoke-tests the Docker image. The image gate rejects every critical finding
and every high finding for which a fixed version is available.

Manual first-release flow:

1. Configure the mail address, tracker path, model endpoint, and credentials.
2. Create one application and verify it survives a restart.
3. Test the 163 account and run read-only mail sync.
4. Export to Excel, make a safe edit, import, and verify manual precedence.
5. Generate a Summary after accepting the data-leaving notice; inspect whether
   sources match the exact role, whether related roles are marked as uncertain,
   timestamps, and `data/markdown/<application-id>.md`.
6. Trigger a recoverable Excel failure by importing a missing workbook. Export
   that workbook, then resume the failed import from Jobs and verify no
   duplicate application is created.

Stage 4C is accepted only after the local Windows flow and the remote Docker
workflow both pass. A machine without Docker can complete the Windows checks,
but cannot alone close the Docker gate.

## Troubleshooting

- `No suitable Python runtime found`: install Python 3.11 or newer, reopen the
  terminal, and confirm with `python --version` or `py -0p`.
- `requirements.txt` not found or `.venv` created under `frontend`: return to
  the repository root before creating the environment and use the locked
  `backend/requirements/windows-dev.lock` installation above.
- `No module named pytest` or `uvicorn`: run pip with the root
  `.\.venv\Scripts\python.exe`; do not use a `frontend\.venv`.
- `docker` is not recognized: install/start Docker Desktop and open a new
  terminal. The Docker CI check can still run after the branch is pushed.
- Port `9998` or `9999` is occupied: stop the existing CareerPilot process or
  container; development uses strict fixed ports.
- Docker Settings rejects a secret with HTTP 409: this is intentional. Restart
  the container with the relevant environment or `_FILE` variable.
- Container is unhealthy: inspect `docker logs careerpilot`, confirm the data
  mount is writable, and request `http://127.0.0.1:9998/api/v1/health`.
- Summary fails with `summary.model_http`: open Tasks and click Continue Task.
  The saved search and page-fetch checkpoint is reused, so this retries the
  unfinished model step without repeating the Tavily search. If it fails again,
  verify the model endpoint, credential, availability, and response latency.
- Excel or Markdown path is rejected: paths are relative to `data/`; absolute
  paths and `..` traversal are blocked.

## Known limitations

- Local single-user use only; there is no authentication or production reverse
  proxy. Keep both ports bound to `127.0.0.1`.
- 163, Gmail and Outlook access remains read-only. Gmail/Outlook require the
  user's own OAuth application and real-provider acceptance.
- Summary generation is manual and depends on a Tavily Search API and an
  OpenAI-compatible model endpoint.
- Reminders and notifications do not have a resident Worker; open the page to
  scan or export ICS to a calendar.
- Browser prefill is allowlisted and confirmation-based. There is no automatic
  application submission, CAPTCHA bypass, candidate scoring or multi-Agent
  workflow.
- No Kubernetes, image publishing pipeline, or multi-container orchestration.
- The Docker port layout assumes the browser runs on the same machine and is
  not a remote-host deployment design.
