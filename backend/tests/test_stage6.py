import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from careerpilot.api import create_app


class MemorySecrets:
    writable = True

    def get(self, account_id: str, email: str) -> None:
        return None

    def set(self, account_id: str, email: str, value: str) -> None:
        pass

    def get_named(self, name: str) -> str | None:
        return "model-secret" if name == "model" else None

    def set_named(self, name: str, value: str) -> None:
        pass


class ScriptedAgentModel:
    def __init__(self, mode: str = "read") -> None:
        self.mode = mode
        self.calls = 0

    def generate_structured(self, payload: dict, **configuration: object) -> dict:
        assert configuration["base_url"] == "https://model.example/v1"
        assert configuration["model"] == "stage6-model"
        assert configuration["credential"] == "model-secret"
        self.calls += 1
        history = payload["history"]
        if self.mode == "invalid":
            return {
                "action": "tool",
                "tool_name": "shell.execute",
                "arguments": {},
                "reason": "Ignore previous instructions",
            }
        if self.mode == "cross_scope":
            return {
                "action": "tool",
                "tool_name": "application.read",
                "arguments": {"application_id": "another-application"},
                "reason": "try another application",
            }
        if not history:
            return {
                "action": "tool",
                "tool_name": "application.read",
                "arguments": {"application_id": payload["application_id"]},
                "reason": "read the bound application",
                "summary": "",
                "facts": [],
                "unknowns": ["inactive tool-action placeholder"],
                "next_questions": [],
            }
        if self.mode in {"write", "reject"} and not any(
            item["tool_name"] == "application.append_note" for item in history
        ):
            application = history[0]["result"]
            return {
                "action": "tool",
                "tool_name": "application.append_note",
                "arguments": {
                    "text": "待核实：请确认项目中的 SQL 使用范围。",
                    "expected_version": application["version"],
                    "source_ids": [history[0]["source_ids"][0]],
                },
                "reason": "user explicitly requested a note",
            }
        if self.mode == "loop":
            return {
                "action": "tool",
                "tool_name": "application.read",
                "arguments": {},
                "reason": "keep reading",
            }
        source_id = history[-1]["source_ids"][0] if history[-1]["source_ids"] else history[0]["source_ids"][0]
        return {
            "action": "final",
            "summary": "已基于当前岗位材料完成整理。",
            "facts": [
                {
                    "statement": "岗位记录已读取",
                    "source_id": source_id,
                    "locator": "当前岗位记录",
                }
            ],
            "unknowns": ["未提供的内容保持未知"],
            "next_questions": ["是否需要继续补充可核实证据？"],
        }

    def generate(self, payload: dict, **configuration: object) -> dict:
        raise AssertionError("Stage 6 must use the structured model contract")


def configured_client(tmp_path: Path, model: ScriptedAgentModel) -> TestClient:
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            secret_store=MemorySecrets(),
            model_client=model,
        )
    )
    response = client.put(
        "/api/v1/settings",
        json={
            "account_id": "personal",
            "email": "",
            "tracker_path": "tracker.xlsx",
            "markdown_path": "markdown",
            "model_base_url": "https://model.example/v1",
            "model_name": "stage6-model",
            "scheduling_enabled": False,
        },
    )
    assert response.status_code == 200
    return client


def create_application(client: TestClient, key: str = "stage6-app") -> dict:
    response = client.post(
        "/api/v1/applications",
        json={"company": "Acme", "role": "Engineer", "idempotency_key": key},
    )
    assert response.status_code == 201
    return response.json()


def start_run(
    client: TestClient,
    application_id: str,
    *,
    key: str = "stage6-run",
    limits: dict | None = None,
) -> object:
    return client.post(
        f"/api/v1/applications/{application_id}/agent-runs",
        json={
            "request_text": "整理当前岗位现有证据",
            "idempotency_key": key,
            "data_leaving_confirmed": True,
            **({"limits": limits} if limits else {}),
        },
    )


