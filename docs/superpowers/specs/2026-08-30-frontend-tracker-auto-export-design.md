# Frontend Tracker Auto-export Design

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

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
