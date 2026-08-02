from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column

from careerpilot.core import ApplicationRecord, Base, Database, MailAccountRecord, utcnow
from careerpilot.secrets import SecretStore

Provider = Literal["gmail", "outlook"]
PREFILL_FIELDS = {
    "full_name",
    "email",
    "phone",
    "location",
    "website",
    "linkedin",
}
PROVIDERS: dict[str, dict[str, object]] = {
    "gmail": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["openid", "email", "https://www.googleapis.com/auth/gmail.readonly"],
        "extra": {"access_type": "offline", "prompt": "consent"},
    },
    "outlook": {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "openid",
            "email",
            "offline_access",
            "https://graph.microsoft.com/Mail.Read",
        ],
        "extra": {"prompt": "select_account"},
    },
}


class OAuthConnectionRecord(Base):
    __tablename__ = "oauth_connections"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("mail_accounts.account_id"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    scopes: Mapped[list[str]] = mapped_column(JSON)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReminderRecord(Base):
    __tablename__ = "reminders"
    reminder_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"))
    title: Mapped[str] = mapped_column(String(300))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NotificationRecord(Base):
    __tablename__ = "notification_events"
    notification_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reminder_id: Mapped[str] = mapped_column(ForeignKey("reminders.reminder_id"))
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PrefillSessionRecord(Base):
    __tablename__ = "prefill_sessions"
    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"))
    target_origin: Mapped[str] = mapped_column(String(500))
    field_values: Mapped[dict[str, str]] = mapped_column(JSON)
    diff: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30))
    captcha_required: Mapped[bool] = mapped_column(Boolean)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@dataclass(frozen=True)
class OAuthConnection:
    account_id: str
    provider: str
    email: str
    status: str
    scopes: list[str]
    token_expires_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Reminder:
    reminder_id: UUID
    application_id: UUID
    company: str
    role: str
    title: str
    due_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Notification:
    notification_id: UUID
    reminder_id: UUID
    application_id: UUID
    company: str
    role: str
    title: str
    due_at: datetime
    kind: str
    status: str
    created_at: datetime
    read_at: datetime | None


