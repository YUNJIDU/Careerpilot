from __future__ import annotations

import hashlib
import imaplib
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from uuid import UUID

from careerpilot.core import (
    ApplicationService,
    Database,
    EmailService,
    ExcelSyncService,
    JobService,
    StoredEmail,
    normalize_identity,
)

MAX_MESSAGE_BYTES = 2 * 1024 * 1024
MAX_TEXT_LENGTH = 100_000


@dataclass
class MailItem:
    message_id: str | None
    sender: str
    subject: str
    sent_at: datetime | None
    text: str
    raw_hash: str


class MailAdapter(Protocol):
    def fetch(self) -> list[MailItem]: ...


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value[:MAX_TEXT_LENGTH])
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _body(message: Message) -> str:
    if message.is_multipart():
        plain: list[str] = []
        html: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            try:
                content = part.get_content()
            except (LookupError, UnicodeError):
                continue
            if not isinstance(content, str):
                continue
            (plain if part.get_content_type() == "text/plain" else html).append(content)
        value = "\n".join(plain) if plain else html_to_text("\n".join(html))
    else:
        try:
            content = message.get_content()
        except (LookupError, UnicodeError):
            content = ""
        value = content if isinstance(content, str) else ""
        if message.get_content_type() == "text/html":
            value = html_to_text(value)
    return value[:MAX_TEXT_LENGTH]


def parse_message(raw: bytes) -> MailItem:
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("message exceeds 2 MiB")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sent_at = None
    if message.get("Date"):
        try:
            sent_at = parsedate_to_datetime(str(message["Date"]))
        except (TypeError, ValueError):
            pass
    return MailItem(
        message_id=str(message["Message-ID"]) if message.get("Message-ID") else None,
        sender=str(message.get("From", ""))[:500],
        subject=str(message.get("Subject", ""))[:500],
        sent_at=sent_at,
        text=_body(message),
        raw_hash=hashlib.sha256(raw).hexdigest(),
    )


class FixtureMailAdapter:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def fetch(self) -> list[MailItem]:
        items: list[MailItem] = []
        for path in sorted(self.directory.glob("*.eml")):
            try:
                items.append(parse_message(path.read_bytes()))
            except (OSError, ValueError):
                continue
        return items


class Imap163Adapter:
    def __init__(
        self,
        email: str,
        authorization_code: str,
        *,
        since: date,
        limit: int = 100,
        client_factory: object = imaplib.IMAP4_SSL,
    ) -> None:
        self.email = email
        self.authorization_code = authorization_code
        self.since = since
        self.limit = min(max(limit, 1), 500)
        self.client_factory = client_factory

    def test_connection(self) -> None:
        client = self._connect()
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise ConnectionError("163 inbox is unavailable")
        finally:
            client.logout()

    def fetch(self) -> list[MailItem]:
        client = self._connect()
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise ConnectionError("163 inbox is unavailable")
            status, data = client.search(None, "SINCE", self.since.strftime("%d-%b-%Y"))
            if status != "OK":
                raise ConnectionError("163 search failed")
            message_ids = data[0].split()[-self.limit :] if data and data[0] else []
            items: list[MailItem] = []
            for message_id in message_ids:
                status, payload = client.fetch(message_id, "(BODY.PEEK[])")
                if status != "OK":
                    continue
                raw = next(
                    (
                        part[1]
                        for part in payload
                        if isinstance(part, tuple)
                        and len(part) > 1
                        and isinstance(part[1], bytes)
                    ),
                    None,
                )
                if raw:
                    try:
                        items.append(parse_message(raw))
                    except ValueError:
                        continue
            return items
        finally:
            client.logout()

    def _connect(self) -> object:
        if not re.fullmatch(r"[^@\s\"]+@[^@\s\"]+\.[^@\s\"]+", self.email):
            raise ValueError("invalid email address")
        client = self.client_factory("imap.163.com", 993, timeout=15)
        status, _ = client.login(self.email, self.authorization_code)
        if status != "OK":
            client.logout()
            raise ConnectionError("163 authentication failed")
        status, _ = client.xatom(
            "ID",
            (
                '("name" "CareerPilot" "version" "0.1.0" '
                f'"vendor" "CareerPilot" "support-email" "{self.email}")'
            ),
        )
        if status != "OK":
            client.logout()
            raise ConnectionError("163 client identity was rejected")
        return client


