from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from careerpilot.core import (
    ApplicationService,
    Database,
    ExcelSyncService,
    JobService,
    SummaryRepository,
    upgrade_database,
)
from careerpilot.excel import COLUMNS
from careerpilot.mail import Imap163Adapter, MailAdapter, MailSyncError, MailSyncService
from careerpilot.markdown import MarkdownRenderer
from careerpilot.secrets import WindowsSecretStore
from careerpilot.security import safe_path
from careerpilot.settings import LocalSettings, SettingsStore
from careerpilot.summary import (
    BraveSearchClient,
    ModelClient,
    OpenAICompatibleModelClient,
    PageFetcher,
    PublicPageFetcher,
    SearchClient,
    SummaryJobError,
    SummaryService,
)


class ExcelSyncRequest(BaseModel):
    path: str = "data/tracker.xlsx"
    direction: Literal["import", "export"] = "import"
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


class ApplicationCreateRequest(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=200)
    values: dict[str, object] = Field(default_factory=dict)


class ApplicationPatchRequest(BaseModel):
    changes: dict[str, object]
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=200)


class SettingsUpdateRequest(LocalSettings):
    mail_secret: str | None = Field(default=None, min_length=1)
    model_secret: str | None = Field(default=None, min_length=1)
    brave_secret: str | None = Field(default=None, min_length=1)


class SummaryJobRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    data_leaving_confirmed: bool


