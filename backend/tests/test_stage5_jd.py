from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from careerpilot.api import create_app
from careerpilot.core import ApplicationService, Database, ExcelSyncService, JobService
from careerpilot.excel import write_tracker
from careerpilot.jd import JDService

JD = "必须熟悉 Python。负责 API 开发。"
RESULT = {
    "requirements": [
        {
            "text": "熟悉 Python",
            "quote": "必须熟悉 Python",
            "importance": "critical",
            "origin": "explicit",
            "reason": "原文明确必须",
        }
    ],
    "unknowns": ["薪资未提供"],
}
CONFIG = {"model": "fixture", "base_url": "https://model.example/v1", "credential": None}


class Model:
    def __init__(self):
        self.calls = []
        self.result = deepcopy(RESULT)

    def generate(self, payload, **kwargs):
        self.calls.append(payload)
        return self.result


def test_jd_reuse_and_resume_independence_and_deletion(tmp_path: Path):
    db = Database(tmp_path / "careerpilot.db")
    apps = ApplicationService(db)
    app = apps.create("Acme", "Engineer", idempotency_key="create")
    model = Model()
    service = JDService(db, model)
    first = service.run(app.application_id, JD, **CONFIG)
    apps.apply_field_change(
        app.application_id,
        "备注",
        "Different candidate resume facts",
        source="user",
        idempotency_key="cv",
    )
    assert service.run(app.application_id, JD, **CONFIG) == first
    assert len(model.calls) == 1
    assert set(model.calls[0]) == {"jd", "_output_schema", "_instructions"}
    assert JDService(Database(tmp_path / "careerpilot.db"), model).list(app.application_id) == [
        first
    ]
    tracker = tmp_path / "tracker.xlsx"
    write_tracker(tracker, [])
    ExcelSyncService(db, apps).import_workbook(tracker, "delete")
    assert JobService(db).list() == []
    with pytest.raises(KeyError):
        service.run(app.application_id, JD, **CONFIG)


@pytest.mark.parametrize(
    "change", [{"quote": "fiction"}, {"origin": "inferred"}, {"importance": "invalid"}]
)
def test_invalid_output_is_not_published_and_can_retry(tmp_path: Path, change):
    db = Database(tmp_path / "careerpilot.db")
    app = ApplicationService(db).create("Acme", "Engineer", idempotency_key="create")
    model = Model()
    model.result["requirements"][0].update(change)
    service = JDService(db, model)
    with pytest.raises(ValueError):
        service.run(app.application_id, JD, **CONFIG)
    assert service.list(app.application_id) == []
    assert JobService(db).list()[0].status == "failed"
    model.result = deepcopy(RESULT)
    assert service.run(app.application_id, JD, **CONFIG)["analysis"] == RESULT
    assert len(JobService(db).list()) == 1
    recovered = JobService(db).list()[0]
    assert recovered.error_code is None
    assert recovered.error_message_safe is None


def test_jd_api_requires_confirmation_and_returns_persisted_report(tmp_path: Path):
    class Secrets:
        def get(self, *args):
            return None

        def get_named(self, *args):
            return None

    model = Model()
    client = TestClient(create_app(data_dir=tmp_path, model_client=model, secret_store=Secrets()))
    app = client.post(
        "/api/v1/applications",
        json={"company": "Acme", "role": "Engineer", "idempotency_key": "create"},
    ).json()
    settings = {
        k: v for k, v in client.get("/api/v1/settings").json().items() if not k.endswith("_saved")
    }
    settings.update(model_base_url=CONFIG["base_url"], model_name=CONFIG["model"])
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    url = f"/api/v1/applications/{app['application_id']}/jd-analyses"
    assert client.post(url, json={"jd": JD, "data_leaving_confirmed": False}).status_code == 422
    assert client.post(url, json={"jd": "  ", "data_leaving_confirmed": True}).status_code == 422
    assert model.calls == []
    response = client.post(url, json={"jd": JD, "data_leaving_confirmed": True})
    assert response.status_code == 200, response.text
    assert client.get(url).json() == [response.json()]


def test_changed_jd_or_model_does_not_reuse_stale_analysis(tmp_path: Path):
    db = Database(tmp_path / "careerpilot.db")
    app = ApplicationService(db).create("Acme", "Engineer", idempotency_key="create")
    model = Model()
    service = JDService(db, model)
    reports = [
        service.run(app.application_id, JD, **CONFIG),
        service.run(app.application_id, JD + "需要沟通能力。", **CONFIG),
        service.run(app.application_id, JD, **{**CONFIG, "model": "other-model"}),
        service.run(app.application_id, JD, **{**CONFIG, "base_url": "https://other.example/v1"}),
    ]
    assert len({item["job_id"] for item in reports}) == 4
    assert len(model.calls) == 4
    assert len(service.list(app.application_id)) == 4


@pytest.mark.parametrize(
    "result",
    [
        {"requirements": [], "unknowns": []},
        {**RESULT, "score": 5},
        {"requirements": [{**RESULT["requirements"][0], "quote": "   "}], "unknowns": []},
    ],
)
def test_empty_or_out_of_scope_model_outputs_are_not_published(tmp_path: Path, result):
    db = Database(tmp_path / "careerpilot.db")
    app = ApplicationService(db).create("Acme", "Engineer", idempotency_key="create")
    model = Model()
    model.result = result
    service = JDService(db, model)
    with pytest.raises(ValueError):
        service.run(app.application_id, JD, **CONFIG)
    assert service.list(app.application_id) == []


def test_model_timeout_can_retry_after_process_restart(tmp_path: Path):
    class TimeoutModel:
        def generate(self, *args, **kwargs):
            raise TimeoutError("private provider diagnostic")

    db = Database(tmp_path / "careerpilot.db")
    app = ApplicationService(db).create("Acme", "Engineer", idempotency_key="create")
    with pytest.raises(TimeoutError):
        JDService(db, TimeoutModel()).run(app.application_id, JD, **CONFIG)
    failed = JobService(db).list()[0]
    assert "private provider diagnostic" not in failed.error_message_safe
    restarted = Database(tmp_path / "careerpilot.db")
    report = JDService(restarted, Model()).run(app.application_id, JD, **CONFIG)
    assert report["job_id"] == str(failed.job_id)
    assert JobService(restarted).get(failed.job_id).error_code is None
