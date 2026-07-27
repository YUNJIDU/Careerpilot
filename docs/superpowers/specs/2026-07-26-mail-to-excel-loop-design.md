# Mail-to-Excel Loop Design

Date: 2026-07-26

Status: Complete

## Goal

Complete the first real CareerPilot data loop:

```text
Swagger manual sync
  → read local fixtures or 163 inbox without server writes
  → extract explicit job facts with deterministic rules
  → persist facts, evidence, jobs, and checkpoints in SQLite
  → update data/tracker.xlsx without overwriting user edits
```

This work completes Stage 2 before entering Stage 3.

## Scope

### Stage 2

- SQLAlchemy, SQLite, and Alembic migration from an empty database.
- Minimal tables used by this loop: applications, application_events,
  field_provenance, email_records, sync_batches, background_jobs, and
  job_checkpoints.
- Repository code handles persistence only.
- Application Service is the only business write path.
- User values take priority; system values remain traceable history.
- Excel import/export runs through Application Service and persists its sync
  baseline and row versions.
- Minimal application, Excel sync, and job APIs.

### Stage 3

- One MailAdapter contract shared by `.eml` fixtures and 163 IMAP.
- Python standard-library MIME parsing and HTML-to-text conversion.
- Deterministic rules extract only explicit company, role, stage, dates,
  deadlines, links, and results.
- Ambiguous values remain empty; no model is called.
- Mail content is untrusted and cannot trigger tools or instructions.
- 163 access uses IMAP over TLS and read-only mailbox selection.
- Mailbox credentials are read from Windows Credential Manager through
  `SecretStore`; target names use `CareerPilot/mail/163/{account_id}`.
- A committed email advances the checkpoint; a failed message is isolated.
- Successful application changes are exported atomically to
  `data/tracker.xlsx`.
- Swagger exposes connection test, manual sync, and job status endpoints.

## Data and conflict rules

- Stable Message-ID is the primary email idempotency key; otherwise use a hash
  of normalized headers and body.
- Stable Application ID links SQLite and Excel.
- A user-edited Excel field is never silently replaced by a mail-derived value.
- A conflicting mail value is recorded as provenance/event history.
- Full MIME and full body are not retained by default.
- Evidence excerpts are bounded and logs are redacted.

## Error and recovery rules

- Migration failure stops startup without deleting the database.
- Database writes are transactional.
- Excel replacement occurs only after write-and-read validation.
- IMAP connection failure does not advance the checkpoint.
- One malformed message does not stop the remaining batch.
- Repeating a sync does not duplicate email records, events, or applications.
- Credentials never enter SQLite, Excel, logs, API responses, Git, or fixtures.

## API

```text
GET  /api/v1/applications
POST /api/v1/excel-sync-jobs
POST /api/v1/mail-accounts/test
POST /api/v1/mail-sync-jobs
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/resume
```

The API calls services only and remains on `127.0.0.1:9998`.

## Validation gates

Stage 2 must pass persistence restart, migration, transaction rollback,
optimistic locking, idempotency, provenance, and Excel round-trip tests before
Stage 3 starts.

Stage 3 must pass fixture/163 adapter contract tests, duplicate mail, malformed
MIME, hostile HTML, prompt injection text, connection interruption, checkpoint
resume, user-value priority, and formula-injection tests.

Final manual acceptance requires one real 163 message to produce traceable
SQLite data and a valid `data/tracker.xlsx` row without any server-side mailbox
mutation.

## Real-mail rule extension

The deterministic extractor must recognize common Chinese recruitment wording
without introducing an LLM or a new dependency.

- Treat phrases such as `感谢您投递`, `已经收到您的简历`, `简历提交成功`,
  `笔试通知`, `面试安排`, and `成绩查询` as recruitment evidence.
- Extract a role from `感谢您投递我公司的{role}职位` and equivalent
  `本公司` or `岗位` forms.
- When the body uses `我公司` or `本公司`, an organization-like closing
  signature may supply the company name. A personal sender name or address is
  not sufficient evidence.
- Map `笔试成绩查询`, `成绩查询已开通`, and equivalent explicit wording to
  `笔试成绩可查询`.
- If company and recruitment stage are explicit but the role is absent, create
  the application with role `岗位待确认` rather than dropping the message.
- Use the message `Date` for `投递时间` on the first application-receipt event
  and for `最近更新时间` on every accepted state event. Later messages must not
  overwrite the original application time.
- Reprocess stored emails that have not been linked to an application. Already
  linked messages remain idempotent.

The minimum regression set contains the two ArcSoft receipt examples and the
Guizhou Financial Holding written-test result example supplied during manual
acceptance. It verifies company, role, stage, timestamps, fallback role,
reprocessing, and duplicate prevention.

## Deferred

- LLM extraction, formal Web UI, schedules, Gmail/Outlook, attachments,
  Markdown/Summary, recommendations, and outbound mail.
