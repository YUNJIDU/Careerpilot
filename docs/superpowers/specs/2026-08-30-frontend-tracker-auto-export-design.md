# Frontend Tracker Auto-export Design

## Goal

Keep the configured Excel tracker current after every frontend operation that changes tracker-visible data. Manual Excel edits remain authoritative only after the user explicitly imports the workbook.

## Behavior

- Creating an application exports the configured tracker.
- Editing application fields exports the configured tracker.
- Assigning or replacing an application's current resume exports the configured tracker.
- Permanently deleting a resume exports the configured tracker and clears affected `当前简历` cells.
- Uploading an unassigned resume does not export because it has no tracker-visible effect.
- Mail sync continues to export once after the batch completes.
- Manual Excel edits do not trigger automatic import; the user must run Excel import.

## Implementation boundary

Add one API-local `export_current_tracker()` helper. It loads `tracker_path` from current settings, validates it below `data_dir`, and calls the existing atomic `ExcelSyncService.export_workbook()` implementation. Tracker-visible mutation endpoints call this helper after their database write succeeds.

Do not add database hooks, background jobs, file watchers, or a new synchronization layer.

## Failure behavior

Database changes occur before filesystem export. If export fails, return an explicit server error stating that the data was saved but Excel could not be updated. The next successful frontend mutation or manual export rewrites the workbook from current database state.

## Verification

One API regression test uses the configured tracker path and verifies:

1. assigning a resume writes `当前简历`;
2. replacing it updates the cell;
3. permanently deleting the resume clears the cell;
4. editing an application field updates the same workbook.
