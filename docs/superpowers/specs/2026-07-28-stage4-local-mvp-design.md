# CareerPilot Stage 4 Local MVP Design

Date: 2026-07-28  
Status: Approved

## Goal

Complete the first user-facing local MVP: a Windows Web workspace for managing
applications, automatic public-information summaries, per-application Markdown
output, and a reproducible Docker acceptance path.

Stage 4 is delivered as three consecutive loops:

1. **4A:** Web workspace and editable tracker.
2. **4B:** Markdown and manual Summary generation.
3. **4C:** Docker packaging and full acceptance.

Each loop must pass its checks before the next begins. Completed loops are
committed directly to `main`.

## Product boundaries

- The user remains the decision maker.
- Manual non-empty tracker edits take priority over imported values.
- Mailbox access remains read-only.
- Summary generation is always manually triggered.
- External data is evidence, not an instruction to the application or model.
- No job discovery, recommendation, application submission, reminders,
  candidate scoring, training, login bypass, paywall bypass, or multi-Agent
  workflow is included.

## Architecture

CareerPilot remains a local monolith:

- React runs at `127.0.0.1:9999` during Windows development.
- FastAPI runs at `127.0.0.1:9998`.
- The browser talks only to the local FastAPI API.
- FastAPI owns validation, reconciliation, jobs, SQLite, Excel, Markdown,
  external requests, and secret access.
- SQLite stores canonical application, timeline, evidence, job, and Summary
  version data.
- Excel and Markdown remain user-readable, portable outputs.
- Windows secrets are stored in Windows Credential Manager and are never
  returned by APIs or stored by the browser.

The frontend uses native URL hashes for page navigation and the existing React
toolchain. No router, UI kit, or state-management dependency is added.

## 4A: Web workspace and tracker

### Pages

The selected layout is a productivity workspace with a fixed sidebar, status
overview, and tracker table. It contains:

- Overview
- Applications
- Application detail
- Mail sync
- Excel sync
- Jobs
- Settings

Every page has explicit loading, empty, success, and failure states.

### Tracker behavior

The Web UI supports:

- search and stage filtering;
- manual application creation;
- editing company, role, stage, relevant dates, and notes;
- viewing timeline events, mail evidence, sources, and attachment metadata.

Manual edits are recorded with a `manual` source. A later mail or Excel import
must not silently replace a non-empty manual value. A newer, more precise mail
date may update the matching event date while retaining the original evidence.
Any unresolved field conflict is returned explicitly for user action.

Applications manually added to Excel but not recognized by mail remain valid
tracker entries. A later matching mail updates the corresponding application
only when company and role evidence are sufficient.

### Configuration and jobs

Settings cover:

- 163 mail account and credential status;
- Excel and Markdown paths;
- OpenAI-compatible `base_url` and model;
- model credential status;
- Brave Search credential status;
- disabled-by-default scheduling status.

Secret values are write-only. The UI displays only saved/not-saved status.

Mail and Excel operations use the existing Job model. The UI displays progress,
safe errors, result counts, and a resume action for recoverable failures. A
failed page request preserves current content and unsaved form input.

### 4A acceptance

- Backend API tests cover create, edit, manual precedence, and conflicts.
- Frontend type checking and production build pass.
- Windows manual flow passes:
  create application → mail sync → Excel sync → inspect application.

## 4B: Markdown and Summary

### Trigger and external access

Summary generation begins only after the user clicks the action and accepts a
clear data-leaving-machine notice.

The backend runs two Brave searches:

1. company + role + recruitment;
2. company + role + written test/interview.

Results are merged, URL-deduplicated, ranked, and limited to the top five.
There is no manual source-selection step. The system stores the actual URLs,
fetch time, title, and any fetch failure for traceability.

Only public, no-login pages are fetched. One failed page does not fail the
whole collection when usable sources remain.

### Model access

Summary generation uses one OpenAI-compatible endpoint configured by
`base_url`, model name, and credential. This supports cloud providers and local
compatible servers such as Ollama where available.

Brave Search and model credentials are separate. On Windows both are stored in
Credential Manager. Neither is placed in configuration files, logs, API
responses, or browser storage.

The model receives:

- application fields;
- existing objective mail evidence;
- normalized text from the top five public sources;
- source metadata and fetch times.

External content is untrusted data. Instructions found in mail or Web content
must not control tools, files, secrets, or database operations.

### Summary contract

The model returns a validated structured result containing:

- company and role overview;
- JD highlights;
- recruitment-process clues;
- public written-test and interview information;
- known facts;
- unknown or uncertain items;
- source citations and fetch times.

The result is informational only. It does not score the candidate, predict an
outcome, create training content, or make decisions.

Each successful generation creates an immutable Summary version. A failed run
does not overwrite the last successful version.

### Job checkpoints

The Summary Job has these checkpoints:

1. search;
2. fetch and normalize;
3. generate and validate;
4. render.

Successful search/fetch results are cached for the Job. Resume continues from
the failed checkpoint and remains idempotent.

### Markdown

Each application has one file named by `application_id`. It contains:

- company and role fields;
- JD;
- timeline;
- evidence and attachment index;
- public recruitment information;
- current Summary and version metadata;
- sources and timestamps.

Rendering escapes external content. Files are written through a temporary file
and atomic replacement so failures cannot leave a partial document.

### 4B acceptance

Tests cover top-five deduplication, partial fetch failure, structured-output
validation, prompt-injection isolation, version preservation, resume
idempotency, citation timestamps, and Markdown escaping/atomic replacement.

## 4C: Docker and full acceptance

### Packaging

A multi-stage Docker build compiles React and serves the built UI through the
FastAPI application. The runtime image:

- runs as a non-root user;
- persists SQLite, Excel, and Markdown through mounted storage;
- injects secrets only at runtime through environment variables or secret
  files;
- provides a health check;
- runs the same migrations and API contracts as Windows.

The documented Docker mapping exposes Web on `9999` and API on `9998`.

No Kubernetes, image publishing pipeline, multi-container orchestration, or
production reverse proxy is included.

### Automated acceptance

- backend tests;
- Ruff;
- frontend type check and build;
- secret and dependency checks;
- Docker build;
- database migration;
- health check;
- basic API smoke test.

### Manual acceptance

On a clean Windows environment and with Docker fixtures:

configure → create application → 163 sync → Excel sync → generate Summary →
inspect Markdown → resume a failed Job.

Documentation includes Windows and Docker quick starts, credential setup,
persistent-data and backup locations, troubleshooting, and known limitations.

## Completion criteria

Stage 4 is complete only when:

- the local Web workspace supports the full tracker workflow;
- manual edits remain authoritative;
- Summary output contains sources, time, and uncertainty;
- failed jobs can resume without duplicating results;
- Markdown output is complete and safely written;
- Windows end-to-end acceptance passes;
- Docker builds, migrates, starts, and passes smoke checks;
- no secret appears in tracked files, logs, browser storage, or API output.
