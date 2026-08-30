from __future__ import annotations

import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    desc,
    or_,
    select,
    update,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from careerpilot.excel import COLUMNS, RESUME_COLUMN, TrackerRow, read_tracker, write_tracker

PROCESS_FIELDS = (
    "简历通过",
    "测评",
    "笔试",
    "一面",
    "二面",
    "三面",
    "HR 面",
    "终面",
)
_TERMINAL_PATTERN = re.compile(r"未通过|不通过|未能通过|淘汰|拒绝|挂|终止|结束|不合适|遗憾")


def terminal_result(field: str, value: Any) -> tuple[str, str] | None:
    text = str(value or "").strip()
    if not text or not _TERMINAL_PATTERN.search(text):
        return None
    step = (
        field
        if field in PROCESS_FIELDS
        else next(
            (candidate for candidate in reversed(PROCESS_FIELDS) if candidate in text),
            "流程",
        )
    )
    reason = "主动结束" if re.search(r"主动|撤回|放弃", text) else "未通过"
    return step, reason


def terminal_label(step: str, reason: str) -> str:
    detail = reason if reason == "主动结束" else f"{step}{reason}"
    return f"已结束（{detail}）"


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


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(
        str.maketrans({"（": "(", "）": ")", "【": "[", "】": "]"})
    )
    return re.sub(r"\s+", "", normalized).casefold()


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


class ResumeVersionRecord(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version"),
        UniqueConstraint("resume_id", "content_hash"),
    )
    version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resume_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApplicationResumeRecord(Base):
    __tablename__ = "application_resumes"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.application_id"), primary_key=True
    )
    version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.version_id"))


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


class SummaryVersionRecord(Base):
    __tablename__ = "summary_versions"
    __table_args__ = (UniqueConstraint("application_id", "version"),)
    summary_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
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
    error_code: str | None
    error_message_safe: str | None


@dataclass
class StoredEmail:
    raw_hash: str
    application_id: UUID
    sent_at: datetime
    facts: dict[str, Any]


@dataclass
class SummaryVersion:
    summary_id: UUID
    application_id: UUID
    version: int
    content: dict[str, Any]
    created_at: datetime


