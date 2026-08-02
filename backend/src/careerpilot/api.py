import hashlib
import os
import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from careerpilot.adapters.contracts import MailAdapter
from careerpilot.agent import (
    AgentApprovalExpired,
    AgentLimits,
    AgentRunError,
    AgentService,
)
from careerpilot.core import (
    ApplicationService,
    Attachment,
    AttachmentService,
    Database,
    ExcelSyncService,
    JobService,
    MailAccount,
    MailAccountService,
    ResumeService,
    ResumeVersion,
    SummaryRepository,
    upgrade_database,
)
from careerpilot.excel import COLUMNS
from careerpilot.external_mail import GmailApiAdapter, OutlookGraphAdapter
from careerpilot.mail import (
    MAX_MESSAGE_BYTES,
    FixtureMailAdapter,
    Imap163Adapter,
    MailSyncError,
    MailSyncService,
    parse_message,
)
from careerpilot.markdown import MarkdownRenderer
from careerpilot.safe_files import (
    MAX_ATTACHMENT_BYTES,
    MAX_RESUME_BYTES,
    clean_filename,
    validate_file_content,
)
from careerpilot.secrets import SecretStore, default_secret_store
from careerpilot.security import safe_path
from careerpilot.settings import LocalSettings, SettingsStore
from careerpilot.stage5 import (
    Stage5JobError,
    Stage5Repository,
    Stage5Service,
    gap_analysis,
)
from careerpilot.stage7 import (
    OAuthConnectionService,
    OAuthCoordinator,
    PrefillService,
    ReminderService,
)
from careerpilot.summary import (
    ModelClient,
    OpenAICompatibleModelClient,
    PageFetcher,
    PublicPageFetcher,
    SearchClient,
    SearchResult,
    SummaryJobError,
    SummaryService,
    TavilySearchClient,
)

BUILTIN_MAIL_ADAPTERS: dict[str, Callable[..., MailAdapter]] = {
    "imap163": Imap163Adapter,
}
LOCAL_MAIL_ACCOUNT_ID = "local-eml"


class ExcelSyncRequest(BaseModel):
    path: str = "tracker.xlsx"
    direction: Literal["import", "export"] = "import"
    idempotency_key: str


class MailAccountRequest(BaseModel):
    account_id: str
    email: str
    since: date = Field(default_factory=lambda: datetime.now(UTC).date() - timedelta(days=30))
    limit: int = 100


class MailSyncRequest(MailAccountRequest):
    tracker_path: str = "tracker.xlsx"
    idempotency_key: str


class MailAccountUpsertRequest(BaseModel):
    adapter: Literal["imap163", "gmail", "outlook"] = "imap163"
    email: str = Field(min_length=3, max_length=320)
    authorization_code: str | None = Field(default=None, min_length=1, max_length=1000)
    enabled: bool = True


class MailAccountPatchRequest(BaseModel):
    enabled: bool


class MailSyncOptions(BaseModel):
    since: date = Field(default_factory=lambda: datetime.now(UTC).date() - timedelta(days=30))
    limit: int = Field(default=100, ge=1, le=500)
    tracker_path: str = "tracker.xlsx"
    idempotency_key: str = Field(min_length=1, max_length=200)


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
    tavily_secret: str | None = Field(default=None, min_length=1)
    gmail_client_id: str | None = Field(default=None, min_length=1, max_length=1000)
    gmail_client_secret: str | None = Field(default=None, min_length=1, max_length=2000)
    outlook_client_id: str | None = Field(default=None, min_length=1, max_length=1000)
    outlook_client_secret: str | None = Field(default=None, min_length=1, max_length=2000)


class SummaryJobRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    data_leaving_confirmed: bool


class JDCreateRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    raw_text: str | None = Field(default=None, max_length=50_000)
    source_url: str | None = Field(default=None, max_length=2_000)


class Stage5ModelJobRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    data_leaving_confirmed: bool


class EvidenceMapJobRequest(Stage5ModelJobRequest):
    jd_version_id: UUID
    resume_version_id: UUID


class ReviewCreateRequest(BaseModel):
    artifact_type: Literal["jd", "research", "evidence_map"]
    artifact_id: UUID
    item_id: str = Field(min_length=1, max_length=80)
    decision: Literal["confirmed", "needs_revision", "rejected"]
    note: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str = Field(min_length=1, max_length=200)


class AgentRunRequest(BaseModel):
    request_text: str = Field(min_length=1, max_length=4_000)
    idempotency_key: str = Field(min_length=1, max_length=200)
    data_leaving_confirmed: bool
    limits: AgentLimits = Field(default_factory=AgentLimits)


class AgentApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    decision_note: str | None = Field(default=None, max_length=2_000)


class OAuthStartRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)


class ReminderCreateRequest(BaseModel):
    application_id: UUID
    title: str = Field(min_length=1, max_length=300)
    due_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=200)


class PrefillCreateRequest(BaseModel):
    application_id: UUID
    target_url: str = Field(min_length=8, max_length=2_000)
    profile: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=200)


class PrefillHandoffRequest(BaseModel):
    diff: list[dict[str, str]] = Field(default_factory=list, max_length=100)
    captcha_required: bool = False


