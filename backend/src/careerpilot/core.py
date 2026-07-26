from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from careerpilot.excel import COLUMNS, TrackerRow, read_tracker, write_tracker


def utcnow() -> datetime:
    return datetime.now(UTC)


def _json_value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def _tracker_values(values: dict[str, Any]) -> dict[str, Any]:
    restored = dict(values)
    for field in ("投递时间", "截止时间"):
        if isinstance(restored.get(field), str):
            try:
                restored[field] = date.fromisoformat(restored[field])
            except ValueError:
                pass
    if isinstance(restored.get("最近更新时间"), str):
        try:
            restored["最近更新时间"] = datetime.fromisoformat(restored["最近更新时间"])
        except ValueError:
            pass
    return restored


class Base(DeclarativeBase):
    pass


class ApplicationRecord(Base):
    __tablename__ = "applications"
    application_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    create_key: Mapped[str] = mapped_column(String(200), unique=True)
    company: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    values: Mapped[dict[str, Any]] = mapped_column(JSON)
    user_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApplicationEventRecord(Base):
    __tablename__ = "application_events"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"))
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProvenanceRecord(Base):
    __tablename__ = "field_provenance"
    provenance_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"))
    field: Mapped[str] = mapped_column(String(100))
    value: Mapped[Any] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailRecord(Base):
    __tablename__ = "email_records"
    email_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.application_id"), nullable=True
    )
    account_id: Mapped[str] = mapped_column(String(100))
    message_id: Mapped[str | None] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    sender: Mapped[str] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_hash: Mapped[str] = mapped_column(String(64), unique=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncBatchRecord(Base):
    __tablename__ = "sync_batches"
    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_type: Mapped[str] = mapped_column(String(30))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    baseline: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BackgroundJobRecord(Base):
    __tablename__ = "background_jobs"
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30))
    current_step: Mapped[str | None] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message_safe: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobCheckpointRecord(Base):
    __tablename__ = "job_checkpoints"
    checkpoint_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("background_jobs.job_id"), unique=True)
    step: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.engine = create_engine(f"sqlite:///{path}", future=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Any:
        session = self.sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def upgrade_database(path: Path) -> None:
    from alembic import command
    from alembic.config import Config

    backend = Path(__file__).parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")


@dataclass
class Application:
    application_id: UUID
    company: str
    role: str
    values: dict[str, Any]
    version: int


@dataclass
class PersistentJob:
    job_id: UUID
    job_type: str
    status: str
    current_step: str | None
    checkpoint: dict[str, Any] | None


def _application(record: ApplicationRecord) -> Application:
    return Application(
        application_id=UUID(record.application_id),
        company=record.company,
        role=record.role,
        values=_tracker_values(record.values),
        version=record.version,
    )


class ApplicationService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        company: str,
        role: str,
        *,
        idempotency_key: str,
        application_id: UUID | None = None,
        values: dict[str, Any] | None = None,
    ) -> Application:
        with self.database.session() as session:
            existing = session.scalar(
                select(ApplicationRecord).where(ApplicationRecord.create_key == idempotency_key)
            )
            if existing:
                return _application(existing)
            application_id = application_id or uuid4()
            normalized = dict.fromkeys(COLUMNS)
            normalized.update(
                {field: _json_value(value) for field, value in (values or {}).items()}
            )
            normalized["公司名称"], normalized["岗位"] = company, role
            record = ApplicationRecord(
                application_id=str(application_id),
                create_key=idempotency_key,
                company=company,
                role=role,
                values=normalized,
                user_fields=[],
            )
            session.add(record)
            return _application(record)

    def get(self, application_id: UUID) -> Application:
        with self.database.session() as session:
            record = session.get(ApplicationRecord, str(application_id))
            if not record:
                raise KeyError(application_id)
            return _application(record)

    def list(self) -> list[Application]:
        with self.database.session() as session:
            return [_application(record) for record in session.scalars(select(ApplicationRecord))]

    def apply_field_change(
        self,
        application_id: UUID,
        field: str,
        value: Any,
        *,
        source: str,
        idempotency_key: str,
        evidence: str | None = None,
        expected_version: int | None = None,
    ) -> Application:
        if field not in COLUMNS:
            raise ValueError(f"unknown tracker field: {field}")
        with self.database.session() as session:
            duplicate = session.scalar(
                select(ProvenanceRecord).where(
                    ProvenanceRecord.idempotency_key == idempotency_key
                )
            )
            record = session.get(ApplicationRecord, str(application_id))
            if not record:
                raise KeyError(application_id)
            if expected_version is not None and record.version != expected_version:
                raise ValueError("application version conflict")
            if duplicate:
                return _application(record)
            session.add(
                ProvenanceRecord(
                    provenance_id=str(uuid4()),
                    application_id=str(application_id),
                    field=field,
                    value=_json_value(value),
                    source=source,
                    evidence=evidence,
                    idempotency_key=idempotency_key,
                )
            )
            session.add(
                ApplicationEventRecord(
                    event_id=str(uuid4()),
                    application_id=str(application_id),
                    event_type="field_change",
                    payload={"field": field, "value": _json_value(value), "source": source},
                    idempotency_key=f"event:{idempotency_key}",
                )
            )
            user_fields = set(record.user_fields)
            if source == "user":
                user_fields.add(field)
            if source == "user" or field not in user_fields:
                updated = dict(record.values)
                updated[field] = _json_value(value)
                record.values = updated
                record.user_fields = sorted(user_fields)
                record.version += 1
                record.updated_at = utcnow()
                if field == "公司名称":
                    record.company = str(value)
                elif field == "岗位":
                    record.role = str(value)
            session.flush()
            return _application(record)

    def provenance(self, application_id: UUID, field: str) -> list[dict[str, Any]]:
        with self.database.session() as session:
            records = session.scalars(
                select(ProvenanceRecord).where(
                    ProvenanceRecord.application_id == str(application_id),
                    ProvenanceRecord.field == field,
                )
            )
            return [
                {"value": record.value, "source": record.source, "evidence": record.evidence}
                for record in records
            ]


