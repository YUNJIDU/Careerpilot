from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.core import ApplicationService, Database, ExcelSyncService, JobService
from careerpilot.excel import COLUMNS, TrackerRow, read_tracker, write_tracker


def test_database_survives_restart_and_user_value_wins(tmp_path: Path) -> None:
    path = tmp_path / "careerpilot.db"
    first = ApplicationService(Database(path))
    app = first.create("Acme", "Engineer", idempotency_key="application-1")
    first.apply_field_change(
        app.application_id,
        "当前阶段",
        "一面 2026-08-01",
        source="user",
        idempotency_key="user-stage",
    )
    first.apply_field_change(
        app.application_id,
        "当前阶段",
        "已拒绝",
        source="mail",
        idempotency_key="mail-stage",
    )

    second = ApplicationService(Database(path))
    loaded = second.get(app.application_id)
    assert loaded.values["当前阶段"] == "一面 2026-08-01"
    assert len(second.provenance(app.application_id, "当前阶段")) == 2
    assert second.create("Ignored", "Ignored", idempotency_key="application-1").application_id == (
        app.application_id
    )
    with pytest.raises(ValueError, match="version conflict"):
        second.apply_field_change(
            app.application_id,
            "备注",
            "stale edit",
            source="user",
            idempotency_key="stale",
            expected_version=1,
        )


def test_excel_database_round_trip_and_user_edit(tmp_path: Path) -> None:
    database = Database(tmp_path / "careerpilot.db")
    applications = ApplicationService(database)
    sync = ExcelSyncService(database, applications)
    source = tmp_path / "source.xlsx"
    row = TrackerRow(values={**dict.fromkeys(COLUMNS), "公司名称": "Acme", "岗位": "Engineer"})
    write_tracker(source, [row])

    sync.import_workbook(source, "import-1")
    output = tmp_path / "tracker.xlsx"
    sync.export_workbook(output)
    [exported] = read_tracker(output)
    assert exported.values["公司名称"] == "Acme"

    exported.values["备注"] = "user note"
    write_tracker(output, [exported])
    sync.import_workbook(output, "import-2")
    assert applications.get(row.application_id).values["备注"] == "user note"


def test_job_checkpoint_persists(tmp_path: Path) -> None:
    path = tmp_path / "careerpilot.db"
    jobs = JobService(Database(path))
    job = jobs.create("excel_sync", "same-input")
    jobs.progress(job.job_id, "validated", {"rows": 1})

    restarted = JobService(Database(path))
    loaded = restarted.get(job.job_id)
    assert loaded.current_step == "validated"
    assert loaded.checkpoint == {"rows": 1}
    assert restarted.create("excel_sync", "same-input").job_id == job.job_id


def test_alembic_upgrades_empty_database(tmp_path: Path) -> None:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    database = tmp_path / "migrated.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "head")
    assert ApplicationService(Database(database)).list() == []


def test_application_and_excel_job_api(tmp_path: Path) -> None:
    tracker = tmp_path / "tracker.xlsx"
    row = TrackerRow(values={**dict.fromkeys(COLUMNS), "公司名称": "API Co", "岗位": "Dev"})
    write_tracker(tracker, [row])
    client = TestClient(create_app(data_dir=tmp_path))
    response = client.post(
        "/api/v1/excel-sync-jobs",
        json={"path": "tracker.xlsx", "direction": "import", "idempotency_key": "api-import"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/applications").json()[0]["company"] == "API Co"
    assert client.get(f"/api/v1/jobs/{response.json()['job_id']}").json()["current_step"] == (
        "completed"
    )