def create_app(
    frontend_origin: str | None = None,
    data_dir: Path | None = None,
    static_dir: Path | None = None,
    secret_store: SecretStore | None = None,
    mail_adapter_factory: Callable[..., MailAdapter] | None = None,
    search_client: SearchClient | None = None,
    page_fetcher: PageFetcher | None = None,
    model_client: ModelClient | None = None,
    external_mail_adapter_factory: Callable[[MailAccount, date, int], MailAdapter]
    | None = None,
    oauth_token_request: Callable[[str, dict[str, str]], dict[str, object]] | None = None,
    oauth_identity_request: Callable[[str, str], str] | None = None,
) -> FastAPI:
    mail_adapter_factory = mail_adapter_factory or BUILTIN_MAIL_ADAPTERS["imap163"]
    frontend_origin = frontend_origin or os.getenv(
        "CAREERPILOT_FRONTEND_ORIGIN", "http://127.0.0.1:9999"
    )
    data_dir = data_dir or Path(os.getenv("CAREERPILOT_DATA_DIR", "data"))
    static_dir = static_dir or (
        Path(value) if (value := os.getenv("CAREERPILOT_STATIC_DIR")) else None
    )
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
    mail_accounts = MailAccountService(database)
    attachments = AttachmentService(database)
    resumes = ResumeService(database)
    excel = ExcelSyncService(database, applications)
    jobs = JobService(database)
    jobs.recover_interrupted()
    mail = MailSyncService(database)
    secret_store = secret_store or default_secret_store()
    settings = SettingsStore(data_dir)
    legacy_settings = settings.load()
    if legacy_settings.email:
        try:
            mail_accounts.upsert(
                legacy_settings.account_id,
                legacy_settings.email,
                adapter="imap163",
            )
        except ValueError:
            pass
    search_client = search_client or TavilySearchClient()
    page_fetcher = page_fetcher or PublicPageFetcher()
    model_client = model_client or OpenAICompatibleModelClient()
    stage5_repository = Stage5Repository(database)
    stage5 = Stage5Service(
        database,
        data_dir=data_dir,
        search_client=search_client,
        page_fetcher=page_fetcher,
        model_client=model_client,
    )
    agent = AgentService(database, model_client=model_client)
    oauth_connections = OAuthConnectionService(database)
    oauth = OAuthCoordinator(
        oauth_connections,
        secret_store,
        **({"token_request": oauth_token_request} if oauth_token_request else {}),
        **({"identity_request": oauth_identity_request} if oauth_identity_request else {}),
    )
    reminders = ReminderService(database)
    prefill = PrefillService(database)
    public_api_origin = os.getenv("CAREERPILOT_PUBLIC_API_ORIGIN", "http://127.0.0.1:9998")

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
        elif job.job_type in {"jd_structure", "company_research", "evidence_map"}:
            checkpoint = checkpoint or None
        elif job.job_type == "agent" and checkpoint:
            checkpoint = {
                key: checkpoint.get(key)
                for key in (
                    "run_id",
                    "next_sequence",
                    "pending_tool_call_id",
                    "last_action",
                )
                if key in checkpoint
            }
        return {
            "job_id": str(job.job_id),
            "job_type": job.job_type,
            "status": job.status,
            "current_step": job.current_step,
            "checkpoint": checkpoint,
            "error_code": job.error_code,
            "error_message_safe": job.error_message_safe,
            "retryable": job.status == "failed"
            and (
                job.job_type in {"excel_sync", "mail_sync", "summary"}
                or (job.job_type == "agent" and job.error_code == "job.interrupted")
            ),
        }

    def run_excel_job(
        request: ExcelSyncRequest, *, idempotency_key: str | None = None
    ) -> tuple[object, dict[str, object]]:
        key = idempotency_key or request.idempotency_key
        job = jobs.create("excel_sync", key)
        if job.status == "succeeded":
            return job, job.checkpoint or {}
        configuration = {"path": request.path, "direction": request.direction}
        jobs.progress(job.job_id, "configured", configuration)
        try:
            path = safe_path(data_dir, Path(request.path))
            if request.direction == "import":
                count = excel.import_workbook(path, key)
                result: dict[str, object] = {"rows": count}
            else:
                excel.export_workbook(path)
                result = {"path": str(path)}
            return jobs.complete(job.job_id, result), result
        except Exception as exc:
            jobs.fail(
                job.job_id,
                "excel.sync_failed",
                "Excel synchronization failed without replacing the existing workbook.",
            )
            raise HTTPException(
                status_code=400,
                detail={"code": "excel.sync_failed", "job_id": str(job.job_id)},
            ) from exc

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
                *[field for field, value in request.values.items() if value not in (None, "")],
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
                raise ValueError(f"unknown tracker fields: {', '.join(sorted(unknown))}")
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
        job, _ = run_excel_job(request)
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
        search_credential = named_secret("tavily")
        if not search_credential:
            raise HTTPException(status_code=400, detail="Tavily credential is not stored")
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
                "search_credential": search_credential,
                "model_base_url": current.model_base_url,
                "model_name": current.model_name,
                "model_credential": named_secret("model"),
            },
        )

    def model_configuration() -> dict[str, object]:
        current = settings.load()
        if not current.model_base_url or not current.model_name:
            raise HTTPException(status_code=400, detail="model endpoint is not configured")
        return {
            "base_url": current.model_base_url,
            "model": current.model_name,
            "credential": named_secret("model"),
        }

    def require_data_leaving(confirmed: bool) -> None:
        if not confirmed:
            raise HTTPException(status_code=422, detail="data leaving must be confirmed")

    def summary_view(item: object) -> dict[str, object]:
        return {
            "summary_id": str(item.summary_id),
            "application_id": str(item.application_id),
            "version": item.version,
            "content": item.content,
            "created_at": item.created_at.isoformat(),
        }

    def mail_account_view(item: MailAccount) -> dict[str, object]:
        credential_saved = (
            bool(secret_store.get(item.account_id, item.email))
            if item.adapter == "imap163"
            else oauth.has_token(item.adapter, item.account_id)
        )
        return {
            "account_id": item.account_id,
            "adapter": item.adapter,
            "email": item.email,
            "enabled": item.enabled,
            "credential_saved": credential_saved,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    def mail_samples_directory() -> Path:
        directory = safe_path(data_dir, Path("mail-samples"))
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def mail_sample_path(sample_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", sample_id):
            raise ValueError("invalid local email sample id")
        return safe_path(mail_samples_directory(), Path(f"{sample_id}.eml"))

    def mail_sample_view(path: Path) -> dict[str, object]:
        item = parse_message(path.read_bytes())
        return {
            "sample_id": item.raw_hash,
            "subject": item.subject,
            "sender": item.sender,
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            "size": path.stat().st_size,
            "uploaded_at": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
        }

    def attachment_view(item: Attachment) -> dict[str, object]:
        return {
            "attachment_id": str(item.attachment_id),
            "application_id": str(item.application_id) if item.application_id else None,
            "filename": item.filename,
            "content_type": item.content_type,
            "size": item.size,
            "allowed": item.allowed,
            "status": item.status,
            "rejection_reason": item.rejection_reason,
            "download_url": (
                f"/api/v1/attachments/{item.attachment_id}/content"
                if item.status == "stored"
                else None
            ),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    def resume_view(item: ResumeVersion) -> dict[str, object]:
        return {
            "version_id": str(item.version_id),
            "resume_id": str(item.resume_id),
            "version": item.version,
            "label": item.label,
            "filename": item.filename,
            "content_type": item.content_type,
            "size": item.size,
            "content_hash": item.content_hash,
            "application_ids": [str(value) for value in item.application_ids],
            "download_url": f"/api/v1/resume-versions/{item.version_id}/content",
            "created_at": item.created_at.isoformat(),
        }

    def oauth_connection_view(item: object) -> dict[str, object]:
        return {
            "account_id": item.account_id,
            "provider": item.provider,
            "email": item.email,
            "status": item.status,
            "scopes": item.scopes,
            "token_saved": oauth.has_token(item.provider, item.account_id),
            "token_expires_at": (
                item.token_expires_at.isoformat() if item.token_expires_at else None
            ),
            "last_error": item.last_error,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    def reminder_view(item: object) -> dict[str, object]:
        return {
            "reminder_id": str(item.reminder_id),
            "application_id": str(item.application_id),
            "company": item.company,
            "role": item.role,
            "title": item.title,
            "due_at": item.due_at.isoformat(),
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    def notification_view(item: object) -> dict[str, object]:
        return {
            "notification_id": str(item.notification_id),
            "reminder_id": str(item.reminder_id),
            "application_id": str(item.application_id),
            "company": item.company,
            "role": item.role,
            "title": item.title,
            "due_at": item.due_at.isoformat(),
            "kind": item.kind,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "read_at": item.read_at.isoformat() if item.read_at else None,
        }

    def prefill_view(item: object) -> dict[str, object]:
        return {
            "session_id": str(item.session_id),
            "application_id": str(item.application_id),
            "company": item.company,
            "role": item.role,
            "target_origin": item.target_origin,
            "field_values": item.field_values,
            "diff": item.diff,
            "status": item.status,
            "captcha_required": item.captcha_required,
            "final_submit_allowed": False,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }

    def content_path(directory_name: str, content_hash: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", content_hash):
            raise ValueError("invalid content hash")
        directory = safe_path(data_dir, Path(directory_name))
        directory.mkdir(parents=True, exist_ok=True)
        return safe_path(directory, Path(content_hash))

    def store_content(directory_name: str, content: bytes) -> tuple[str, Path]:
        content_hash = hashlib.sha256(content).hexdigest()
        path = content_path(directory_name, content_hash)
        if path.is_file():
            return content_hash, path
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=".content-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            temporary_path.replace(path)
        except Exception:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            raise
        return content_hash, path

    def store_mail_sample(raw: bytes) -> tuple[Path, bool]:
        item = parse_message(raw)
        path = mail_sample_path(item.raw_hash)
        if path.is_file():
            return path, False
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=".mail-sample-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(raw)
                temporary_path = Path(temporary.name)
            temporary_path.replace(path)
        except Exception:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            raise
        return path, True

    @app.get("/api/v1/settings")
    def get_settings() -> dict[str, object]:
        current = settings.load()
        return {
            **current.model_dump(),
            "mail_secret_saved": bool(
                current.email and secret_store.get(current.account_id, current.email)
            ),
            "model_secret_saved": bool(named_secret("model")),
            "tavily_secret_saved": bool(named_secret("tavily")),
            "gmail_client_id_saved": bool(named_secret("oauth.gmail.client_id")),
            "gmail_client_secret_saved": bool(named_secret("oauth.gmail.client_secret")),
            "outlook_client_id_saved": bool(named_secret("oauth.outlook.client_id")),
            "outlook_client_secret_saved": bool(named_secret("oauth.outlook.client_secret")),
        }

    @app.put("/api/v1/settings")
    def update_settings(request: SettingsUpdateRequest) -> dict[str, object]:
        setter = getattr(secret_store, "set_named", None)
        oauth_values = {
            "oauth.gmail.client_id": request.gmail_client_id,
            "oauth.gmail.client_secret": request.gmail_client_secret,
            "oauth.outlook.client_id": request.outlook_client_id,
            "oauth.outlook.client_secret": request.outlook_client_secret,
        }
        supplied_secrets = (
            request.mail_secret
            or request.model_secret
            or request.tavily_secret
            or any(oauth_values.values())
        )
        if supplied_secrets and not getattr(secret_store, "writable", True):
            raise HTTPException(
                status_code=409,
                detail="Docker secrets are read-only; inject them at container startup",
            )
        if (request.model_secret or request.tavily_secret or any(oauth_values.values())) and not setter:
            raise HTTPException(status_code=501, detail="named secret storage unavailable")
        values = request.model_dump(
            exclude={
                "mail_secret",
                "model_secret",
                "tavily_secret",
                "gmail_client_id",
                "gmail_client_secret",
                "outlook_client_id",
                "outlook_client_secret",
            }
        )
        try:
            current = settings.save(values)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if request.mail_secret:
            secret_store.set(current.account_id, current.email, request.mail_secret)
        if request.model_secret or request.tavily_secret:
            if request.model_secret:
                setter("model", request.model_secret)
            if request.tavily_secret:
                setter("tavily", request.tavily_secret)
        for name, value in oauth_values.items():
            if value:
                setter(name, value)
        return get_settings()

    @app.post("/api/v1/applications/{application_id}/summary-jobs")
    def generate_summary(application_id: UUID, request: SummaryJobRequest) -> dict[str, object]:
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
        return [summary_view(item) for item in SummaryRepository(database).list(application_id)]

    @app.post("/api/v1/applications/{application_id}/jd-versions", status_code=201)
    def create_jd_version(
        application_id: UUID, request: JDCreateRequest
    ) -> dict[str, object]:
        if bool(request.raw_text) == bool(request.source_url):
            raise HTTPException(
                status_code=422,
                detail="provide exactly one of raw_text or source_url",
            )
        source_type, source_title = "manual", None
        source_url = request.source_url
        raw_text = request.raw_text
        if source_url:
            try:
                fetched = page_fetcher.fetch(SearchResult(url=source_url, title=source_url))
                source_type = "url"
                source_url = str(fetched["url"])
                source_title = str(fetched["title"])
                raw_text = str(fetched["text"])
            except Exception as exc:
                raise HTTPException(
                    status_code=422, detail="public JD page could not be fetched safely"
                ) from exc
        try:
            return stage5_repository.create_jd(
                application_id,
                raw_text=raw_text or "",
                create_key=request.idempotency_key,
                source_type=source_type,
                source_url=source_url,
                source_title=source_title,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/applications/{application_id}/jd-versions")
    def list_jd_versions(application_id: UUID) -> list[dict[str, object]]:
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return stage5_repository.list_jds(application_id)

    @app.post("/api/v1/jd-versions/{jd_version_id}/structure-jobs")
    def structure_jd_version(
        jd_version_id: UUID, request: Stage5ModelJobRequest
    ) -> dict[str, object]:
        require_data_leaving(request.data_leaving_confirmed)
        try:
            job, jd = stage5.structure_jd(
                jd_version_id,
                idempotency_key=request.idempotency_key,
                model_config=model_configuration(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="JD version not found") from exc
        except Stage5JobError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.category, "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(job.job_id), "jd": jd}

    @app.get("/api/v1/applications/{application_id}/company-research")
    def list_company_research(application_id: UUID) -> list[dict[str, object]]:
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return stage5_repository.list_research(application_id)

    @app.post("/api/v1/applications/{application_id}/company-research-jobs")
    def create_company_research(
        application_id: UUID, request: Stage5ModelJobRequest
    ) -> dict[str, object]:
        require_data_leaving(request.data_leaving_confirmed)
        search_credential = named_secret("tavily")
        if not search_credential:
            raise HTTPException(status_code=400, detail="Tavily credential is not stored")
        try:
            job, research = stage5.research_company(
                application_id,
                idempotency_key=request.idempotency_key,
                search_credential=search_credential,
                model_config=model_configuration(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except Stage5JobError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.category, "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(job.job_id), "research": research}

    @app.get("/api/v1/applications/{application_id}/evidence-maps")
    def list_evidence_maps(application_id: UUID) -> list[dict[str, object]]:
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return stage5_repository.list_maps(application_id)

    @app.post("/api/v1/applications/{application_id}/evidence-map-jobs")
    def create_evidence_map(
        application_id: UUID, request: EvidenceMapJobRequest
    ) -> dict[str, object]:
        require_data_leaving(request.data_leaving_confirmed)
        try:
            job, evidence_map = stage5.map_evidence(
                application_id,
                request.jd_version_id,
                request.resume_version_id,
                idempotency_key=request.idempotency_key,
                model_config=model_configuration(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Stage 5 resource not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Stage5JobError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.category, "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(job.job_id), "evidence_map": evidence_map}

    @app.get("/api/v1/evidence-maps/{map_id}/gaps")
    def get_gap_analysis(map_id: UUID) -> dict[str, object]:
        try:
            evidence_map = stage5_repository.get_map(map_id)
            jd = stage5_repository.get_jd(UUID(str(evidence_map["jd_version_id"])))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="evidence map not found") from exc
        return {
            "map_id": str(map_id),
            "gaps": gap_analysis(evidence_map["content"], jd["structure"]),
        }

    @app.get("/api/v1/applications/{application_id}/reviews")
    def list_reviews(application_id: UUID) -> list[dict[str, object]]:
        try:
            applications.get(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        return stage5_repository.list_reviews(application_id)

    @app.post("/api/v1/applications/{application_id}/reviews", status_code=201)
    def create_review(
        application_id: UUID, request: ReviewCreateRequest
    ) -> dict[str, object]:
        try:
            applications.get(application_id)
            return stage5_repository.append_review(
                application_id,
                artifact_type=request.artifact_type,
                artifact_id=request.artifact_id,
                item_id=request.item_id,
                decision=request.decision,
                note=request.note,
                idempotency_key=request.idempotency_key,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/applications/{application_id}/agent-runs", status_code=201)
    def create_agent_run(
        application_id: UUID, request: AgentRunRequest
    ) -> dict[str, object]:
        require_data_leaving(request.data_leaving_confirmed)
        try:
            return agent.start(
                application_id,
                request.request_text,
                idempotency_key=request.idempotency_key,
                limits=request.limits,
                model_config=model_configuration(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AgentRunError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.code, "run_id": str(exc.run_id)},
            ) from exc

    @app.get("/api/v1/applications/{application_id}/agent-runs")
    def list_agent_runs(application_id: UUID) -> list[dict[str, object]]:
        try:
            return agent.list(application_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc

    @app.get("/api/v1/agent-runs/{run_id}")
    def get_agent_run(run_id: UUID) -> dict[str, object]:
        try:
            return agent.view(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="agent run not found") from exc

    @app.post("/api/v1/agent-runs/{run_id}/approvals/{approval_id}")
    def decide_agent_approval(
        run_id: UUID,
        approval_id: UUID,
        request: AgentApprovalRequest,
    ) -> dict[str, object]:
        try:
            return agent.decide(
                run_id,
                approval_id,
                request.decision,
                request.decision_note,
                model_config=model_configuration(),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="agent approval not found") from exc
        except AgentApprovalExpired as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "agent.approval_expired", "run_id": str(run_id)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AgentRunError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.code, "run_id": str(exc.run_id)},
            ) from exc

    @app.post("/api/v1/agent-runs/{run_id}/resume")
    def resume_agent_run(run_id: UUID) -> dict[str, object]:
        try:
            return agent.resume(run_id, model_config=model_configuration())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="agent run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except AgentRunError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.code, "run_id": str(exc.run_id)},
            ) from exc

    @app.post("/api/v1/agent-runs/{run_id}/cancel")
    def cancel_agent_run(run_id: UUID) -> dict[str, object]:
        try:
            return agent.cancel(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="agent run not found") from exc

    def oauth_provider(value: str) -> Literal["gmail", "outlook"]:
        if value not in {"gmail", "outlook"}:
            raise HTTPException(status_code=404, detail="OAuth provider not found")
        return value

    @app.get("/api/v1/oauth-connections")
    def list_oauth_connections() -> list[dict[str, object]]:
        return [oauth_connection_view(item) for item in oauth_connections.list()]

    @app.post("/api/v1/oauth/{provider}/start")
    def start_oauth(provider: str, request: OAuthStartRequest) -> dict[str, object]:
        selected = oauth_provider(provider)
        account_id = validate_account_id(request.account_id)
        if not re.fullmatch(r"[^@\s\"]+@[^@\s\"]+\.[^@\s\"]+", request.email):
            raise HTTPException(status_code=422, detail="invalid email address")
        if not named_secret(f"oauth.{selected}.client_id"):
            raise HTTPException(
                status_code=409,
                detail=f"{selected} OAuth client ID is not configured",
            )
        try:
            mail_accounts.upsert(account_id, request.email, adapter=selected)
            authorization_url, connection = oauth.start(
                selected,
                account_id,
                f"{public_api_origin.rstrip('/')}/api/v1/oauth/{selected}/callback",
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "authorization_url": authorization_url,
            "connection": oauth_connection_view(connection),
        }

    @app.get("/api/v1/oauth/{provider}/callback")
    def oauth_callback(
        provider: str,
        state: str = "",
        code: str = "",
        error: str | None = None,
    ) -> RedirectResponse:
        selected = oauth_provider(provider)
        if error or not state or not code:
            raise HTTPException(status_code=400, detail="OAuth authorization was cancelled")
        try:
            oauth.complete(selected, state, code)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (ConnectionError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse(f"{frontend_origin}/#/integrations?oauth=connected", status_code=303)

    @app.post("/api/v1/oauth-connections/{account_id}/disconnect")
    def disconnect_oauth(account_id: str) -> dict[str, object]:
        try:
            account = registered_account(account_id)
            selected = oauth_provider(account.adapter)
            return oauth_connection_view(oauth.disconnect(selected, account.account_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="OAuth connection not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/reminders")
    def list_reminders(application_id: UUID | None = None) -> list[dict[str, object]]:
        return [reminder_view(item) for item in reminders.list(application_id)]

    @app.post("/api/v1/reminders", status_code=201)
    def create_reminder(request: ReminderCreateRequest) -> dict[str, object]:
        try:
            return reminder_view(
                reminders.create(
                    request.application_id,
                    request.title,
                    request.due_at,
                    request.idempotency_key,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/reminders/{reminder_id}/dismiss")
    def dismiss_reminder(reminder_id: UUID) -> dict[str, object]:
        try:
            return reminder_view(reminders.dismiss(reminder_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="reminder not found") from exc

    @app.get("/api/v1/reminders.ics")
    def export_reminders(application_id: UUID | None = None) -> Response:
        return Response(
            reminders.ics(application_id),
            media_type="text/calendar",
            headers={"Content-Disposition": 'attachment; filename="careerpilot-reminders.ics"'},
        )

    @app.get("/api/v1/notifications")
    def list_notifications() -> list[dict[str, object]]:
        return [notification_view(item) for item in reminders.notifications()]

    @app.post("/api/v1/notifications/scan")
    def scan_notifications() -> list[dict[str, object]]:
        return [notification_view(item) for item in reminders.scan()]

    @app.post("/api/v1/notifications/{notification_id}/read")
    def read_notification(notification_id: UUID) -> dict[str, object]:
        try:
            return notification_view(reminders.read(notification_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="notification not found") from exc

    @app.post("/api/v1/prefill-sessions", status_code=201)
    def create_prefill_session(request: PrefillCreateRequest) -> dict[str, object]:
        try:
            return prefill_view(
                prefill.create(
                    request.application_id,
                    request.target_url,
                    request.profile,
                    request.idempotency_key,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/prefill-sessions/{session_id}")
    def get_prefill_session(session_id: UUID) -> dict[str, object]:
        try:
            return prefill_view(prefill.get(session_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="prefill session not found") from exc

    @app.post("/api/v1/prefill-sessions/{session_id}/handoff")
    def handoff_prefill(
        session_id: UUID, request: PrefillHandoffRequest
    ) -> dict[str, object]:
        try:
            return prefill_view(
                prefill.handoff(
                    session_id,
                    request.diff,
                    captcha_required=request.captcha_required,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="prefill session not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

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

    def validate_account_id(account_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", account_id):
            raise HTTPException(status_code=422, detail="invalid mail account id")
        return account_id

    def registered_account(account_id: str) -> MailAccount:
        account_id = validate_account_id(account_id)
        try:
            account = mail_accounts.get(account_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="mail account not found") from exc
        if not account.enabled:
            raise HTTPException(status_code=409, detail="mail account is disabled")
        return account

    def account_adapter(account: MailAccount, since: date, limit: int) -> MailAdapter:
        if external_mail_adapter_factory and account.adapter in {"gmail", "outlook"}:
            return external_mail_adapter_factory(account, since, limit)
        if account.adapter == "gmail":
            return GmailApiAdapter(
                lambda: oauth.access_token("gmail", account.account_id),
                since=since,
                limit=limit,
            )
        if account.adapter == "outlook":
            return OutlookGraphAdapter(
                lambda: oauth.access_token("outlook", account.account_id),
                since=since,
                limit=limit,
            )
        authorization_code = secret_store.get(account.account_id, account.email)
        if not authorization_code:
            raise HTTPException(
                status_code=400,
                detail="163 credential is not stored for this account",
            )
        return mail_adapter_factory(
            account.email,
            authorization_code,
            since=since,
            limit=limit,
        )

    def verify_mail_adapter(
        mail_adapter: MailAdapter, authentication_detail: str = "163 authentication failed"
    ) -> None:
        try:
            mail_adapter.test_connection()
        except PermissionError as exc:
            raise HTTPException(
                status_code=401,
                detail=authentication_detail,
            ) from exc
        except (ConnectionError, OSError, TimeoutError) as exc:
            raise HTTPException(status_code=502, detail="mail provider is unavailable") from exc

    @app.get("/api/v1/mail-samples")
    def list_mail_samples() -> list[dict[str, object]]:
        samples: list[dict[str, object]] = []
        for path in mail_samples_directory().glob("*.eml"):
            try:
                samples.append(mail_sample_view(path))
            except (OSError, ValueError):
                continue
        return sorted(samples, key=lambda item: str(item["uploaded_at"]), reverse=True)

    @app.post("/api/v1/mail-samples/import-jobs")
    async def import_mail_sample(
        request: Request,
        filename: str,
        idempotency_key: str,
        tracker_path: str = "tracker.xlsx",
    ) -> dict[str, object]:
        if (
            not filename
            or len(filename) > 255
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
            or filename.lower() == ".eml"
            or not filename.lower().endswith(".eml")
        ):
            raise HTTPException(status_code=422, detail="invalid .eml filename")
        if not idempotency_key or len(idempotency_key) > 200:
            raise HTTPException(status_code=422, detail="invalid idempotency key")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "message/rfc822":
            raise HTTPException(
                status_code=415,
                detail="Content-Type must be message/rfc822",
            )
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_MESSAGE_BYTES:
                raise HTTPException(status_code=413, detail="email sample exceeds 2 MiB")
            raw.extend(chunk)
        if not raw:
            raise HTTPException(status_code=422, detail="email sample is empty")
        try:
            resolved_tracker_path = safe_path(data_dir, Path(tracker_path))
            stored_path, stored = store_mail_sample(bytes(raw))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        job = jobs.create("mail_sync", idempotency_key)
        if job.status == "succeeded":
            return {
                **mail_sample_view(stored_path),
                "stored": stored,
                "job_id": str(job.job_id),
                "processed": int((job.checkpoint or {}).get("processed", 0)),
            }
        checkpoint = {
            "source": "local_eml",
            "sample_id": stored_path.stem,
            "tracker_path": tracker_path,
        }
        try:
            processed = mail.sync(
                FixtureMailAdapter(stored_path.parent, sample_id=stored_path.stem),
                LOCAL_MAIL_ACCOUNT_ID,
                resolved_tracker_path,
                idempotency_key,
                resume_payload=checkpoint,
            )
        except MailSyncError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
            ) from exc
        return {
            **mail_sample_view(stored_path),
            "stored": stored,
            "job_id": str(job.job_id),
            "processed": processed,
        }

    @app.get("/api/v1/attachments")
    def list_attachments(
        application_id: UUID | None = None,
    ) -> list[dict[str, object]]:
        if application_id:
            try:
                applications.get(application_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="application not found") from exc
        return [attachment_view(item) for item in attachments.list(application_id)]

    @app.post("/api/v1/attachments/{attachment_id}/approve")
    def approve_attachment(attachment_id: UUID) -> dict[str, object]:
        try:
            item = attachments.get(attachment_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="attachment not found") from exc
        if item.status == "stored":
            return attachment_view(item)
        if not item.allowed:
            raise HTTPException(
                status_code=409,
                detail=item.rejection_reason or "attachment type is not allowed",
            )
        if item.account_id == LOCAL_MAIL_ACCOUNT_ID:
            mail_adapter: MailAdapter = FixtureMailAdapter(mail_samples_directory())
        else:
            account = registered_account(item.account_id)
            mail_adapter = account_adapter(
                account,
                datetime.now(UTC).date() - timedelta(days=3650),
                1,
            )
        try:
            content = mail_adapter.fetch_attachment(item.source_id)
            validate_file_content(
                content,
                item.filename,
                item.content_type,
                maximum=MAX_ATTACHMENT_BYTES,
            )
            content_hash, _ = store_content("attachments", content)
            item = attachments.set_result(
                attachment_id,
                status="stored",
                content_hash=content_hash,
            )
        except ValueError as exc:
            attachments.set_result(
                attachment_id,
                status="rejected",
                rejection_reason=str(exc)[:200],
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            attachments.set_result(
                attachment_id,
                status="failed",
                rejection_reason="attachment retrieval failed safely",
            )
            raise HTTPException(
                status_code=502,
                detail="attachment retrieval failed safely",
            ) from exc
        return attachment_view(item)

    @app.get("/api/v1/attachments/{attachment_id}/content")
    def download_attachment(attachment_id: UUID) -> FileResponse:
        try:
            item = attachments.get(attachment_id)
            if item.status != "stored" or not item.content_hash:
                raise KeyError(attachment_id)
            path = content_path("attachments", item.content_hash)
            if not path.is_file():
                raise KeyError(attachment_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="attachment content not found") from exc
        return FileResponse(path, media_type=item.content_type, filename=item.filename)

    @app.get("/api/v1/resumes")
    def list_resumes() -> list[dict[str, object]]:
        return [resume_view(item) for item in resumes.list()]

    @app.post("/api/v1/resumes", status_code=201)
    async def upload_resume(
        request: Request,
        filename: str,
        label: str,
        resume_id: UUID | None = None,
        application_id: UUID | None = None,
    ) -> dict[str, object]:
        label = label.strip()
        if not label or len(label) > 200:
            raise HTTPException(status_code=422, detail="invalid resume label")
        try:
            filename = clean_filename(filename)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_RESUME_BYTES:
                raise HTTPException(status_code=413, detail="resume exceeds 5 MiB")
            content.extend(chunk)
        try:
            validate_file_content(
                bytes(content),
                filename,
                content_type,
                resume_only=True,
                maximum=MAX_RESUME_BYTES,
            )
            content_hash, _ = store_content("resumes", bytes(content))
            version = resumes.create_version(
                label=label,
                filename=filename,
                content_type=content_type,
                size=len(content),
                content_hash=content_hash,
                resume_id=resume_id,
                application_id=application_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="resume or application not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return resume_view(version)

    @app.put("/api/v1/resume-versions/{version_id}/applications/{application_id}")
    def link_resume(version_id: UUID, application_id: UUID) -> dict[str, object]:
        try:
            return resume_view(resumes.link(version_id, application_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="resume or application not found") from exc

    @app.get("/api/v1/resume-versions/{version_id}/content")
    def download_resume(version_id: UUID) -> FileResponse:
        try:
            item = resumes.get(version_id)
            path = content_path("resumes", item.content_hash)
            if not path.is_file():
                raise KeyError(version_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="resume content not found") from exc
        return FileResponse(path, media_type=item.content_type, filename=item.filename)

    @app.get("/api/v1/mail-accounts")
    def list_mail_accounts() -> list[dict[str, object]]:
        return [mail_account_view(item) for item in mail_accounts.list()]

    @app.put("/api/v1/mail-accounts/{account_id}")
    def upsert_mail_account(
        account_id: str, request: MailAccountUpsertRequest
    ) -> dict[str, object]:
        account_id = validate_account_id(account_id)
        if not re.fullmatch(r"[^@\s\"]+@[^@\s\"]+\.[^@\s\"]+", request.email):
            raise HTTPException(status_code=422, detail="invalid email address")
        if request.authorization_code and request.adapter != "imap163":
            raise HTTPException(
                status_code=422,
                detail="Gmail and Outlook must use OAuth; passwords are not accepted",
            )
        if request.authorization_code and not getattr(secret_store, "writable", True):
            raise HTTPException(
                status_code=409,
                detail="Docker secrets are read-only; inject them at container startup",
            )
        try:
            account = mail_accounts.upsert(
                account_id,
                request.email,
                adapter=request.adapter,
                enabled=request.enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if request.authorization_code:
            secret_store.set(account.account_id, account.email, request.authorization_code)
        return mail_account_view(account)

    @app.patch("/api/v1/mail-accounts/{account_id}")
    def patch_mail_account(account_id: str, request: MailAccountPatchRequest) -> dict[str, object]:
        account_id = validate_account_id(account_id)
        try:
            account = mail_accounts.set_enabled(account_id, request.enabled)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="mail account not found") from exc
        return mail_account_view(account)

    @app.post("/api/v1/mail-accounts/test")
    def test_mail_account(request: MailAccountRequest) -> dict[str, str]:
        mail_adapter = adapter(request)
        test_connection = getattr(mail_adapter, "test_connection", None)
        if not test_connection:
            raise HTTPException(status_code=400, detail="adapter cannot test connections")
        verify_mail_adapter(mail_adapter)
        return {"status": "ok"}

    @app.post("/api/v1/mail-accounts/{account_id}/test")
    def test_registered_mail_account(account_id: str) -> dict[str, str]:
        account = registered_account(account_id)
        mail_adapter = account_adapter(
            account,
            datetime.now(UTC).date() - timedelta(days=30),
            1,
        )
        verify_mail_adapter(
            mail_adapter,
            "163 authentication failed"
            if account.adapter == "imap163"
            else "mail authentication failed",
        )
        return {"status": "ok"}

    @app.post("/api/v1/mail-accounts/{account_id}/sync-jobs")
    def sync_registered_mail_account(
        account_id: str, request: MailSyncOptions
    ) -> dict[str, object]:
        account = registered_account(account_id)
        job = jobs.create("mail_sync", request.idempotency_key)
        try:
            tracker_path = safe_path(data_dir, Path(request.tracker_path))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            processed = mail.sync(
                account_adapter(account, request.since, request.limit),
                account.account_id,
                tracker_path,
                request.idempotency_key,
                resume_payload={
                    "account_id": account.account_id,
                    **request.model_dump(mode="json", exclude={"idempotency_key"}),
                },
            )
        except MailSyncError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
            ) from exc
        return {"job_id": str(job.job_id), "processed": processed}

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
                resume_payload=request.model_dump(mode="json", exclude={"idempotency_key"}),
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
        if failed.status != "failed" or failed.job_type not in {
            "excel_sync",
            "mail_sync",
            "summary",
        }:
            raise HTTPException(status_code=409, detail="job is not resumable")
        if failed.job_type == "excel_sync":
            try:
                request = ExcelSyncRequest(
                    **(failed.checkpoint or {}),
                    idempotency_key=f"resume:{job_id}",
                )
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=409, detail="job resume checkpoint is invalid"
                ) from exc
            resumed, result = run_excel_job(request)
            jobs.complete(
                failed.job_id,
                {"resumed_job_id": str(resumed.job_id)},
                step="resumed",
            )
            return {"job_id": str(resumed.job_id), **result}
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
            jobs.complete(
                failed.job_id,
                {"resumed_job_id": str(resumed.job_id)},
                step="resumed",
            )
            return {
                "job_id": str(resumed.job_id),
                "summary": summary_view(summary),
            }
        checkpoint = dict(failed.checkpoint or {})
        if checkpoint.get("source") == "local_eml":
            try:
                sample_id = str(checkpoint["sample_id"])
                sample_path = mail_sample_path(sample_id)
                if not sample_path.is_file():
                    raise ValueError("local email sample is missing")
                tracker_value = str(checkpoint["tracker_path"])
                tracker_path = safe_path(data_dir, Path(tracker_value))
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=409, detail="job resume checkpoint is invalid"
                ) from exc
            idempotency_key = f"resume:{job_id}"
            resumed = jobs.create("mail_sync", idempotency_key)
            try:
                processed = mail.sync(
                    FixtureMailAdapter(sample_path.parent, sample_id=sample_id),
                    LOCAL_MAIL_ACCOUNT_ID,
                    tracker_path,
                    idempotency_key,
                    resume_payload={
                        "source": "local_eml",
                        "sample_id": sample_id,
                        "tracker_path": tracker_value,
                    },
                )
            except MailSyncError as exc:
                raise HTTPException(
                    status_code=502,
                    detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
                ) from exc
            jobs.complete(
                failed.job_id,
                {"resumed_job_id": str(resumed.job_id)},
                step="resumed",
            )
            return {"job_id": str(resumed.job_id), "processed": processed}
        try:
            account_id = str(checkpoint["account_id"])
            try:
                account = mail_accounts.get(account_id)
            except KeyError:
                account = None
            request = MailSyncRequest(
                **({**checkpoint, "email": account.email} if account else checkpoint),
                idempotency_key=f"resume:{job_id}",
            )
            tracker_path = safe_path(data_dir, Path(request.tracker_path))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail="job resume checkpoint is invalid") from exc
        resumed = jobs.create("mail_sync", request.idempotency_key)
        try:
            processed = mail.sync(
                account_adapter(account, request.since, request.limit)
                if account
                else adapter(request),
                request.account_id,
                tracker_path,
                request.idempotency_key,
                resume_payload=request.model_dump(mode="json", exclude={"idempotency_key"}),
            )
        except MailSyncError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "mail.sync_failed", "job_id": str(exc.job_id)},
            ) from exc
        jobs.complete(
            failed.job_id,
            {"resumed_job_id": str(resumed.job_id)},
            step="resumed",
        )
        return {"job_id": str(resumed.job_id), "processed": processed}

    if static_dir:
        resolved_static_dir = static_dir.resolve()
        if not (resolved_static_dir / "index.html").is_file():
            raise RuntimeError("CAREERPILOT_STATIC_DIR must contain index.html")
        app.mount("/", StaticFiles(directory=resolved_static_dir, html=True), name="frontend")

    return app