class ExcelSyncService:
    def __init__(self, database: Database, applications: ApplicationService) -> None:
        self.database, self.applications = database, applications

    def import_workbook(self, path: Path, idempotency_key: str) -> int:
        rows = read_tracker(path)
        with self.database.session() as session:
            existing = session.scalar(
                select(SyncBatchRecord).where(
                    SyncBatchRecord.idempotency_key == idempotency_key
                )
            )
            if existing:
                return 0
            session.add(
                SyncBatchRecord(
                    batch_id=str(uuid4()),
                    batch_type="excel_import",
                    idempotency_key=idempotency_key,
                    baseline={"rows": len(rows)},
                )
            )
        for row in rows:
            try:
                current = self.applications.get(row.application_id)
            except KeyError:
                self.applications.create(
                    str(row.values.get("公司名称") or ""),
                    str(row.values.get("岗位") or ""),
                    idempotency_key=f"excel:create:{row.application_id}",
                    application_id=row.application_id,
                    values=row.values,
                )
                continue
            for field, value in row.values.items():
                if value != current.values.get(field):
                    self.applications.apply_field_change(
                        row.application_id,
                        field,
                        value,
                        source="user",
                        idempotency_key=f"{idempotency_key}:{row.application_id}:{field}",
                    )
        return len(rows)

    def export_workbook(self, path: Path) -> Path:
        rows = [
            TrackerRow(
                application_id=application.application_id,
                row_version=application.version,
                values=application.values,
            )
            for application in self.applications.list()
        ]
        return write_tracker(path, rows)


class JobService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, job_type: str, idempotency_key: str) -> PersistentJob:
        with self.database.session() as session:
            existing = session.scalar(
                select(BackgroundJobRecord).where(
                    BackgroundJobRecord.idempotency_key == idempotency_key
                )
            )
            if existing:
                return self._view(session, existing)
            record = BackgroundJobRecord(
                job_id=str(uuid4()),
                job_type=job_type,
                status="pending",
                current_step=None,
                idempotency_key=idempotency_key,
                error_code=None,
                error_message_safe=None,
            )
            session.add(record)
            session.flush()
            return self._view(session, record)

    def progress(self, job_id: UUID, step: str, payload: dict[str, Any]) -> PersistentJob:
        with self.database.session() as session:
            record = session.get(BackgroundJobRecord, str(job_id))
            if not record:
                raise KeyError(job_id)
            record.status, record.current_step, record.updated_at = "running", step, utcnow()
            checkpoint = session.scalar(
                select(JobCheckpointRecord).where(JobCheckpointRecord.job_id == str(job_id))
            )
            if checkpoint:
                checkpoint.step, checkpoint.payload = step, payload
            else:
                session.add(
                    JobCheckpointRecord(
                        checkpoint_id=str(uuid4()),
                        job_id=str(job_id),
                        step=step,
                        payload=payload,
                    )
                )
            session.flush()
            return self._view(session, record)

    def get(self, job_id: UUID) -> PersistentJob:
        with self.database.session() as session:
            record = session.get(BackgroundJobRecord, str(job_id))
            if not record:
                raise KeyError(job_id)
            return self._view(session, record)

    def complete(self, job_id: UUID, payload: dict[str, Any]) -> PersistentJob:
        self.progress(job_id, "completed", payload)
        with self.database.session() as session:
            record = session.get(BackgroundJobRecord, str(job_id))
            if not record:
                raise KeyError(job_id)
            record.status, record.updated_at = "succeeded", utcnow()
            session.flush()
            return self._view(session, record)

    @staticmethod
    def _view(session: Session, record: BackgroundJobRecord) -> PersistentJob:
        checkpoint = session.scalar(
            select(JobCheckpointRecord).where(JobCheckpointRecord.job_id == record.job_id)
        )
        return PersistentJob(
            job_id=UUID(record.job_id),
            job_type=record.job_type,
            status=record.status,
            current_step=record.current_step,
            checkpoint=dict(checkpoint.payload) if checkpoint else None,
        )
