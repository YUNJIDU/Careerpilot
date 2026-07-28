from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.core import ApplicationService, Database, EmailService


class MemorySecrets:
    def __init__(self) -> None:
        self.mail: dict[tuple[str, str], str] = {}
        self.named: dict[str, str] = {}

    def get(self, account_id: str, email: str) -> str | None:
        return self.mail.get((account_id, email))

    def set(self, account_id: str, email: str, value: str) -> None:
        self.mail[(account_id, email)] = value

    def get_named(self, name: str) -> str | None:
        return self.named.get(name)

    def set_named(self, name: str, value: str) -> None:
        self.named[name] = value


def test_application_create_update_detail_and_conflict(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, secret_store=MemorySecrets()))
    created = client.post(
        "/api/v1/applications",
        json={
            "company": "Acme",
            "role": "Engineer",
            "idempotency_key": "create-acme",
        },
    )
    assert created.status_code == 201
    application = created.json()
    application_id = application["application_id"]
    assert (
        client.post(
            "/api/v1/applications",
            json={
                "company": "Acme",
                "role": "Engineer",
                "idempotency_key": "create-acme",
            },
        ).json()["application_id"]
        == application_id
    )

    updated = client.patch(
        f"/api/v1/applications/{application_id}",
        json={
            "changes": {"当前阶段": "一面", "备注": "人工备注"},
            "expected_version": 1,
            "idempotency_key": "edit-acme",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 3
    assert updated.json()["values"]["备注"] == "人工备注"
    conflict = client.patch(
        f"/api/v1/applications/{application_id}",
        json={
            "changes": {"备注": "过期写入"},
            "expected_version": 1,
            "idempotency_key": "stale",
        },
    )
    assert conflict.status_code == 409
    invalid_change = client.patch(
        f"/api/v1/applications/{application_id}",
        json={
            "changes": {"备注": "不应部分写入", "unknown": "x"},
            "expected_version": 3,
            "idempotency_key": "invalid-fields",
        },
    )
    assert invalid_change.status_code == 422
    assert client.get(f"/api/v1/applications/{application_id}").json()["values"]["备注"] == "人工备注"

    EmailService(Database(tmp_path / "careerpilot.db")).record(
        account_id="personal",
        raw_hash="a" * 64,
        message_id="<detail@example>",
        subject="面试邀请",
        sender="jobs@example.com",
        sent_at=datetime(2026, 7, 28, tzinfo=UTC),
        application_id=ApplicationService(Database(tmp_path / "careerpilot.db"))
        .get(UUID(application_id))
        .application_id,
        facts={"当前阶段": "一面"},
    )
    detail = client.get(f"/api/v1/applications/{application_id}").json()
    assert len(detail["timeline"]) == 2
    assert {item["field"] for item in detail["provenance"]} == {"当前阶段", "备注"}
    assert detail["emails"][0]["subject"] == "面试邀请"
    assert detail["values"]["备注"] == "人工备注"

    assert client.get(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000"
    ).status_code == 404
    assert client.post(
        "/api/v1/applications",
        json={"company": "", "role": "Engineer", "idempotency_key": "invalid"},
    ).status_code == 422
    assert client.post(
        "/api/v1/applications",
        json={"company": "   ", "role": "Engineer", "idempotency_key": "spaces"},
    ).status_code == 422

    service = ApplicationService(Database(tmp_path / "careerpilot.db"))
    service.apply_field_change(
        UUID(application_id),
        "公司名称",
        "Imported name",
        source="mail",
        idempotency_key="later-mail-company",
    )
    assert service.get(UUID(application_id)).company == "Acme"


def test_settings_are_atomic_scoped_and_never_echo_secrets(tmp_path: Path) -> None:
    secrets = MemorySecrets()
    client = TestClient(create_app(data_dir=tmp_path, secret_store=secrets))
    sentinel = "SECRET_SENTINEL_9284"
    payload = {
        "account_id": "personal",
        "email": "me@163.com",
        "tracker_path": "tracker.xlsx",
        "markdown_path": "markdown",
        "model_base_url": "http://127.0.0.1:11434/v1",
        "model_name": "local-model",
        "scheduling_enabled": False,
        "mail_secret": f"mail-{sentinel}",
        "model_secret": f"model-{sentinel}",
        "brave_secret": f"brave-{sentinel}",
    }
    response = client.put("/api/v1/settings", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["mail_secret_saved"]
    assert body["model_secret_saved"]
    assert body["brave_secret_saved"]
    assert sentinel not in str(body)
    assert sentinel not in (tmp_path / "settings.json").read_text(encoding="utf-8")

    restarted = TestClient(create_app(data_dir=tmp_path, secret_store=secrets))
    assert restarted.get("/api/v1/settings").json()["model_name"] == "local-model"
    assert restarted.put(
        "/api/v1/settings",
        json={**payload, "tracker_path": "../outside.xlsx"},
    ).status_code == 422


def test_jobs_list_excel_completion_and_validation(tmp_path: Path) -> None:
    fresh_data = tmp_path / "fresh" / "data"
    client = TestClient(create_app(data_dir=fresh_data, secret_store=MemorySecrets()))
    assert (fresh_data / "careerpilot.db").exists()
    invalid = client.post(
        "/api/v1/excel-sync-jobs",
        json={"path": "tracker.xlsx", "direction": "sideways", "idempotency_key": "bad"},
    )
    assert invalid.status_code == 422

    exported = client.post(
        "/api/v1/excel-sync-jobs",
        json={"path": "tracker.xlsx", "direction": "export", "idempotency_key": "out"},
    )
    assert exported.status_code == 200
    jobs = client.get("/api/v1/jobs").json()
    succeeded = next(item for item in jobs if item["job_id"] == exported.json()["job_id"])
    assert succeeded["status"] == "succeeded"
    assert not succeeded["retryable"]
    assert "secret" not in str(jobs).lower()
