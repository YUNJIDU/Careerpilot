# Stage 4B Summary and Markdown Implementation Plan

Date: 2026-07-28
Design: `docs/superpowers/specs/2026-07-28-stage4-local-mvp-design.md`

## Goal

Deliver the manual information loop:

`application → Brave Top 5 → public pages → OpenAI-compatible Summary → Markdown`

Stage 4C Docker work remains out of scope.

## Constraints

- Use the Python standard library for HTTP and HTML extraction.
- Do not add a crawler, vector database, model framework, or frontend library.
- Search and model calls occur only after explicit user confirmation.
- Never send credentials to the model or store them in SQLite, Markdown, jobs,
  logs, or browser storage.
- Reject private/local fetch targets and enforce response-size/time limits.
- Failed jobs preserve the last successful Summary and Markdown.

## Task 1: Summary persistence and contracts

**Files**

- Add `backend/migrations/versions/0002_summary_versions.py`
- Modify `backend/src/careerpilot/core.py`
- Modify `backend/src/careerpilot/contracts.py`
- Add `backend/tests/test_stage4b.py`

Add an immutable `summary_versions` table keyed by summary id, application id,
and monotonically increasing version. Store only validated structured Summary
JSON and creation time. Add service methods for append, latest, and list.

Tests cover version ordering, application isolation, and preservation of the
latest successful version after later failures.

## Task 2: Brave search and bounded public-page fetch

**Files**

- Add `backend/src/careerpilot/summary.py`
- Extend `backend/tests/test_stage4b.py`

Implement:

- two approved queries;
- stable URL deduplication and combined Top 5;
- Brave credential sent only in the Brave request header;
- HTTP(S)-only public target validation;
- redirect, timeout, MIME, and maximum-size checks;
- small HTML-to-text extraction with scripts/styles ignored;
- per-page failure recording without aborting usable results.

Search/fetch clients remain injectable so tests never require the network.

## Task 3: OpenAI-compatible structured generation

**Files**

- Modify `backend/src/careerpilot/summary.py`
- Extend `backend/tests/test_stage4b.py`

Post to `<base_url>/chat/completions` using the configured model. Request one
JSON object containing overview, JD highlights, process clues, written-test and
interview information, known facts, unknowns, and cited sources.

Validate:

- required fields and size bounds;
- every citation belongs to the fetched Top 5;
- source URL, title, and fetch time are retained;
- external instructions remain quoted data and no tools are exposed.

## Task 4: Summary Job checkpoints and API

**Files**

- Modify `backend/src/careerpilot/summary.py`
- Modify `backend/src/careerpilot/api.py`
- Modify `backend/src/careerpilot/core.py`
- Extend `backend/tests/test_stage4b.py`

Add:

- `POST /api/v1/applications/{id}/summary-jobs`;
- `GET /api/v1/applications/{id}/summaries`;
- Summary dispatch in `POST /api/v1/jobs/{id}/resume`.

The request must contain `data_leaving_confirmed=true`. Checkpoints are search,
fetch, generate, and render. Search/fetch output is cached in the safe
checkpoint. Resume copies the failed checkpoint into a new idempotent job and
continues from the first incomplete step.

Tests cover explicit confirmation, missing settings/secrets, partial page
failure, safe errors, retry, idempotency, and no credential leakage.

## Task 5: Atomic per-application Markdown

**Files**

- Add `backend/src/careerpilot/markdown.py`
- Modify `backend/src/careerpilot/api.py`
- Extend `backend/tests/test_stage4b.py`

Render `<markdown_path>/<application_id>.md` with application fields, timeline,
evidence, mail metadata, current Summary, version, sources, timestamps, and
uncertainty. Escape Markdown/HTML-sensitive external content and replace the
target atomically.

Add `GET /api/v1/applications/{id}/markdown` for safe local viewing. Tests prove
escaping, stable naming, atomic replacement, and old-file preservation.

## Task 6: Summary and Markdown UI

**Files**

- Modify `frontend/src/api.ts`
- Modify `frontend/src/App.tsx`
- Modify `frontend/src/styles.css`

Application Detail gains:

- latest Summary and version history;
- a data-leaving confirmation checkbox;
- manual Generate Summary action;
- stage/progress and safe failure status;
- retry through the Jobs page;
- Markdown view/download link;
- sources and fetch times.

No background generation, automatic polling service, or source-selection UI is
added. The page performs bounded polling only while its newly created Job is
running.

## Task 7: Acceptance and documentation

**Files**

- Modify `README.md`
- Modify `plan/EXECUTION-HANDOFF.md`
- Modify `plan/implementation/stage-04-implementation.md`

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\ruff.exe check backend
Set-Location frontend
npm run check
npm run build
```

Fixture acceptance must complete search → partial fetch → generation → version
storage → Markdown → failed-job resume. Real Brave/model acceptance runs only
when both credentials are available through Credential Manager.

## Completion gate

Stage 4B is complete when automated checks pass, generated facts contain source
URLs and fetch times, failed jobs resume without duplicate versions, Markdown
is atomically rendered, secrets remain absent from outputs, and the PR is
merged to `main`.