@dataclass(frozen=True)
class PrefillSession:
    session_id: UUID
    application_id: UUID
    company: str
    role: str
    target_origin: str
    field_values: dict[str, str]
    diff: list[dict[str, str]]
    status: str
    captcha_required: bool
    created_at: datetime
    updated_at: datetime


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class OAuthConnectionService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _view(record: OAuthConnectionRecord, account: MailAccountRecord) -> OAuthConnection:
        return OAuthConnection(
            account_id=record.account_id,
            provider=record.provider,
            email=account.email,
            status=record.status,
            scopes=list(record.scopes),
            token_expires_at=record.token_expires_at,
            last_error=record.last_error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def list(self) -> list[OAuthConnection]:
        with self.database.session() as session:
            records = session.scalars(
                select(OAuthConnectionRecord).order_by(OAuthConnectionRecord.created_at)
            )
            return [
                self._view(record, account)
                for record in records
                if (account := session.get(MailAccountRecord, record.account_id))
            ]

    def set_status(
        self,
        account_id: str,
        provider: Provider,
        status: str,
        *,
        expires_at: datetime | None = None,
        error: str | None = None,
    ) -> OAuthConnection:
        with self.database.session() as session:
            account = session.get(MailAccountRecord, account_id)
            if not account or account.adapter != provider:
                raise KeyError(account_id)
            record = session.get(OAuthConnectionRecord, account_id)
            if not record:
                record = OAuthConnectionRecord(
                    account_id=account_id,
                    provider=provider,
                    status=status,
                    scopes=list(PROVIDERS[provider]["scopes"]),
                )
                session.add(record)
            record.status = status
            record.token_expires_at = expires_at
            record.last_error = error
            record.updated_at = utcnow()
            session.flush()
            return self._view(record, account)


TokenRequest = Any


def request_token(url: str, payload: dict[str, str]) -> dict[str, object]:
    request = Request(
        url,
        data=urlencode(payload).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "CareerPilot/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            value = json.loads(response.read(1_000_000))
    except HTTPError as exc:
        raise PermissionError("OAuth token exchange was rejected") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ConnectionError("OAuth token exchange failed") from exc
    if not isinstance(value, dict):
        raise ConnectionError("OAuth provider returned invalid JSON")
    return value


class OAuthCoordinator:
    def __init__(
        self,
        connections: OAuthConnectionService,
        secret_store: SecretStore,
        *,
        token_request: TokenRequest = request_token,
    ) -> None:
        self.connections = connections
        self.secret_store = secret_store
        self.token_request = token_request
        self.pending: dict[str, dict[str, object]] = {}
        self.runtime_tokens: dict[str, dict[str, object]] = {}
        self.lock = threading.Lock()

    @staticmethod
    def token_name(provider: str, account_id: str) -> str:
        return f"oauth.{provider}.{account_id}.token"

    def has_token(self, provider: str, account_id: str) -> bool:
        name = self.token_name(provider, account_id)
        return name in self.runtime_tokens or bool(self.secret_store.get_named(name))

    def start(
        self,
        provider: Provider,
        account_id: str,
        redirect_uri: str,
    ) -> tuple[str, OAuthConnection]:
        configuration = PROVIDERS[provider]
        client_id = self.secret_store.get_named(f"oauth.{provider}.client_id")
        if not client_id:
            raise ValueError(f"{provider} OAuth client ID is not configured")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        with self.lock:
            self.pending[state] = {
                "provider": provider,
                "account_id": account_id,
                "redirect_uri": redirect_uri,
                "verifier": verifier,
                "created_at": utcnow(),
            }
        connection = self.connections.set_status(account_id, provider, "authorizing")
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(configuration["scopes"]),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            **configuration["extra"],
        }
        return f"{configuration['authorize_url']}?{urlencode(query)}", connection

    def complete(self, provider: Provider, state: str, code: str) -> OAuthConnection:
        with self.lock:
            pending = self.pending.pop(state, None)
        if (
            not pending
            or pending["provider"] != provider
            or utcnow() - _aware(pending["created_at"]) > timedelta(minutes=10)
        ):
            raise PermissionError("OAuth state is invalid or expired")
        if not getattr(self.secret_store, "writable", True):
            raise RuntimeError("runtime-injected secrets are read-only")
        client_id = self.secret_store.get_named(f"oauth.{provider}.client_id")
        if not client_id:
            raise ValueError(f"{provider} OAuth client ID is not configured")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": str(pending["redirect_uri"]),
            "code_verifier": str(pending["verifier"]),
        }
        if client_secret := self.secret_store.get_named(f"oauth.{provider}.client_secret"):
            payload["client_secret"] = client_secret
        token = self.token_request(str(PROVIDERS[provider]["token_url"]), payload)
        return self._store_token(provider, str(pending["account_id"]), token)

    def access_token(self, provider: Provider, account_id: str) -> str:
        name = self.token_name(provider, account_id)
        token = self.runtime_tokens.get(name)
        try:
            token = token or json.loads(self.secret_store.get_named(name) or "")
            expires_at = datetime.fromisoformat(str(token["expires_at"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise PermissionError("OAuth token is invalid") from exc
        access_token = token.get("access_token")
        if isinstance(access_token, str) and _aware(expires_at) > utcnow() + timedelta(seconds=60):
            return access_token
        refresh_token = token.get("refresh_token")
        client_id = self.secret_store.get_named(f"oauth.{provider}.client_id")
        if not isinstance(refresh_token, str) or not client_id:
            raise PermissionError("OAuth token cannot be refreshed")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
        if provider == "outlook":
            payload["scope"] = " ".join(PROVIDERS[provider]["scopes"])
        if client_secret := self.secret_store.get_named(f"oauth.{provider}.client_secret"):
            payload["client_secret"] = client_secret
        refreshed = self.token_request(str(PROVIDERS[provider]["token_url"]), payload)
        refreshed.setdefault("refresh_token", refresh_token)
        connection = self._normalized_token(refreshed)
        self.runtime_tokens[name] = connection
        if getattr(self.secret_store, "writable", True):
            self.secret_store.set_named(name, json.dumps(connection))
        return str(connection["access_token"])

    def disconnect(self, provider: Provider, account_id: str) -> OAuthConnection:
        deleter = getattr(self.secret_store, "delete_named", None)
        if deleter:
            deleter(self.token_name(provider, account_id))
        elif self.has_token(provider, account_id):
            raise RuntimeError("secret store cannot remove OAuth tokens")
        return self.connections.set_status(account_id, provider, "disconnected")

    def _store_token(
        self, provider: Provider, account_id: str, token: dict[str, object]
    ) -> OAuthConnection:
        value = self._normalized_token(token)
        self.secret_store.set_named(self.token_name(provider, account_id), json.dumps(value))
        return self.connections.set_status(
            account_id,
            provider,
            "connected",
            expires_at=datetime.fromisoformat(str(value["expires_at"])),
        )

    @staticmethod
    def _normalized_token(token: dict[str, object]) -> dict[str, object]:
        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise PermissionError("OAuth provider did not return an access token")
        try:
            lifetime = min(max(int(token.get("expires_in", 3600)), 60), 86400)
        except (TypeError, ValueError):
            lifetime = 3600
        value: dict[str, object] = {
            "access_token": access_token,
            "expires_at": (utcnow() + timedelta(seconds=lifetime)).isoformat(),
        }
        if isinstance(token.get("refresh_token"), str):
            value["refresh_token"] = token["refresh_token"]
        if isinstance(token.get("scope"), str):
            value["scope"] = token["scope"]
        return value


class ReminderService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _view(record: ReminderRecord, application: ApplicationRecord) -> Reminder:
        return Reminder(
            reminder_id=UUID(record.reminder_id),
            application_id=UUID(record.application_id),
            company=application.company,
            role=application.role,
            title=record.title,
            due_at=record.due_at,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create(
        self,
        application_id: UUID,
        title: str,
        due_at: datetime,
        idempotency_key: str,
    ) -> Reminder:
        title = title.strip()
        if not title or len(title) > 300:
            raise ValueError("invalid reminder title")
        if due_at.tzinfo is None:
            raise ValueError("reminder time must include a timezone")
        with self.database.session() as session:
            existing = session.scalar(
                select(ReminderRecord).where(ReminderRecord.idempotency_key == idempotency_key)
            )
            if existing:
                application = session.get(ApplicationRecord, existing.application_id)
                return self._view(existing, application)
            application = session.get(ApplicationRecord, str(application_id))
            if not application:
                raise KeyError(application_id)
            record = ReminderRecord(
                reminder_id=str(uuid4()),
                application_id=str(application_id),
                title=title,
                due_at=due_at.astimezone(UTC),
                status="scheduled",
                idempotency_key=idempotency_key,
            )
            session.add(record)
            session.flush()
            return self._view(record, application)

    def list(self, application_id: UUID | None = None) -> list[Reminder]:
        with self.database.session() as session:
            statement = select(ReminderRecord).order_by(ReminderRecord.due_at)
            if application_id:
                statement = statement.where(
                    ReminderRecord.application_id == str(application_id)
                )
            records = session.scalars(statement)
            return [
                self._view(record, application)
                for record in records
                if (application := session.get(ApplicationRecord, record.application_id))
            ]

    def dismiss(self, reminder_id: UUID) -> Reminder:
        with self.database.session() as session:
            record = session.get(ReminderRecord, str(reminder_id))
            if not record:
                raise KeyError(reminder_id)
            record.status = "dismissed"
            record.updated_at = utcnow()
            application = session.get(ApplicationRecord, record.application_id)
            return self._view(record, application)

    def scan(self, now: datetime | None = None) -> list[Notification]:
        now = (now or utcnow()).astimezone(UTC)
        horizon = now + timedelta(days=3)
        with self.database.session() as session:
            reminders = session.scalars(
                select(ReminderRecord).where(
                    ReminderRecord.status == "scheduled",
                    ReminderRecord.due_at <= horizon,
                )
            )
            for reminder in reminders:
                due_at = _aware(reminder.due_at)
                kind = "overdue" if due_at <= now else "urgent" if due_at <= now + timedelta(days=1) else "upcoming"
                key = f"reminder:{reminder.reminder_id}:{kind}"
                if not session.scalar(
                    select(NotificationRecord).where(NotificationRecord.idempotency_key == key)
                ):
                    session.add(
                        NotificationRecord(
                            notification_id=str(uuid4()),
                            reminder_id=reminder.reminder_id,
                            kind=kind,
                            status="unread",
                            idempotency_key=key,
                        )
                    )
            session.flush()
            records = session.scalars(
                select(NotificationRecord).order_by(NotificationRecord.created_at.desc())
            )
            return [self._notification_view(session, record) for record in records]

    def notifications(self) -> list[Notification]:
        with self.database.session() as session:
            records = session.scalars(
                select(NotificationRecord).order_by(NotificationRecord.created_at.desc())
            )
            return [self._notification_view(session, record) for record in records]

    def read(self, notification_id: UUID) -> Notification:
        with self.database.session() as session:
            record = session.get(NotificationRecord, str(notification_id))
            if not record:
                raise KeyError(notification_id)
            record.status = "read"
            record.read_at = utcnow()
            session.flush()
            return self._notification_view(session, record)

    @staticmethod
    def _notification_view(session: Any, record: NotificationRecord) -> Notification:
        reminder = session.get(ReminderRecord, record.reminder_id)
        application = session.get(ApplicationRecord, reminder.application_id)
        return Notification(
            notification_id=UUID(record.notification_id),
            reminder_id=UUID(record.reminder_id),
            application_id=UUID(reminder.application_id),
            company=application.company,
            role=application.role,
            title=reminder.title,
            due_at=reminder.due_at,
            kind=record.kind,
            status=record.status,
            created_at=record.created_at,
            read_at=record.read_at,
        )

    def ics(self, application_id: UUID | None = None) -> str:
        reminders = [item for item in self.list(application_id) if item.status == "scheduled"]
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//CareerPilot//Stage 7//ZH-CN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]
        for item in reminders:
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{item.reminder_id}@careerpilot.local",
                    f"DTSTAMP:{_ics_time(utcnow())}",
                    f"DTSTART:{_ics_time(item.due_at)}",
                    "DURATION:PT30M",
                    f"SUMMARY:{_ics_text(item.title)}",
                    f"DESCRIPTION:{_ics_text(f'{item.company} / {item.role}')}",
                    "END:VEVENT",
                ]
            )
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"


def _ics_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _ics_time(value: datetime) -> str:
    return _aware(value).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


class PrefillService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _view(record: PrefillSessionRecord, application: ApplicationRecord) -> PrefillSession:
        return PrefillSession(
            session_id=UUID(record.session_id),
            application_id=UUID(record.application_id),
            company=application.company,
            role=application.role,
            target_origin=record.target_origin,
            field_values=dict(record.field_values),
            diff=list(record.diff),
            status=record.status,
            captcha_required=record.captcha_required,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create(
        self,
        application_id: UUID,
        target_url: str,
        profile: dict[str, str],
        idempotency_key: str,
    ) -> PrefillSession:
        origin = _target_origin(target_url)
        values = {
            key: str(value).strip()[:500]
            for key, value in profile.items()
            if key in PREFILL_FIELDS and str(value).strip()
        }
        if not values:
            raise ValueError("at least one safe prefill field is required")
        with self.database.session() as session:
            existing = session.scalar(
                select(PrefillSessionRecord).where(
                    PrefillSessionRecord.idempotency_key == idempotency_key
                )
            )
            if existing:
                application = session.get(ApplicationRecord, existing.application_id)
                return self._view(existing, application)
            application = session.get(ApplicationRecord, str(application_id))
            if not application:
                raise KeyError(application_id)
            record = PrefillSessionRecord(
                session_id=str(uuid4()),
                application_id=str(application_id),
                target_origin=origin,
                field_values=values,
                diff=[],
                status="draft",
                captcha_required=False,
                idempotency_key=idempotency_key,
            )
            session.add(record)
            session.flush()
            return self._view(record, application)

    def get(self, session_id: UUID) -> PrefillSession:
        with self.database.session() as session:
            record = session.get(PrefillSessionRecord, str(session_id))
            if not record:
                raise KeyError(session_id)
            application = session.get(ApplicationRecord, record.application_id)
            return self._view(record, application)

    def handoff(
        self,
        session_id: UUID,
        diff: list[dict[str, str]],
        *,
        captcha_required: bool,
    ) -> PrefillSession:
        if len(diff) > 100:
            raise ValueError("prefill diff is too large")
        with self.database.session() as session:
            record = session.get(PrefillSessionRecord, str(session_id))
            if not record:
                raise KeyError(session_id)
            cleaned: list[dict[str, str]] = []
            for item in diff:
                key = str(item.get("field_key", ""))
                if key not in record.field_values:
                    raise ValueError("prefill diff contains an unknown field")
                next_value = str(item.get("next_value", ""))
                if next_value != record.field_values[key]:
                    raise ValueError("prefill diff does not match the approved payload")
                cleaned.append(
                    {
                        "field_key": key,
                        "label": str(item.get("label", ""))[:300],
                        "current_value": str(item.get("current_value", ""))[:500],
                        "next_value": next_value,
                    }
                )
            record.diff = cleaned
            record.captcha_required = captcha_required
            record.status = "blocked_captcha" if captcha_required else "handed_off"
            record.updated_at = utcnow()
            application = session.get(ApplicationRecord, record.application_id)
            return self._view(record, application)


def _target_origin(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("target form must use a public HTTPS URL")
    try:
        host = parsed.hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("target form URL is invalid") from exc
    port = f":{parsed.port}" if parsed.port else ""
    return f"https://{host}{port}"
