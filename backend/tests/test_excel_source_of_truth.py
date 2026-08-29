from pathlib import Path

import pytest

from careerpilot.core import ApplicationService, Database, ExcelSyncService, ResumeService
from careerpilot.excel import COLUMNS, RESUME_COLUMN, TrackerRow, write_tracker


def test_excel_snapshot_clears_deletes_and_maps_resume(tmp_path: Path) -> None:
    database = Database(tmp_path / "careerpilot.db")
    applications = ApplicationService(database)
    resumes = ResumeService(database)
    sync = ExcelSyncService(database, applications)
    kept = applications.create(
        "Acme", "Developer", idempotency_key="kept", values={"备注": "remove me"}
    )
    deleted = applications.create("Gone", "Role", idempotency_key="deleted")
    resume = resumes.create_version(
        label="后端简历",
        filename="resume.txt",
        content_type="text/plain",
        size=6,
        content_hash="a" * 64,
    )
    tracker = write_tracker(
        tmp_path / "tracker.xlsx",
        [
            TrackerRow(
                application_id=kept.application_id,
                values={
                    **dict.fromkeys(COLUMNS),
                    "公司名称": "Acme",
                    "岗位": "Developer",
                    RESUME_COLUMN: "后端简历@v1",
                },
            )
        ],
    )

    result = sync.import_workbook(tracker, "snapshot")

    assert result == {"created": 0, "updated": 1, "deleted": 1, "resume_mapped": 1}
    assert applications.get(kept.application_id).values["备注"] is None
    with pytest.raises(KeyError):
        applications.get(deleted.application_id)
    assert resumes.get(resume.version_id).application_ids == (kept.application_id,)
    assert (tmp_path / "careerpilot.db.pre-excel-import.bak").is_file()


def test_invalid_resume_rolls_back_snapshot_deletion(tmp_path: Path) -> None:
    database = Database(tmp_path / "careerpilot.db")
    applications = ApplicationService(database)
    sync = ExcelSyncService(database, applications)
    kept = applications.create("Acme", "Developer", idempotency_key="kept")
    omitted = applications.create("Still", "Here", idempotency_key="omitted")
    tracker = write_tracker(
        tmp_path / "tracker.xlsx",
        [
            TrackerRow(
                application_id=kept.application_id,
                values={
                    **dict.fromkeys(COLUMNS),
                    "公司名称": "Acme",
                    "岗位": "Developer",
                    RESUME_COLUMN: "不存在的简历",
                },
            )
        ],
    )

    with pytest.raises(ValueError, match="missing or ambiguous"):
        sync.import_workbook(tracker, "invalid")

    assert applications.get(omitted.application_id).company == "Still"
