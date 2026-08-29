from pathlib import Path

from fastapi.testclient import TestClient

from careerpilot.api import create_app


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
    assert (
        client.put(
            f"/api/v1/applications/{application['application_id']}/resume/{second['version_id']}"
        ).status_code
        == 200
    )
    versions = client.get("/api/v1/resumes").json()
    assert next(item for item in versions if item["version"] == 1)["application_ids"] == []
    assert next(item for item in versions if item["version"] == 2)["application_ids"] == [
        application["application_id"]
    ]

    assert client.delete(f"/api/v1/resumes/{first['resume_id']}?confirmed=true").status_code == 204
    assert client.get("/api/v1/resumes").json() == []
    assert list((tmp_path / "resumes").iterdir()) == []
