import sqlite3
from datetime import date
from pathlib import Path
from typing import ClassVar

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.secrets import EnvironmentSecretStore
from careerpilot.settings import SettingsStore


class MemorySecrets:
    writable = True

    def __init__(self) -> None:
        self.mail: dict[tuple[str, str], str] = {}

    def get(self, account_id: str, email: str) -> str | None:
        return self.mail.get((account_id, email))

    def set(self, account_id: str, email: str, value: str) -> None:
        self.mail[(account_id, email)] = value

    def get_named(self, name: str) -> None:
        return None

    def set_named(self, name: str, value: str) -> None:
        pass


class RecordingAdapter:
    calls: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, email: str, code: str, **kwargs: object) -> None:
        self.email = email
        self.code = code

    def test_connection(self) -> None:
        self.calls.append((self.email, self.code))

    def fetch(self) -> list[object]:
        self.calls.append((self.email, self.code))
        return []


def _upgrade_to_0002(path: Path) -> None:
    backend = Path(__file__).parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "0002")
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE IF EXISTS mail_accounts")
        connection.execute(
            "INSERT INTO sync_batches "
            "(batch_id, batch_type, idempotency_key, baseline, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("legacy-batch", "excel", "legacy-key", "{}", "2026-01-01 00:00:00"),
        )


def test_legacy_single_mailbox_is_backed_up_migrated_and_kept(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "careerpilot.db"
    _upgrade_to_0002(database_path)
    SettingsStore(data_dir).save(
        {
            "account_id": "personal",
            "email": "Me@163.com",
            "tracker_path": "tracker.xlsx",
            "markdown_path": "markdown",
            "model_base_url": "",
            "model_name": "",
            "scheduling_enabled": False,
        }
    )
    secrets = MemorySecrets()
    secrets.set("personal", "me@163.com", "legacy-code")

    client = TestClient(create_app(data_dir=data_dir, secret_store=secrets))

    [account] = client.get("/api/v1/mail-accounts").json()
    assert account == {
        **account,
        "account_id": "personal",
        "adapter": "imap163",
        "email": "me@163.com",
        "enabled": True,
        "credential_saved": True,
    }
    backup = data_dir / "careerpilot.db.pre-0003.bak"
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0002",
        )
        assert connection.execute(
            "SELECT idempotency_key FROM sync_batches"
        ).fetchone() == ("legacy-key",)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0009",
        )
        assert connection.execute(
            "SELECT idempotency_key FROM sync_batches"
        ).fetchone() == ("legacy-key",)


def test_multiple_accounts_keep_credentials_scoped_and_never_echo_them(
    tmp_path: Path,
) -> None:
    RecordingAdapter.calls = []
    secrets = MemorySecrets()
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            secret_store=secrets,
            mail_adapter_factory=RecordingAdapter,
        )
    )
    credentials = {"personal": "PERSONAL_SECRET", "school": "SCHOOL_SECRET"}
    for account_id, secret in credentials.items():
        response = client.put(
            f"/api/v1/mail-accounts/{account_id}",
            json={
                "email": f"{account_id}@163.com",
                "authorization_code": secret,
            },
        )
        assert response.status_code == 200
        assert response.json()["credential_saved"]
        assert secret not in response.text

    assert client.put(
        "/api/v1/mail-accounts/duplicate",
        json={"email": "personal@163.com"},
    ).status_code == 409
    assert client.put(
        "/api/v1/mail-accounts/personal",
        json={"email": "changed@163.com"},
    ).status_code == 409

    for account_id in credentials:
        assert client.post(f"/api/v1/mail-accounts/{account_id}/test").status_code == 200
        synced = client.post(
            f"/api/v1/mail-accounts/{account_id}/sync-jobs",
            json={
                "since": date(2026, 1, 1).isoformat(),
                "limit": 10,
                "tracker_path": "tracker.xlsx",
                "idempotency_key": f"sync-{account_id}",
            },
        )
        assert synced.status_code == 200

    assert RecordingAdapter.calls == [
        ("personal@163.com", "PERSONAL_SECRET"),
        ("personal@163.com", "PERSONAL_SECRET"),
        ("school@163.com", "SCHOOL_SECRET"),
        ("school@163.com", "SCHOOL_SECRET"),
    ]
    database_bytes = (tmp_path / "careerpilot.db").read_bytes()
    settings_bytes = (tmp_path / "settings.json").read_bytes() if (tmp_path / "settings.json").exists() else b""
    for secret in credentials.values():
        assert secret.encode() not in database_bytes
        assert secret.encode() not in settings_bytes
    jobs = client.get("/api/v1/jobs").json()
    assert all("email" not in (job["checkpoint"] or {}) for job in jobs)

    disabled = client.patch(
        "/api/v1/mail-accounts/school", json={"enabled": False}
    )
    assert disabled.json()["enabled"] is False
    assert client.post("/api/v1/mail-accounts/school/test").status_code == 409
    restarted = TestClient(create_app(data_dir=tmp_path, secret_store=secrets))
    assert len(restarted.get("/api/v1/mail-accounts").json()) == 2


def test_environment_mail_secrets_are_scoped_per_account(monkeypatch) -> None:
    monkeypatch.setenv("CAREERPILOT_MAIL_SECRET", "legacy")
    monkeypatch.setenv("CAREERPILOT_MAIL_SECRET_SCHOOL", "school")
    store = EnvironmentSecretStore()

    assert store.get("personal", "personal@163.com") == "legacy"
    assert store.get("school", "school@163.com") == "school"
    assert store.get("other", "other@163.com") is None


def test_mail_connection_endpoints_return_safe_authentication_error(tmp_path: Path) -> None:
    sentinel = "ADAPTER_DETAIL_SENTINEL_9284"

    class RejectingAdapter:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def test_connection(self) -> None:
            raise PermissionError(sentinel)

    secrets = MemorySecrets()
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            secret_store=secrets,
            mail_adapter_factory=RejectingAdapter,
        )
    )
    client.put(
        "/api/v1/mail-accounts/personal",
        json={"email": "me@163.com", "authorization_code": "not-logged"},
    )

    registered = client.post("/api/v1/mail-accounts/personal/test")
    legacy = client.post(
        "/api/v1/mail-accounts/test",
        json={
            "account_id": "personal",
            "email": "me@163.com",
            "since": "2026-01-01",
            "limit": 1,
        },
    )

    for response in (registered, legacy):
        assert response.status_code == 401
        assert response.json() == {"detail": "163 authentication failed"}
        assert sentinel not in response.text
