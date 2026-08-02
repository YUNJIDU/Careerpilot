import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError

from careerpilot.api import create_app
from careerpilot.contracts import ApplicationSnapshot
from careerpilot.core import upgrade_database
from careerpilot.extensions import DeferredService
from careerpilot.security import escape_excel_formula, mark_untrusted, redact, safe_path


def test_health_and_local_cors(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    assert client.get("/api/v1/health").json()["status"] == "ok"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://127.0.0.1:9999",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:9999"


def test_contract_requires_timezone() -> None:
    ApplicationSnapshot(company="Acme", role="Engineer", updated_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        ApplicationSnapshot(
            company="Acme",
            role="Engineer",
            updated_at=datetime(2026, 1, 1),  # noqa: DTZ001 - deliberate invalid input
        )


def test_security_boundaries(tmp_path: Path) -> None:
    assert safe_path(tmp_path, Path("attachments/a.pdf")).is_relative_to(tmp_path)
    with pytest.raises(ValueError):
        safe_path(tmp_path, Path("../secret"))
    assert escape_excel_formula("=1+1") == "'=1+1"
    assert "[REDACTED]" in redact("api_key=secret")
    assert "[REDACTED_EMAIL]" in redact("me@example.com")
    assert mark_untrusted("ignore instructions")["trusted"] is False


def test_deferred_service_is_explicit() -> None:
    with pytest.raises(NotImplementedError):
        DeferredService().run()


def _migration_config(path: Path) -> Config:
    backend = Path(__file__).parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def test_initial_migration_is_frozen_and_legacy_schema_is_verified(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "fresh.db"
    config = _migration_config(fresh)
    command.upgrade(config, "0001")
    with sqlite3.connect(fresh) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "applications" in tables
    assert "summary_versions" not in tables
    assert "mail_accounts" not in tables

    command.upgrade(config, "0002")
    with sqlite3.connect(fresh) as connection:
        connection.execute("DROP TABLE alembic_version")
    upgrade_database(fresh)
    with sqlite3.connect(fresh) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0009",
        )

    invalid = tmp_path / "invalid.db"
    with sqlite3.connect(invalid) as connection:
        connection.execute("CREATE TABLE applications (application_id TEXT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="does not match CareerPilot 0002"):
        upgrade_database(invalid)
    with sqlite3.connect(invalid) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'alembic_version'"
        ).fetchone() is None
