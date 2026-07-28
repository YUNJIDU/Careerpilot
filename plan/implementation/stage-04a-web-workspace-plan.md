# Stage 4A Web Workspace Implementation Plan

Date: 2026-07-28
Design: `docs/superpowers/specs/2026-07-28-stage4-local-mvp-design.md`

## Goal

Deliver the first usable local Web loop:

`configure → create/edit application → sync mail → sync Excel → inspect detail/job`

This plan covers Stage 4A only. Summary, Brave search, Markdown, and Docker stay
out of this loop.

## Constraints

- Reuse the existing FastAPI, SQLAlchemy, React, and browser APIs.
- Add no frontend router, UI kit, form library, or state library.
- Keep secrets out of tracked files, browser storage, logs, and API responses.
- Preserve current mail/Excel reconciliation and Job resume behavior.
- Store non-secret settings under `data/`; keep runtime data ignored by Git.

## Task 1: Application read/write API

**Files**

- Modify `backend/src/careerpilot/core.py`
- Modify `backend/src/careerpilot/api.py`
- Add `backend/tests/test_stage4a.py`

**Checks first**

Add API tests proving:

1. `POST /api/v1/applications` creates an application idempotently.
2. Empty company or role is rejected.
3. `GET /api/v1/applications/{id}` returns fields, timeline, provenance, and
   linked mail evidence.
4. `PATCH /api/v1/applications/{id}` records user provenance and increments the
   version.
5. A stale `expected_version` returns HTTP 409 and does not change data.
6. Unknown applications return HTTP 404.

**Implementation**

- Add focused `ApplicationService` read methods for events, provenance, and
  linked email evidence. Reuse the existing tables; no migration is required.
- Add strict Pydantic request models for create and patch.
- Use the existing `source="user"` storage value and expose it as manual
  provenance in the UI.
- Map service `KeyError`, validation errors, and version conflicts to stable
  HTTP 404/422/409 responses.
- Permit `GET`, `POST`, and `PATCH` through CORS.

**Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_stage4a.py -q
.\.venv\Scripts\ruff.exe check backend
```

## Task 2: Settings and secret status API

**Files**

- Add `backend/src/careerpilot/settings.py`
- Modify `backend/src/careerpilot/secrets.py`
- Modify `backend/src/careerpilot/api.py`
- Extend `backend/tests/test_stage4a.py`

**Checks first**

Add tests proving:

1. non-secret settings survive an API restart;
2. configured paths cannot escape the project data directory;
3. mail, model, and Brave secrets can be written and report only
   `saved: true/false`;
4. no read endpoint returns a secret;
5. settings JSON and safe errors contain no credential sentinel.

**Implementation**

- Store one small atomic JSON document at `data/settings.json` containing only
  mail identity, tracker/Markdown paths, model base URL/model name, and
  scheduling-disabled state.
- Extend `WindowsSecretStore` with named model and Brave credential targets
  while preserving the existing 163 target and CLI.
- Add `GET /api/v1/settings` and `PUT /api/v1/settings`.
- Accept optional write-only secret fields on update, store them immediately,
  and omit them from all response models.
- Keep scheduling displayed as disabled; do not create a scheduler.

**Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_stage4a.py -q
.\.venv\Scripts\ruff.exe check backend
```

## Task 3: Job listing and consistent sync results

**Files**

- Modify `backend/src/careerpilot/core.py`
- Modify `backend/src/careerpilot/api.py`
- Extend `backend/tests/test_stage4a.py`

**Checks first**

Add tests proving:

1. `GET /api/v1/jobs` returns newest jobs first without secrets;
2. Excel import/export jobs finish with `succeeded`;
3. invalid Excel direction returns HTTP 422 rather than a server error;
4. mail sync returns its `job_id` as well as the processed count;
5. only failed mail jobs expose a valid resume action.

**Implementation**

- Add `JobService.list()` using the existing job/checkpoint records.
- Return a shared safe Job view from list/get/sync endpoints.
- Complete Excel jobs with `JobService.complete()` instead of leaving them in
  `running`.
- Preserve the Stage 3 resume endpoint and idempotency rules.

**Verify**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_stage3.py backend\tests\test_stage4a.py -q
.\.venv\Scripts\ruff.exe check backend
```

## Task 4: React workspace shell

**Files**

- Replace `frontend/src.tsx` with `frontend/src/main.tsx`
- Add `frontend/src/App.tsx`
- Add `frontend/src/api.ts`
- Add `frontend/src/styles.css`
- Modify `frontend/index.html`
- Modify `frontend/tsconfig.json`

**Implementation**

- Build the approved fixed-sidebar workspace.
- Use `location.hash` and `hashchange` for navigation.
- Define the API response/request types next to the small typed fetch wrapper in
  `api.ts`.
- Add overview cards and navigation for Overview, Applications, Mail, Excel,
  Jobs, and Settings.
- Provide visible keyboard focus, semantic labels, adequate contrast, and
  responsive behavior.
- Keep state in React only; do not use `localStorage` or `sessionStorage`.

**Verify**

```powershell
Set-Location frontend
npm run check
npm run build
```

## Task 5: Tracker, detail, sync, jobs, and settings pages

**Files**

- Modify `frontend/src/App.tsx`
- Modify `frontend/src/api.ts`
- Modify `frontend/src/styles.css`

**Implementation**

- Applications:
  search, stage filter, create form, and application table.
- Application detail:
  editable fields with version-aware save, timeline, provenance, and mail
  evidence.
- Mail:
  account/date/limit controls, connection test, sync action, and safe result.
- Excel:
  configured tracker path, import/export actions, and result.
- Jobs:
  newest-first history, progress/error/checkpoint summary, and resume for failed
  mail jobs.
- Settings:
  non-secret configuration, secret saved status, and optional replacement
  inputs that clear after successful save.
- Every request has loading, empty, success, and error feedback. Failed saves
  keep current form input.
- Generate idempotency keys in the browser with `crypto.randomUUID()`.

**Verify**

```powershell
Set-Location frontend
npm run check
npm run build
```

## Task 6: Full regression and Windows acceptance

**Files**

- Modify `README.md`
- Modify `plan/EXECUTION-HANDOFF.md`
- Modify `plan/implementation/stage-04-implementation.md`

**Automated checks**

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\ruff.exe check backend
Set-Location frontend
npm run check
npm run build
```

**Manual Windows acceptance**

1. Start FastAPI on `127.0.0.1:9998`.
2. Start Vite on `127.0.0.1:9999`.
3. Save settings without exposing credential values.
4. Create and edit one application in the Web UI.
5. Test the configured 163 account and run mail sync.
6. Import and export the configured tracker.
7. Confirm the application detail includes timeline/evidence.
8. Confirm Job history and a fixture-backed resume flow.
9. Confirm a manual non-empty field survives later Excel/mail reconciliation.

## Completion gate

Stage 4A is complete when all automated checks pass, the Windows acceptance
loop succeeds, credentials are absent from tracked/runtime-readable outputs,
and the 4A commit is merged to `main`.
