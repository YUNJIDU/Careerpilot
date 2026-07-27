from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from careerpilot.core import (
    ApplicationService,
    Database,
    ExcelSyncService,
    JobService,
    upgrade_database,
)
from careerpilot.mail import Imap163Adapter, MailAdapter, MailSyncError, MailSyncService
from careerpilot.secrets import WindowsSecretStore
from careerpilot.security import safe_path


class ExcelSyncRequest(BaseModel):
    path: str = "data/tracker.xlsx"
    direction: str = "import"
    idempotency_key: str


class MailAccountRequest(BaseModel):
    account_id: str
    email: str
    since: date = Field(
        default_factory=lambda: datetime.now(UTC).date() - timedelta(days=30)
    )
    limit: int = 100


class MailSyncRequest(MailAccountRequest):
    tracker_path: str = "data/tracker.xlsx"
    idempotency_key: str


def create_app(
    frontend_origin: str = "http://127.0.0.1:9999",
    data_dir: Path = Path("data"),
    secret_store: WindowsSecretStore | None = None,
    mail_adapter_factory: Callable[..., MailAdapter] = Imap163Adapter,
) -> FastAPI:
    app = FastAPI(title="CareerPilot", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    data_dir = data_dir.resolve()
    upgrade_database(data_dir / "careerpilot.db")
    database = Database(data_dir / "careerpilot.db")
    applications = ApplicationService(database)
    excel = ExcelSyncService(database, applications)
    jobs = JobService(database)
    mail = MailSyncService(database)
    secret_store = secret_store or WindowsSecretStore()

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/v1/applications")
    def list_applications() -> list[dict[str, object]]:
        return [
            {
                "application_id": str(item.application_id),
                "company": item.company,
                "role": item.role,
                "values": item.values,
                "version": item.version,
            }
            for item in applications.list()
        ]

    @app.post("/api/v1/excel-sync-jobs")
    def excel_sync(request: ExcelSyncRequest) -> dict[str, object]:
        job = jobs.create("excel_sync", request.idempotency_key)
        try:
            path = safe_path(data_dir, Path(request.path))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if request.direction == "import":
            count = excel.import_workbook(path, request.idempotency_key)
            jobs.progress(job.job_id, "completed", {"rows": count})
        elif request.direction == "export":
            excel.export_workbook(path)
            jobs.progress(job.job_id, "completed", {"path": str(path)})
        else:
            raise ValueError("direction must be import or export")
        return {"job_id": str(job.job_id)}

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: UUID) -> dict[str, object]:
        job = jobs.get(job_id)
        return {
            "job_id": str(job.job_id),
            "job_type": job.job_type,
            "status": job.status,
            "current_step": job.current_step,
            "checkpoint": job.checkpoint,
            "error_code": job.error_code,
            "error_message_safe": job.error_message_safe,
        }

    def adapter(request: MailAccountRequest) -> MailAdapter:
        authorization_code = secret_store.get(request.account_id, request.email)
        if not authorization_code:
            raise HTTPException(
                status_code=400,
                detail="163 credential is not stored for this account",
            )
        return mail_adapter_factory(
            request.email,
            authorization_code,
            since=request.since,
            limit=request.limit,
        )

    @app.post("/api/v1/mail-accounts/test")
    def test_mail_account(request: MailAccountRequest) -> dict[str, str]:
        mail_adapter = adapter(request)
        test_connection = getattr(mail_adapter, "test_connection", None)
        if not test_connection:
            raise HTTPException(status_code=400, detail="adapter cannot test connections")
        test_connection()
        return {"status": "ok"}

    @app.post("/api/v1/mail-sync-jobs")
    def mail_sync(request: MailSyncRequest) -> dict[str, object]:
        try:
            tracker_path = safe_path(data_dir, Path(request.tracker_path))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            processed = mail.sync(
                adapter(request),
                request.account_id,
                tracker_path,
                request.idempotency_key,
                resume_payload=request.model_dump(
                    mode="json", exclude={"idempotency_key"}
                ),
            )
        except MailSyncError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
            ) from exc
        return {"processed": processed}

    @app.post("/api/v1/jobs/{job_id}/resume")
    def resume_mail_job(job_id: UUID) -> dict[str, object]:
        try:
            failed = jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if failed.job_type != "mail_sync" or failed.status != "failed":
            raise HTTPException(status_code=409, detail="job is not resumable")
        try:
            request = MailSyncRequest(
                **(failed.checkpoint or {}),
                idempotency_key=f"resume:{job_id}",
            )
            tracker_path = safe_path(data_dir, Path(request.tracker_path))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=409, detail="job resume checkpoint is invalid"
            ) from exc
        resumed = jobs.create("mail_sync", request.idempotency_key)
        try:
            processed = mail.sync(
                adapter(request),
                request.account_id,
                tracker_path,
                request.idempotency_key,
                resume_payload=request.model_dump(
                    mode="json", exclude={"idempotency_key"}
                ),
            )
        except MailSyncError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(resumed.job_id), "processed": processed}

    return app


app = create_app()