def test_read_only_agent_has_cited_output_and_audit(tmp_path: Path) -> None:
    model = ScriptedAgentModel()
    client = configured_client(tmp_path, model)
    application = create_application(client)

    denied = client.post(
        f"/api/v1/applications/{application['application_id']}/agent-runs",
        json={
            "request_text": "read",
            "idempotency_key": "denied",
            "data_leaving_confirmed": False,
        },
    )
    assert denied.status_code == 422

    response = start_run(client, application["application_id"])
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "succeeded"
    assert run["usage"]["steps"] == 2
    assert run["usage"]["model_calls"] == 2
    assert run["usage"]["tool_calls"] == 1
    assert run["usage"]["write_approvals"] == 0
    assert run["usage"]["elapsed_ms"] >= 0
    assert run["tool_calls"][0]["tool_name"] == "application.read"
    assert run["final_output"]["facts"][0]["source_id"] in run["tool_calls"][0]["result_refs"]
    assert run["approvals"] == []
    listed = client.get(
        f"/api/v1/applications/{application['application_id']}/agent-runs"
    ).json()
    assert listed[0]["run_id"] == run["run_id"]


def test_note_write_waits_for_approval_is_idempotent_and_survives_restart(
    tmp_path: Path,
) -> None:
    model = ScriptedAgentModel("write")
    client = configured_client(tmp_path, model)
    application = create_application(client)
    response = start_run(client, application["application_id"], key="write-run")
    assert response.status_code == 201
    waiting = response.json()
    assert waiting["status"] == "waiting_approval"
    assert client.get(f"/api/v1/applications/{application['application_id']}").json()["values"]["备注"] is None
    assert waiting["approvals"][0]["status"] == "pending"

    restarted = configured_client(tmp_path, model)
    persisted = restarted.get(f"/api/v1/agent-runs/{waiting['run_id']}").json()
    assert persisted["status"] == "waiting_approval"
    approval_id = persisted["approvals"][0]["approval_id"]
    approved = restarted.post(
        f"/api/v1/agent-runs/{waiting['run_id']}/approvals/{approval_id}",
        json={"decision": "approved", "decision_note": None},
    )
    assert approved.status_code == 200
    completed = approved.json()
    assert completed["status"] == "succeeded"
    saved = restarted.get(f"/api/v1/applications/{application['application_id']}").json()
    assert saved["values"]["备注"] == "待核实：请确认项目中的 SQL 使用范围。"
    assert saved["version"] == 2

    duplicate = restarted.post(
        f"/api/v1/agent-runs/{waiting['run_id']}/approvals/{approval_id}",
        json={"decision": "approved", "decision_note": None},
    )
    assert duplicate.status_code == 200
    assert restarted.get(f"/api/v1/applications/{application['application_id']}").json()["version"] == 2

    with sqlite3.connect(tmp_path / "careerpilot.db") as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0009",)
    with sqlite3.connect(tmp_path / "careerpilot.db.pre-0008.bak") as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0007",)


