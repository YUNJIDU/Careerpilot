from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from careerpilot.api import create_app
from careerpilot.contracts import ApplicationSnapshot
from careerpilot.extensions import DeferredService
from careerpilot.security import escape_excel_formula, mark_untrusted, redact, safe_path


def test_health_and_local_cors() -> None:
    client = TestClient(create_app())
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