@dataclass
class ResumeVersion:
    version_id: UUID
    resume_id: UUID
    version: int
    label: str
    filename: str
    content_type: str
    size: int
    content_hash: str
    application_ids: tuple[UUID, ...]
    created_at: datetime


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
        user_fields: list[str] | None = None,
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
            for field in PROCESS_FIELDS:
                terminal = terminal_result(field, normalized.get(field))
                if terminal:
                    normalized[field] = terminal[1]
                    normalized["当前阶段"] = terminal_label(*terminal)
            record = ApplicationRecord(
                application_id=str(application_id),
                create_key=idempotency_key,
                company=company,
                role=role,
                values=normalized,
                user_fields=user_fields or [],
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
                select(ProvenanceRecord).where(ProvenanceRecord.idempotency_key == idempotency_key)
            )
            record = session.get(ApplicationRecord, str(application_id))
            if not record:
                raise KeyError(application_id)
            if expected_version is not None and record.version != expected_version:
                raise ValueError("application version conflict")
            if duplicate:
                return _application(record)
            terminal = terminal_result(field, value)
            if field in PROCESS_FIELDS and terminal:
                value = terminal[1]
            elif field == "当前阶段" and terminal:
                value = terminal_label(*terminal)
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
                if value in (None, ""):
                    user_fields.discard(field)
                else:
                    user_fields.add(field)
            if source in {"user", "mail_authoritative"} or field not in user_fields:
                updated = dict(record.values)
                updated[field] = _json_value(value)
                if (
                    terminal
                    and field in PROCESS_FIELDS
                    and (source in {"user", "mail_authoritative"} or "当前阶段" not in user_fields)
                ):
                    stage = terminal_label(*terminal)
                    updated["当前阶段"] = stage
                    session.add(
                        ProvenanceRecord(
                            provenance_id=str(uuid4()),
                            application_id=str(application_id),
                            field="当前阶段",
                            value=stage,
                            source=source,
                            evidence=evidence,
                            idempotency_key=f"{idempotency_key}:terminal",
                        )
                    )
                    session.add(
                        ApplicationEventRecord(
                            event_id=str(uuid4()),
                            application_id=str(application_id),
                            event_type="field_change",
                            payload={
                                "field": "当前阶段",
                                "value": stage,
                                "source": source,
                            },
                            idempotency_key=f"event:{idempotency_key}:terminal",
                        )
                    )
                    if source == "user":
                        user_fields.add("当前阶段")
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

    def details(self, application_id: UUID) -> dict[str, list[dict[str, Any]]]:
        with self.database.session() as session:
            if not session.get(ApplicationRecord, str(application_id)):
                raise KeyError(application_id)
            events = session.scalars(
                select(ApplicationEventRecord)
                .where(ApplicationEventRecord.application_id == str(application_id))
                .order_by(desc(ApplicationEventRecord.created_at))
            )
            provenance = session.scalars(
                select(ProvenanceRecord)
                .where(ProvenanceRecord.application_id == str(application_id))
                .order_by(desc(ProvenanceRecord.created_at))
            )
            emails = session.scalars(
                select(EmailRecord)
                .where(EmailRecord.application_id == str(application_id))
                .order_by(desc(EmailRecord.sent_at))
            )
            return {
                "timeline": [
                    {
                        "event_type": item.event_type,
                        "payload": item.payload,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in events
                ],
                "provenance": [
                    {
                        "field": item.field,
                        "value": item.value,
                        "source": item.source,
                        "evidence": item.evidence,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in provenance
                ],
                "emails": [
                    {
                        "subject": item.subject,
                        "sender": item.sender,
                        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
                        "evidence": item.evidence,
                    }
                    for item in emails
                ],
            }

    def latest_user_change(self, application_id: UUID, field: str) -> datetime | None:
        with self.database.session() as session:
            record = session.scalar(
                select(ProvenanceRecord)
                .where(
                    ProvenanceRecord.application_id == str(application_id),
                    ProvenanceRecord.field == field,
                    ProvenanceRecord.source == "user",
                )
                .order_by(desc(ProvenanceRecord.created_at))
            )
            return record.created_at if record else None


class ExcelSyncService:
    def __init__(self, database: Database, applications: ApplicationService) -> None:
        self.database, self.applications = database, applications

    def import_workbook(self, path: Path, idempotency_key: str) -> dict[str, int]:
        rows = read_tracker(path)
        with self.database.session() as session:
            existing = session.scalar(
                select(SyncBatchRecord).where(SyncBatchRecord.idempotency_key == idempotency_key)
            )
            if existing:
                return {"created": 0, "updated": 0, "deleted": 0, "resume_mapped": 0}

        current = self.applications.list()
        by_id = {item.application_id: item for item in current}
        by_identity = {
            (normalize_identity(item.company), normalize_identity(item.role)): item
            for item in current
        }
        prepared: list[tuple[TrackerRow, UUID]] = []
        for row in rows:
            company = str(row.values.get("公司名称") or "").strip()
            role = str(row.values.get("岗位") or "").strip()
            if not company or not role:
                raise ValueError("company and role are required for every Excel row")
            target_id = row.application_id
            if target_id not in by_id:
                match = by_identity.get((normalize_identity(company), normalize_identity(role)))
                if match:
                    target_id = match.application_id
            prepared.append((row, target_id))

        resume_links: dict[UUID, str | None] = {}
        if rows and rows[0].resume_column_present:
            with self.database.session() as session:
                versions = list(session.scalars(select(ResumeVersionRecord)))
            latest: dict[str, ResumeVersionRecord] = {}
            for version in versions:
                if (
                    version.resume_id not in latest
                    or version.version > latest[version.resume_id].version
                ):
                    latest[version.resume_id] = version
            labels: dict[str, list[str]] = {}
            for resume_id, version in latest.items():
                labels.setdefault(version.label.casefold(), []).append(resume_id)
            for row, target_id in prepared:
                reference = str(row.values.get(RESUME_COLUMN) or "").strip()
                if not reference:
                    resume_links[target_id] = None
                    continue
                match = re.fullmatch(r"(.+?)(?:@v(\d+))?", reference)
                if not match:
                    raise ValueError(f"invalid current resume: {reference}")
                label, requested_version = match.group(1).strip(), match.group(2)
                resume_ids = labels.get(label.casefold(), [])
                if len(resume_ids) != 1:
                    raise ValueError(f"current resume is missing or ambiguous: {reference}")
                candidates = [item for item in versions if item.resume_id == resume_ids[0]]
                selected = (
                    next(
                        (item for item in candidates if item.version == int(requested_version)),
                        None,
                    )
                    if requested_version
                    else max(candidates, key=lambda item: item.version)
                )
                if not selected:
                    raise ValueError(f"resume version does not exist: {reference}")
                resume_links[target_id] = selected.version_id

        backup = self.database.path.with_name("careerpilot.db.pre-excel-import.bak")
        with sqlite3.connect(self.database.path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)

        input_ids = {target_id for _, target_id in prepared}
        stats = {"created": 0, "updated": 0, "deleted": 0, "resume_mapped": 0}
        with self.database.session() as session:
            session.add(
                SyncBatchRecord(
                    batch_id=str(uuid4()),
                    batch_type="excel_import",
                    idempotency_key=idempotency_key,
                    baseline={"rows": len(rows)},
                )
            )
            records = {
                UUID(item.application_id): item
                for item in session.scalars(select(ApplicationRecord))
            }
            for row, target_id in prepared:
                values = {field: _json_value(row.values.get(field)) for field in COLUMNS}
                for field in PROCESS_FIELDS:
                    terminal = terminal_result(field, values.get(field))
                    if terminal:
                        values[field] = terminal[1]
                        values["当前阶段"] = terminal_label(*terminal)
                company, role = str(values["公司名称"]), str(values["岗位"])
                record = records.get(target_id)
                if record is None:
                    record = ApplicationRecord(
                        application_id=str(target_id),
                        create_key=f"excel:create:{target_id}",
                        company=company,
                        role=role,
                        values=values,
                        user_fields=[
                            field for field, value in values.items() if value not in (None, "")
                        ],
                    )
                    session.add(record)
                    records[target_id] = record
                    stats["created"] += 1
                else:
                    changed = [
                        field for field in COLUMNS if record.values.get(field) != values[field]
                    ]
                    for field in changed:
                        session.add(
                            ProvenanceRecord(
                                provenance_id=str(uuid4()),
                                application_id=str(target_id),
                                field=field,
                                value=values[field],
                                source="user",
                                evidence=None,
                                idempotency_key=f"{idempotency_key}:{target_id}:{field}",
                            )
                        )
                    if changed:
                        record.company, record.role, record.values = company, role, values
                        record.user_fields = [
                            field for field, value in values.items() if value not in (None, "")
                        ]
                        record.version += 1
                        record.updated_at = utcnow()
                        stats["updated"] += 1
                if target_id in resume_links:
                    session.execute(
                        delete(ApplicationResumeRecord).where(
                            ApplicationResumeRecord.application_id == str(target_id)
                        )
                    )
                    if resume_links[target_id]:
                        session.add(
                            ApplicationResumeRecord(
                                application_id=str(target_id),
                                version_id=str(resume_links[target_id]),
                            )
                        )
                    stats["resume_mapped"] += 1

            deleted_ids = [item for item in records if item not in input_ids]
            if deleted_ids:
                ids = [str(item) for item in deleted_ids]
                session.execute(
                    update(EmailRecord)
                    .where(EmailRecord.application_id.in_(ids))
                    .values(application_id=None)
                )
                for model in (
                    ApplicationResumeRecord,
                    SummaryVersionRecord,
                    ProvenanceRecord,
                    ApplicationEventRecord,
                ):
                    session.execute(delete(model).where(model.application_id.in_(ids)))
                session.execute(
                    delete(ApplicationRecord).where(ApplicationRecord.application_id.in_(ids))
                )
                stats["deleted"] = len(ids)
        return stats

    def export_workbook(self, path: Path) -> Path:
        with self.database.session() as session:
            links = {
                link.application_id: session.get(ResumeVersionRecord, link.version_id)
                for link in session.scalars(select(ApplicationResumeRecord))
            }
        rows = [
            TrackerRow(
                application_id=application.application_id,
                row_version=application.version,
                values={
                    **application.values,
                    RESUME_COLUMN: (
                        f"{links[str(application.application_id)].label}@v{links[str(application.application_id)].version}"
                        if str(application.application_id) in links
                        else None
                    ),
                },
            )
            for application in self.applications.list()
        ]
        return write_tracker(path, rows)


class EmailService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def exists(self, account_id: str, raw_hash: str, message_id: str | None) -> bool:
        return self.find(account_id, raw_hash, message_id)[0]

    def find(
        self, account_id: str, raw_hash: str, message_id: str | None
    ) -> tuple[bool, UUID | None]:
        with self.database.session() as session:
            conditions = [EmailRecord.raw_hash == raw_hash]
            if message_id:
                conditions.append(
                    (EmailRecord.account_id == account_id) & (EmailRecord.message_id == message_id)
                )
            record = session.scalar(select(EmailRecord).where(or_(*conditions)))
            application_id = (
                UUID(record.application_id) if record and record.application_id else None
            )
            return record is not None, application_id

    def link(
        self,
        raw_hash: str,
        application_id: UUID,
        facts: dict[str, Any],
        mail_kind: str | None = None,
    ) -> None:
        with self.database.session() as session:
            record = session.scalar(select(EmailRecord).where(EmailRecord.raw_hash == raw_hash))
            if not record:
                raise KeyError(raw_hash)
            record.application_id = str(application_id)
            record.evidence = {
                "facts": {key: str(value) for key, value in facts.items()},
                "mail_kind": mail_kind,
            }

    def linked(self) -> list[StoredEmail]:
        with self.database.session() as session:
            records = session.scalars(
                select(EmailRecord).where(
                    EmailRecord.application_id.is_not(None),
                    EmailRecord.sent_at.is_not(None),
                )
            )
            return [
                StoredEmail(
                    raw_hash=record.raw_hash,
                    application_id=UUID(str(record.application_id)),
                    sent_at=record.sent_at,
                    facts=dict(record.evidence.get("facts", {})),
                )
                for record in records
            ]

    def record(
        self,
        *,
        account_id: str,
        raw_hash: str,
        message_id: str | None,
        subject: str,
        sender: str,
        sent_at: datetime | None,
        application_id: UUID | None,
        facts: dict[str, Any],
        mail_kind: str | None = None,
    ) -> None:
        with self.database.session() as session:
            session.add(
                EmailRecord(
                    email_id=raw_hash,
                    application_id=str(application_id) if application_id else None,
                    account_id=account_id,
                    message_id=message_id,
                    subject=subject,
                    sender=sender,
                    sent_at=sent_at,
                    raw_hash=raw_hash,
                    evidence={
                        "facts": {key: str(value) for key, value in facts.items()},
                        "mail_kind": mail_kind,
                    },
                )
            )


class ResumeService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _view(session: Session, record: ResumeVersionRecord) -> ResumeVersion:
        links = session.scalars(
            select(ApplicationResumeRecord).where(
                ApplicationResumeRecord.version_id == record.version_id
            )
        )
        return ResumeVersion(
            version_id=UUID(record.version_id),
            resume_id=UUID(record.resume_id),
            version=record.version,
            label=record.label,
            filename=record.filename,
            content_type=record.content_type,
            size=record.size,
            content_hash=record.content_hash,
            application_ids=tuple(UUID(link.application_id) for link in links),
            created_at=record.created_at,
        )

    def create_version(
        self,
        *,
        label: str,
        filename: str,
        content_type: str,
        size: int,
        content_hash: str,
        resume_id: UUID | None = None,
    ) -> ResumeVersion:
        requested = resume_id is not None
        resume_id = resume_id or uuid4()
        with self.database.session() as session:
            records = list(
                session.scalars(
                    select(ResumeVersionRecord).where(
                        ResumeVersionRecord.resume_id == str(resume_id)
                    )
                )
            )
            if requested and not records:
                raise KeyError(resume_id)
            if any(record.content_hash == content_hash for record in records):
                raise ValueError("this resume version already exists")
            record = ResumeVersionRecord(
                version_id=str(uuid4()),
                resume_id=str(resume_id),
                version=max((item.version for item in records), default=0) + 1,
                label=label,
                filename=filename,
                content_type=content_type,
                size=size,
                content_hash=content_hash,
            )
            session.add(record)
            session.flush()
            return self._view(session, record)

    def list(self) -> list[ResumeVersion]:
        with self.database.session() as session:
            records = session.scalars(
                select(ResumeVersionRecord).order_by(desc(ResumeVersionRecord.created_at))
            )
            return [self._view(session, record) for record in records]

    def get(self, version_id: UUID) -> ResumeVersion:
        with self.database.session() as session:
            record = session.get(ResumeVersionRecord, str(version_id))
            if not record:
                raise KeyError(version_id)
            return self._view(session, record)

    def set_current(self, version_id: UUID, application_id: UUID) -> ResumeVersion:
        with self.database.session() as session:
            record = session.get(ResumeVersionRecord, str(version_id))
            if not record or not session.get(ApplicationRecord, str(application_id)):
                raise KeyError(version_id)
            session.execute(
                delete(ApplicationResumeRecord).where(
                    ApplicationResumeRecord.application_id == str(application_id)
                )
            )
            session.add(
                ApplicationResumeRecord(
                    application_id=str(application_id), version_id=str(version_id)
                )
            )
            session.flush()
            return self._view(session, record)

    def delete_resume(self, resume_id: UUID) -> tuple[str, ...]:
        with self.database.session() as session:
            records = list(
                session.scalars(
                    select(ResumeVersionRecord).where(
                        ResumeVersionRecord.resume_id == str(resume_id)
                    )
                )
            )
            if not records:
                raise KeyError(resume_id)
            version_ids = [record.version_id for record in records]
            hashes = tuple({record.content_hash for record in records})
            session.execute(
                delete(ApplicationResumeRecord).where(
                    ApplicationResumeRecord.version_id.in_(version_ids)
                )
            )
            session.execute(
                delete(ResumeVersionRecord).where(ResumeVersionRecord.resume_id == str(resume_id))
            )
            return hashes


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
                checkpoint.step = step
                checkpoint.payload = {**checkpoint.payload, **payload}
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

    def list(self) -> list[PersistentJob]:
        with self.database.session() as session:
            records = session.scalars(
                select(BackgroundJobRecord).order_by(desc(BackgroundJobRecord.created_at))
            )
            return [self._view(session, record) for record in records]

    def complete(self, job_id: UUID, payload: dict[str, Any]) -> PersistentJob:
        self.progress(job_id, "completed", payload)
        with self.database.session() as session:
            record = session.get(BackgroundJobRecord, str(job_id))
            if not record:
                raise KeyError(job_id)
            record.status, record.updated_at = "succeeded", utcnow()
            session.flush()
            return self._view(session, record)

    def fail(self, job_id: UUID, error_code: str, message: str) -> PersistentJob:
        with self.database.session() as session:
            record = session.get(BackgroundJobRecord, str(job_id))
            if not record:
                raise KeyError(job_id)
            record.status = "failed"
            record.current_step = "failed"
            record.error_code = error_code[:100]
            record.error_message_safe = message[:500]
            record.updated_at = utcnow()
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
            error_code=record.error_code,
            error_message_safe=record.error_message_safe,
        )


class SummaryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def append(self, application_id: UUID, content: dict[str, Any]) -> SummaryVersion:
        with self.database.session() as session:
            if not session.get(ApplicationRecord, str(application_id)):
                raise KeyError(application_id)
            latest = session.scalar(
                select(SummaryVersionRecord)
                .where(SummaryVersionRecord.application_id == str(application_id))
                .order_by(desc(SummaryVersionRecord.version))
            )
            record = SummaryVersionRecord(
                summary_id=str(uuid4()),
                application_id=str(application_id),
                version=(latest.version + 1) if latest else 1,
                content=content,
            )
            session.add(record)
            session.flush()
            return self._view(record)

    def list(self, application_id: UUID) -> list[SummaryVersion]:
        with self.database.session() as session:
            records = session.scalars(
                select(SummaryVersionRecord)
                .where(SummaryVersionRecord.application_id == str(application_id))
                .order_by(desc(SummaryVersionRecord.version))
            )
            return [self._view(record) for record in records]

    def latest(self, application_id: UUID) -> SummaryVersion | None:
        versions = self.list(application_id)
        return versions[0] if versions else None

    @staticmethod
    def _view(record: SummaryVersionRecord) -> SummaryVersion:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return SummaryVersion(
            summary_id=UUID(record.summary_id),
            application_id=UUID(record.application_id),
            version=record.version,
            content=dict(record.content),
            created_at=created_at,
        )