_PATTERNS = {
    "公司名称": re.compile(r"(?:公司名称|公司)[：:]\s*([^\n\r<]+)"),
    "岗位": re.compile(r"(?:岗位名称|岗位|职位)[：:]\s*([^\n\r<]+)"),
    "当前阶段": re.compile(r"(?:当前阶段|阶段)[：:]\s*([^\n\r<]+)"),
    "截止时间": re.compile(r"(?:截止时间|截止日期)[：:]\s*(\d{4}-\d{2}-\d{2})"),
    "JD 链接": re.compile(r"(?:JD\s*链接|职位链接)[：:]\s*(https?://[^\s<]+)"),
}
_JOB_KEYWORDS = re.compile(
    r"招聘|应聘|职位|岗位|面试|笔试|测评|录用|offer|application|interview|assessment",
    re.IGNORECASE,
)


def extract_facts(value: str, sender: str = "") -> dict[str, object]:
    text = html_to_text(value) if "<" in value and ">" in value else value
    facts: dict[str, object] = {}
    for field, pattern in _PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        extracted: object = match.group(1).strip()
        if field == "截止时间":
            try:
                extracted = date.fromisoformat(str(extracted))
            except ValueError:
                continue
        facts[field] = extracted
    if "公司名称" not in facts:
        company_patterns = (
            r"感谢您投递【([^】]+)】",
            r"成功投递([A-Za-z0-9\u4e00-\u9fff]+?)20\d{2}届",
            r"^【([^】]+)】",
            r"^(.+?)(?:20\d{2}年)公开招聘",
        )
        for pattern in company_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                company = re.sub(r"(?:校园招聘|招聘)$", "", match.group(1).strip())
                if company and company not in {"本公司", "我公司"}:
                    facts["公司名称"] = company
                    break
    if "岗位" not in facts:
        role_patterns = (
            r"投递【[^】]+】的(.+?)职位",
            r"(?:我公司|本公司)的?(.+?)职位",
            r"投递\s+(?:NIO)?(.+?)岗位",
            r"——(.+?)(?:\n|$)",
            r"感谢投递(.+?)(?:\n|$)",
        )
        for pattern in role_patterns:
            match = re.search(pattern, text)
            if match:
                role = match.group(1).strip(" ！!-")
                if role:
                    facts["岗位"] = role
                    break
    if "公司名称" not in facts and "岗位" in facts and re.search(r"我公司|本公司", text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            signature = lines[-1]
            if (
                2 <= len(signature) <= 50
                and not re.search(r"[，。！？：；]", signature)
                and not re.search(r"我公司|本公司|职位|岗位", signature)
                and re.search(r"[A-Za-z\u4e00-\u9fff]", signature)
            ):
                facts["公司名称"] = signature
        if "公司名称" not in facts:
            display_name = parseaddr(sender)[0].strip()
            if re.search(
                r"公司|集团|科技|银行|招聘|人才|人力|大学|学院|研究院|ArcSoft|虹软",
                display_name,
                re.IGNORECASE,
            ):
                facts["公司名称"] = display_name
    if "当前阶段" not in facts:
        if re.search(r"(?:笔试|考试)成绩.{0,12}(?:查询|公布|发布|开放|可查|已开通)", text):
            facts["当前阶段"] = "笔试成绩可查询"
        elif re.search(r"完善简历", text):
            facts["当前阶段"] = "简历待完善"
        elif re.search(
            r"投递成功|提交成功|感谢.{0,8}(?:投递|应聘)|"
            r"(?:已经|已|我们已经)?收到.{0,4}(?:您的)?(?:简历|申请)",
            text,
        ):
            facts["当前阶段"] = "已投递"
    return facts


def is_job_candidate(item: MailItem) -> bool:
    return bool(_JOB_KEYWORDS.search(f"{item.subject}\n{item.text[:5000]}"))


class MailSyncService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.applications = ApplicationService(database)
        self.emails = EmailService(database)
        self.excel = ExcelSyncService(database, self.applications)
        self.jobs = JobService(database)

    def sync(
        self,
        adapter: MailAdapter,
        account_id: str,
        tracker_path: Path,
        idempotency_key: str,
    ) -> int:
        job = self.jobs.create("mail_sync", idempotency_key)
        if tracker_path.exists():
            self.excel.import_workbook(
                tracker_path, f"{idempotency_key}:tracker-import"
            )
        self._reconcile_linked_mail()
        processed = 0
        for item in adapter.fetch():
            if not is_job_candidate(item):
                continue
            exists, linked_application_id = self.emails.find(
                account_id, item.raw_hash, item.message_id
            )
            if linked_application_id:
                continue
            facts = extract_facts(f"{item.subject}\n{item.text}", item.sender)
            company, role = facts.get("公司名称"), facts.get("岗位")
            if company and not role and facts.get("当前阶段"):
                role = facts["岗位"] = "岗位待确认"
            application_id = None
            if company and role:
                application = next(
                    (
                        candidate
                        for candidate in self.applications.list()
                        if normalize_identity(candidate.company)
                        == normalize_identity(str(company))
                        and normalize_identity(candidate.role)
                        == normalize_identity(str(role))
                    ),
                    None,
                )
                application = application or self.applications.create(
                    str(company),
                    str(role),
                    idempotency_key=f"mail-app:{company}:{role}",
                )
                application_id = application.application_id
                for field, value in facts.items():
                    if field in {"公司名称", "岗位"}:
                        continue
                    if field == "当前阶段" and item.sent_at:
                        continue
                    self.applications.apply_field_change(
                        application.application_id,
                        field,
                        value,
                        source="mail",
                        idempotency_key=f"mail:{item.raw_hash}:{field}",
                        evidence=f"{field}: {value}"[:500],
                    )
            if exists:
                if application_id:
                    self.emails.link(item.raw_hash, application_id, facts)
                else:
                    continue
            else:
                self.emails.record(
                    account_id=account_id,
                    raw_hash=item.raw_hash,
                    message_id=item.message_id,
                    subject=item.subject,
                    sender=item.sender,
                    sent_at=item.sent_at,
                    application_id=application_id,
                    facts=facts,
                )
            processed += 1
            self.jobs.progress(
                job.job_id,
                "message_committed",
                {"last_message_id": item.message_id, "processed": processed},
            )
        self._reconcile_linked_mail()
        self.excel.export_workbook(tracker_path)
        self.jobs.complete(job.job_id, {"processed": processed})
        return processed

    def _reconcile_linked_mail(self) -> None:
        by_application: dict[UUID, list[StoredEmail]] = {}
        for email in self.emails.linked():
            by_application.setdefault(email.application_id, []).append(email)
        for application_id, emails in by_application.items():
            emails.sort(key=lambda email: self._naive_utc(email.sent_at))
            receipt = next(
                (
                    email
                    for email in emails
                    if email.facts.get("当前阶段") == "已投递"
                ),
                None,
            )
            if receipt:
                sent_at = self._naive_utc(receipt.sent_at)
                self.applications.apply_field_change(
                    application_id,
                    "投递时间",
                    sent_at.date(),
                    source="mail_authoritative",
                    idempotency_key=f"reconcile:{receipt.raw_hash}:投递时间",
                    evidence=f"Date: {receipt.sent_at.isoformat()}",
                )
            latest = emails[-1]
            sent_at = self._naive_utc(latest.sent_at)
            self.applications.apply_field_change(
                application_id,
                "最近更新时间",
                sent_at,
                source="mail_authoritative",
                idempotency_key=f"reconcile:{latest.raw_hash}:最近更新时间",
                evidence=f"Date: {latest.sent_at.isoformat()}",
            )
            stage = latest.facts.get("当前阶段")
            user_changed = self.applications.latest_user_change(
                application_id, "当前阶段"
            )
            if stage and (
                not user_changed
                or sent_at > self._naive_utc(user_changed)
            ):
                self.applications.apply_field_change(
                    application_id,
                    "当前阶段",
                    stage,
                    source="mail_authoritative",
                    idempotency_key=f"reconcile:{latest.raw_hash}:当前阶段",
                    evidence=f"当前阶段: {stage}",
                )

    @staticmethod
    def _naive_utc(value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
