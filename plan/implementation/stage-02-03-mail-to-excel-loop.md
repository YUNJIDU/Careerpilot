# Stage 2–3 Mail-to-Excel Execution Loop

## Entry

- Stage 0–1 tests pass.
- Development ports are frontend 9999 and backend 9998.
- 163 IMAP/SMTP access is enabled and the user has retained a client
  authorization code outside the repository.

## Loop

Each work package follows:

```text
failing test → minimum implementation → focused checks → full current-stage checks
```

### L1: Persistence foundation

1. Add SQLAlchemy and Alembic.
2. Define the minimal ORM tables and first migration.
3. Test empty upgrade, restart persistence, constraints, and rollback.

Gate: a migrated file database survives process restart and failed writes roll
back.

### L2: Application and Job services

1. Add repository persistence methods.
2. Add Application Service create/list/field-change/event operations.
3. Add provenance, user priority, idempotency, and optimistic locking.
4. Persist job lifecycle and checkpoints.

Gate: all writes pass through services and conflict/history tests pass.

### L3: Excel integration and Stage 2 gate

1. Import Stage 1 diffs through Application Service.
2. Export database snapshots through the existing atomic writer.
3. Persist workbook baseline, schema, and row versions.
4. Add application, Excel job, and job-status APIs.
5. Run Excel → DB → Excel → user edit → DB and resume tests.

Gate: every Stage 2 Exit Gate passes before L4.

### L4: Fixture mail pipeline

1. Add MailAdapter DTOs and fixture adapter.
2. Parse `.eml` with bounded standard-library MIME handling.
3. Convert HTML to text without loading remote content.
4. Add deterministic job fact extraction with bounded evidence.
5. Link or create applications only when explicit evidence is sufficient.
6. Persist emails idempotently and export the tracker.

Gate: fixture mail produces traceable SQLite and Excel output twice without
duplicates.

### L5: Windows secrets and 163 read-only adapter

1. Add Credential Manager SecretStore.
2. Add IMAP TLS connection and read-only inbox selection.
3. Add bounded date window, page size, timeout, retry, and cursor.
4. Add connection-test and manual-sync APIs.
5. Prove no send, delete, move, flag, or expunge operation exists.

Gate: fixture and 163 adapters pass the same contract tests.

### L6: Recovery, security, and Stage 3 gate

1. Test malformed MIME, hostile HTML, prompt injection text, duplicate mail,
   connection interruption, and resume.
2. Test that Excel user values win over later mail facts.
3. Scan logs, API output, SQLite, and Excel for credentials/full bodies.
4. Run all backend/frontend checks.
5. User stores the authorization code in Credential Manager.
6. Run one real 163 → SQLite → Excel demo and record Exit Gate results.

Gate: every Stage 3 Exit Gate passes, or the real-mail item is explicitly
reported as awaiting user-side acceptance.

## Commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\ruff.exe check backend
cd frontend
npm.cmd run check
npm.cmd run build
```

## Non-goals

No LLM, business UI, scheduler, attachment download, other email provider,
summary, recommendation, or outbound mailbox operation.
