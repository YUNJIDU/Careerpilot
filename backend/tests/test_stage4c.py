from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.core import Database, JobService
from careerpilot.secrets import EnvironmentSecretStore


class MemorySecrets:
    writable = True

    def get(self, account_id: str, email: str) -> str | None:
        return None

    def set(self, account_id: str, email: str, value: str) -> None:
        pass

    def get_named(self, name: str) -> str | None:
        return None

    def set_named(self, name: str, value: str) -> None:
        pass


def test_environment_config_and_static_frontend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "runtime-data"
    static_dir = tmp_path / "frontend"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<h1>CareerPilot Docker</h1>", encoding="utf-8")
    monkeypatch.setenv("CAREERPILOT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CAREERPILOT_FRONTEND_ORIGIN", "http://127.0.0.1:9999")
    monkeypatch.setenv("CAREERPILOT_STATIC_DIR", str(static_dir))

    client = TestClient(create_app(secret_store=MemorySecrets()))

    assert (data_dir / "careerpilot.db").is_file()
    assert "CareerPilot Docker" in client.get("/").text
    response = client.get(
        "/api/v1/health", headers={"Origin": "http://127.0.0.1:9999"}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:9999"


def test_runtime_secrets_support_environment_and_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mail_file = tmp_path / "mail-secret"
    mail_file.write_text("mail-value\n", encoding="utf-8")
    tavily_file = tmp_path / "tavily-secret"
    tavily_file.write_text("tavily-value\n", encoding="utf-8")
    monkeypatch.setenv("CAREERPILOT_MAIL_SECRET_FILE", str(mail_file))
    monkeypatch.setenv("CAREERPILOT_MODEL_SECRET", "model-value")
    monkeypatch.setenv("CAREERPILOT_TAVILY_SECRET_FILE", str(tavily_file))
    store = EnvironmentSecretStore()

    assert store.get("personal", "me@163.com") == "mail-value"
    assert store.get_named("model") == "model-value"
    assert store.get_named("tavily") == "tavily-value"
    client = TestClient(create_app(data_dir=tmp_path / "data", secret_store=store))
    rejected = client.put(
        "/api/v1/settings",
        json={
            "account_id": "personal",
            "email": "me@163.com",
            "tracker_path": "tracker.xlsx",
            "markdown_path": "markdown",
            "model_base_url": "",
            "model_name": "",
            "scheduling_enabled": False,
            "mail_secret": "must-not-be-stored",
        },
    )
    assert rejected.status_code == 409
    assert not (tmp_path / "data" / "settings.json").exists()

    settings = client.put(
        "/api/v1/settings",
        json={
            "account_id": "personal",
            "email": "me@163.com",
            "tracker_path": "tracker.xlsx",
            "markdown_path": "markdown",
            "model_base_url": "",
            "model_name": "",
            "scheduling_enabled": False,
        },
    )
    assert settings.status_code == 200
    assert settings.json()["mail_secret_saved"]
    assert settings.json()["model_secret_saved"]
    assert settings.json()["tavily_secret_saved"]
    assert "mail-value" not in settings.text
    assert "model-value" not in settings.text
    assert "tavily-value" not in settings.text


def test_interrupted_excel_job_recovers_and_default_path_is_scoped(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    database = Database(data_dir / "careerpilot.db")
    jobs = JobService(database)
    interrupted = jobs.create("excel_sync", "interrupted-excel")
    jobs.progress(
        interrupted.job_id,
        "configured",
        {"path": "tracker.xlsx", "direction": "export"},
    )
    database.engine.dispose()

    client = TestClient(create_app(data_dir=data_dir, secret_store=MemorySecrets()))
    failed = client.get(f"/api/v1/jobs/{interrupted.job_id}").json()
    assert failed["status"] == "failed"
    assert failed["error_code"] == "job.interrupted"
    assert failed["retryable"]

    resumed = client.post(f"/api/v1/jobs/{interrupted.job_id}/resume")
    assert resumed.status_code == 200
    recovered = client.get(f"/api/v1/jobs/{interrupted.job_id}").json()
    assert recovered["status"] == "succeeded"
    assert recovered["current_step"] == "resumed"
    assert not recovered["retryable"]
    assert recovered["error_code"] is None
    assert recovered["checkpoint"]["resumed_job_id"] == resumed.json()["job_id"]
    assert (data_dir / "tracker.xlsx").is_file()
    assert not (data_dir / "data" / "tracker.xlsx").exists()

    default_export = client.post(
        "/api/v1/excel-sync-jobs",
        json={"direction": "export", "idempotency_key": "default-export"},
    )
    assert default_export.status_code == 200