def create_app(
    frontend_origin: str = "http://127.0.0.1:9999",
    data_dir: Path = Path("data"),
    secret_store: WindowsSecretStore | None = None,
    mail_adapter_factory: Callable[..., MailAdapter] = Imap163Adapter,
    search_client: SearchClient | None = None,
    page_fetcher: PageFetcher | None = None,
    model_client: ModelClient | None = None,
) -> FastAPI:
    app = FastAPI(title="CareerPilot", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["*"],
    )
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    upgrade_database(data_dir / "careerpilot.db")
    database = Database(data_dir / "careerpilot.db")
    applications = ApplicationService(database)
    excel = ExcelSyncService(database, applications)
    jobs = JobService(database)
    mail = MailSyncService(database)
    secret_store = secret_store or WindowsSecretStore()
    settings = SettingsStore(data_dir)
    search_client = search_client or BraveSearchClient()
    page_fetcher = page_fetcher or PublicPageFetcher()
    model_client = model_client or OpenAICompatibleModelClient()

    def application_view(item: object) -> dict[str, object]:
        return {
            "application_id": str(item.application_id),
            "company": item.company,
            "role": item.role,
            "values": item.values,
            "version": item.version,
        }

    def job_view(job: object) -> dict[str, object]:
        checkpoint = job.checkpoint
        if job.job_type == "summary" and checkpoint:
            checkpoint = {
                "application_id": checkpoint.get("application_id"),
                "search_result_count": len(checkpoint.get("search_results", [])),
                "source_count": len(checkpoint.get("sources", [])),
                "summary_version": checkpoint.get("summary_version"),
                "rendered_path": checkpoint.get("rendered_path"),
            }
        return {
            "job_id": str(job.job_id),
            "job_type": job.job_type,
            "status": job.status,
            "current_step": job.current_step,
            "checkpoint": checkpoint,
            "error_code": job.error_code,
            "error_message_safe": job.error_message_safe,
            "retryable": job.job_type in {"mail_sync", "summary"}
            and job.status == "failed",
        }

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/v1/applications")
    def list_applications() -> list[dict[str, object]]:
        return [application_view(item) for item in applications.list()]

    @app.post("/api/v1/applications", status_code=201)
    def create_application(request: ApplicationCreateRequest) -> dict[str, object]:
        company, role = request.company.strip(), request.role.strip()
        if not company or not role:
            raise HTTPException(status_code=422, detail="company and role are required")
        unknown = set(request.values) - set(COLUMNS)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"unknown tracker fields: {', '.join(sorted(unknown))}"
            )
        item = applications.create(
            company,
            role,
            idempotency_key=request.idempotency_key,
            values=request.values,
            user_fields=[
                "公司名称",
                "岗位",
                *[
                    field
                    for field, value in request.values.items()
                    if value not in (None, "")
                ],
            ],
        )
        return application_view(item)

    @app.get("/api/v1/applications/{application_id}")
    def get_application(application_id: UUID) -> dict[str, object]:
        try:
            item = applications.get(application_id)
            details = applications.details(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return {**application_view(item), **details}

    @app.patch("/api/v1/applications/{application_id}")
    def update_application(
        application_id: UUID, request: ApplicationPatchRequest
    ) -> dict[str, object]:
        try:
            item = applications.get(application_id)
            unknown = set(request.changes) - set(COLUMNS)
            if unknown:
                raise ValueError(
                    f"unknown tracker fields: {', '.join(sorted(unknown))}"
                )
            version = request.expected_version
            for field, value in request.changes.items():
                item = applications.apply_field_change(
                    application_id,
                    field,
                    value,
                    source="user",
                    idempotency_key=f"{request.idempotency_key}:{field}",
                    expected_version=version,
                )
                version = item.version
            return application_view(item)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            status = 409 if "version conflict" in str(exc) else 422
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.post("/api/v1/excel-sync-jobs")
    def excel_sync(request: ExcelSyncRequest) -> dict[str, object]:
        job = jobs.create("excel_sync", request.idempotency_key)
        try:
            path = safe_path(data_dir, Path(request.path))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if request.direction == "import":
            count = excel.import_workbook(path, request.idempotency_key)
            jobs.complete(job.job_id, {"rows": count})
        elif request.direction == "export":
            excel.export_workbook(path)
            jobs.complete(job.job_id, {"path": str(path)})
        return {"job_id": str(job.job_id)}

    @app.get("/api/v1/jobs")
    def list_jobs() -> list[dict[str, object]]:
        return [job_view(job) for job in jobs.list()]

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: UUID) -> dict[str, object]:
        try:
            return job_view(jobs.get(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    def named_secret(name: str) -> str | None:
        getter = getattr(secret_store, "get_named", None)
        return getter(name) if getter else None

    def summary_service() -> tuple[SummaryService, dict[str, object]]:
        current = settings.load()
        brave_credential = named_secret("brave")
        if not brave_credential:
            raise HTTPException(status_code=400, detail="Brave credential is not stored")
        if not current.model_base_url or not current.model_name:
            raise HTTPException(status_code=400, detail="model endpoint is not configured")
        markdown_directory = safe_path(data_dir, Path(current.markdown_path))
        return (
            SummaryService(
                database,
                search_client=search_client,
                page_fetcher=page_fetcher,
                model_client=model_client,
                renderer=MarkdownRenderer(database, markdown_directory),
            ),
            {
                "brave_credential": brave_credential,
                "model_base_url": current.model_base_url,
                "model_name": current.model_name,
                "model_credential": named_secret("model"),
            },
        )

    def summary_view(item: object) -> dict[str, object]:
        return {
            "summary_id": str(item.summary_id),
            "application_id": str(item.application_id),
            "version": item.version,
            "content": item.content,
            "created_at": item.created_at.isoformat(),
        }

    @app.get("/api/v1/settings")
    def get_settings() -> dict[str, object]:
        current = settings.load()
        return {
            **current.model_dump(),
            "mail_secret_saved": bool(
                current.email and secret_store.get(current.account_id, current.email)
            ),
            "model_secret_saved": bool(named_secret("model")),
            "brave_secret_saved": bool(named_secret("brave")),
        }

    @app.put("/api/v1/settings")
    def update_settings(request: SettingsUpdateRequest) -> dict[str, object]:
        setter = getattr(secret_store, "set_named", None)
        if (request.model_secret or request.brave_secret) and not setter:
            raise HTTPException(status_code=501, detail="named secret storage unavailable")
        values = request.model_dump(
            exclude={"mail_secret", "model_secret", "brave_secret"}
        )
        try:
            current = settings.save(values)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if request.mail_secret:
            secret_store.set(current.account_id, current.email, request.mail_secret)
        if request.model_secret or request.brave_secret:
            if request.model_secret:
                setter("model", request.model_secret)
            if request.brave_secret:
                setter("brave", request.brave_secret)
        return get_settings()

    @app.post("/api/v1/applications/{application_id}/summary-jobs")
    def generate_summary(
        application_id: UUID, request: SummaryJobRequest
    ) -> dict[str, object]:
        if not request.data_leaving_confirmed:
            raise HTTPException(status_code=422, detail="data leaving must be confirmed")
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        service, configuration = summary_service()
        try:
            job, summary = service.run(
                application_id,
                idempotency_key=request.idempotency_key,
                **configuration,
            )
        except SummaryJobError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "summary.failed", "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(job.job_id), "summary": summary_view(summary)}

    @app.get("/api/v1/applications/{application_id}/summaries")
    def list_summaries(application_id: UUID) -> list[dict[str, object]]:
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return [
            summary_view(item)
            for item in SummaryRepository(database).list(application_id)
        ]

    @app.get(
        "/api/v1/applications/{application_id}/markdown",
        response_class=PlainTextResponse,
    )
    def get_markdown(application_id: UUID) -> str:
        current = settings.load()
        path = safe_path(data_dir, Path(current.markdown_path)) / f"{application_id}.md"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Markdown is not generated")
        return path.read_text(encoding="utf-8")

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
        job = jobs.create("mail_sync", request.idempotency_key)
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
        return {"job_id": str(job.job_id), "processed": processed}

    @app.post("/api/v1/jobs/{job_id}/resume")
    def resume_job(job_id: UUID) -> dict[str, object]:
        try:
            failed = jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if failed.status != "failed" or failed.job_type not in {"mail_sync", "summary"}:
            raise HTTPException(status_code=409, detail="job is not resumable")
        if failed.job_type == "summary":
            checkpoint = failed.checkpoint or {}
            try:
                application_id = UUID(str(checkpoint["application_id"]))
                service, configuration = summary_service()
                resumed, summary = service.run(
                    application_id,
                    idempotency_key=f"resume:{job_id}",
                    checkpoint=checkpoint,
                    **configuration,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=409, detail="job resume checkpoint is invalid"
                ) from exc
            except SummaryJobError as exc:
                raise HTTPException(
                    status_code=502,
                    detail={"code": "summary.failed", "job_id": str(exc.job_id)},
                ) from exc
            return {
                "job_id": str(resumed.job_id),
                "summary": summary_view(summary),
            }
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
