from pathlib import Path

from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.excel import COLUMNS, RESUME_COLUMN, read_tracker
from careerpilot.safe_files import MAX_RESUME_BYTES


def test_resume_versions_current_assignment_and_permanent_delete(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    application = client.post(
        "/api/v1/applications",
        json={"company": "Example", "role": "Developer", "idempotency_key": "app"},
    ).json()

    first = client.post(
        "/api/v1/resumes?filename=resume.txt&label=Backend",
        content=b"first resume",
        headers={"content-type": "text/plain"},
    ).json()
    second = client.post(
        f"/api/v1/resumes?filename=resume.txt&label=Backend&resume_id={first['resume_id']}",
        content=b"second resume",
        headers={"content-type": "text/plain"},
    ).json()

    assert second["version"] == 2
    assert (
        client.put(
            f"/api/v1/applications/{application['application_id']}/resume/{first['version_id']}"
        ).status_code
        == 200
    )
    [row] = read_tracker(tmp_path / "tracker.xlsx")
    assert row.values[RESUME_COLUMN] == "Backend@v1"
    assert (
        client.put(
            f"/api/v1/applications/{application['application_id']}/resume/{second['version_id']}"
        ).status_code
        == 200
    )
    [row] = read_tracker(tmp_path / "tracker.xlsx")
    assert row.values[RESUME_COLUMN] == "Backend@v2"
    updated = client.patch(
        f"/api/v1/applications/{application['application_id']}",
        json={
            "changes": {COLUMNS[-1]: "frontend edit"},
            "expected_version": client.get(
                f"/api/v1/applications/{application['application_id']}"
            ).json()["version"],
            "idempotency_key": "edit",
        },
    )
    assert updated.status_code == 200, updated.text
    [row] = read_tracker(tmp_path / "tracker.xlsx")
    assert row.values[COLUMNS[-1]] == "frontend edit"
    versions = client.get("/api/v1/resumes").json()
    assert next(item for item in versions if item["version"] == 1)["application_ids"] == []
    assert next(item for item in versions if item["version"] == 2)["application_ids"] == [
        application["application_id"]
    ]

    assert client.delete(f"/api/v1/resumes/{first['resume_id']}?confirmed=true").status_code == 204
    [row] = read_tracker(tmp_path / "tracker.xlsx")
    assert row.values[RESUME_COLUMN] is None
    assert client.get("/api/v1/resumes").json() == []
    assert list((tmp_path / "resumes").iterdir()) == []


def test_resume_upload_rejects_unsafe_files(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    wrong_type = client.post(
        "/api/v1/resumes?filename=resume.pdf&label=Backend",
        content=b"not a pdf",
        headers={"content-type": "application/pdf"},
    )
    assert wrong_type.status_code == 422

    oversized = client.post(
        "/api/v1/resumes?filename=resume.txt&label=Backend",
        content=b"x" * (MAX_RESUME_BYTES + 1),
        headers={"content-type": "text/plain"},
    )
    assert oversized.status_code == 413
    assert not (tmp_path / "resumes").exists()
