# Stage 3 Completion Design

Date: 2026-07-28

Status: Approved design, pending written-spec review

## Goal

Close the remaining Stage 3 recovery and security gates for the existing
manual 163 mail-to-Tracker workflow without adding scheduling, a business UI,
another mail provider, or an LLM.

## IMAP retry

- Retry transient connection, timeout, and server-abort failures up to three
  attempts.
- Reconnect and repeat the same bounded, read-only search after each transient
  failure.
- Use short increasing waits between attempts.
- Do not retry invalid input or authentication rejection.
- Preserve TLS, read-only mailbox selection, `BODY.PEEK[]`, date window, and
  message limit.

Repeating a search is safe because Message-ID and raw-hash idempotency prevent
duplicate email, event, application, and Tracker writes.

## Failure and checkpoint state

At job start, persist a safe resume payload containing:

- account ID;
- mailbox address;
- start date;
- message limit;
- Tracker path.

The payload must not contain the authorization code. Each committed message
continues to update `last_message_id` and the processed count.

If synchronization fails after retries:

- mark the job `failed`;
- store a stable error code and a bounded, redacted message;
- retain the latest checkpoint;
- leave already committed database and Tracker data intact.

## Resume API

Implement:

```text
POST /api/v1/jobs/{job_id}/resume
```

The endpoint:

- accepts only failed `mail_sync` jobs;
- reads the safe resume payload from the existing checkpoint;
- obtains the authorization code again from Windows Credential Manager;
- creates a new resumptive execution linked by idempotency to the failed job;
- scans the same bounded window and skips already committed messages;
- returns the resumed job ID and processed count.

Missing jobs, non-mail jobs, non-failed jobs, missing checkpoint data, and
missing credentials return bounded client errors without exposing secrets.

## Security acceptance

Automated tests use sentinel secrets and message content to verify they do not
appear in:

- API responses;
- safe job errors;
- SQLite application, email, job, checkpoint, event, or provenance fields;
- generated Tracker workbooks;
- Git-tracked project files.

Email metadata, extracted facts, bounded evidence, Message-ID, and hashes remain
permitted. Full MIME and full body remain excluded.

## Validation

The minimum regression set covers:

- transient IMAP failure followed by a successful retry;
- authentication rejection without retry;
- failed job status and redacted safe error;
- resume of a partially processed mail job;
- rejection of invalid resume requests;
- duplicate prevention after resume;
- sentinel credential and body scanning;
- all existing Stage 0-3 backend tests;
- Ruff, frontend type-check, frontend production build, and GitHub CI.

Final manual acceptance performs a real read-only 163 connection and sync. A
forced real-provider failure is not required because deterministic adapter
tests cover interruption and recovery without risking mailbox state.

## Exit gate

Stage 3 is complete when:

- every validation item passes;
- the real read-only connection and sync succeed;
- the mail-to-SQLite-to-Tracker loop remains idempotent;
- Stage 3 planning and design documents are marked complete with the recorded
  checks.

## Deferred

- Scheduled synchronization.
- Formal application UI.
- Gmail or Outlook.
- Attachments and outbound mail.
- Dedicated IMAP UID cursor tables.
- LLM extraction.