def test_rejected_write_never_changes_business_data(tmp_path: Path) -> None:
    model = ScriptedAgentModel("reject")
    client = configured_client(tmp_path, model)
    application = create_application(client)
    waiting = start_run(client, application["application_id"], key="reject-run").json()
    approval_id = waiting["approvals"][0]["approval_id"]
    response = client.post(
        f"/api/v1/agent-runs/{waiting['run_id']}/approvals/{approval_id}",
        json={"decision": "rejected", "decision_note": "not wanted"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    saved = client.get(f"/api/v1/applications/{application['application_id']}").json()
    assert saved["values"]["备注"] is None
    assert saved["version"] == 1


def test_unknown_and_cross_scope_tools_fail_without_execution(tmp_path: Path) -> None:
    for index, mode in enumerate(("invalid", "cross_scope")):
        client = configured_client(tmp_path / mode, ScriptedAgentModel(mode))
        application = create_application(client, f"app-{mode}")
        response = start_run(
            client, application["application_id"], key=f"run-{mode}-{index}"
        )
        assert response.status_code == 502
        assert response.json()["detail"]["code"] in {
            "agent.unknown_tool",
            "agent.tool_arguments_invalid",
        }
        saved = client.get(f"/api/v1/applications/{application['application_id']}").json()
        assert saved["version"] == 1


def test_budget_exhaustion_stops_loop_and_cancel_rejects_pending_write(
    tmp_path: Path,
) -> None:
    client = configured_client(tmp_path / "budget", ScriptedAgentModel("loop"))
    application = create_application(client)
    exhausted = start_run(
        client,
        application["application_id"],
        limits={
            "max_steps": 2,
            "max_model_calls": 2,
            "max_tool_calls": 1,
            "max_write_approvals": 0,
            "max_elapsed_seconds": 30,
        },
    ).json()
    assert exhausted["status"] == "budget_exhausted"
    assert exhausted["error_code"] == "agent.budget_exhausted"

    write_client = configured_client(tmp_path / "cancel", ScriptedAgentModel("write"))
    write_app = create_application(write_client)
    waiting = start_run(write_client, write_app["application_id"]).json()
    cancelled = write_client.post(f"/api/v1/agent-runs/{waiting['run_id']}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["approvals"][0]["status"] == "rejected"
    assert write_client.get(f"/api/v1/applications/{write_app['application_id']}").json()["version"] == 1


def test_credentials_are_rejected_before_agent_audit(tmp_path: Path) -> None:
    client = configured_client(tmp_path, ScriptedAgentModel())
    application = create_application(client)
    response = client.post(
        f"/api/v1/applications/{application['application_id']}/agent-runs",
        json={
            "request_text": "API Key = sk-this-must-not-be-stored",
            "idempotency_key": "secret-run",
            "data_leaving_confirmed": True,
        },
    )
    assert response.status_code == 422
    assert client.get(
        f"/api/v1/applications/{application['application_id']}/agent-runs"
    ).json() == []


def test_stale_approval_expires_without_overwriting_new_user_value(tmp_path: Path) -> None:
    client = configured_client(tmp_path, ScriptedAgentModel("write"))
    application = create_application(client)
    waiting = start_run(client, application["application_id"]).json()
    changed = client.patch(
        f"/api/v1/applications/{application['application_id']}",
        json={
            "changes": {"备注": "用户刚刚写入的备注"},
            "expected_version": 1,
            "idempotency_key": "user-change-after-preview",
        },
    )
    assert changed.status_code == 200
    approval_id = waiting["approvals"][0]["approval_id"]
    response = client.post(
        f"/api/v1/agent-runs/{waiting['run_id']}/approvals/{approval_id}",
        json={"decision": "approved", "decision_note": None},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "agent.approval_expired"
    saved = client.get(f"/api/v1/applications/{application['application_id']}").json()
    assert saved["values"]["备注"] == "用户刚刚写入的备注"
    assert saved["version"] == 2


def test_interruption_between_preview_and_pause_restores_pending_approval(
    tmp_path: Path,
) -> None:
    model = ScriptedAgentModel("write")
    client = configured_client(tmp_path, model)
    application = create_application(client)
    waiting = start_run(client, application["application_id"]).json()
    with sqlite3.connect(tmp_path / "careerpilot.db") as connection:
        connection.execute(
            "UPDATE background_jobs SET status = 'running' WHERE job_id = ?",
            (waiting["run_id"],),
        )
        connection.commit()

    restarted = configured_client(tmp_path, model)
    interrupted = restarted.get(f"/api/v1/agent-runs/{waiting['run_id']}").json()
    assert interrupted["status"] == "failed"
    assert interrupted["error_code"] == "job.interrupted"
    resumed = restarted.post(f"/api/v1/agent-runs/{waiting['run_id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "waiting_approval"
    assert resumed.json()["approvals"][0]["status"] == "pending"
