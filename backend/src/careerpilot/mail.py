from __future__ import annotations

import hashlib
import imaplib
import re
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
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
    PROCESS_FIELDS,
    ApplicationService,
    Database,
    EmailService,
    ExcelSyncService,
    JobService,
    PersistentJob,
    normalize_identity,
    terminal_label,
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
    def fetch(self) -> Iterable[MailItem]: ...


class MailSyncError(RuntimeError):
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id
        super().__init__("mail sync failed")


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
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.email = email
        self.authorization_code = authorization_code
        self.since = since
        self.limit = min(max(limit, 1), 500)
        self.client_factory = client_factory
        self.sleep = sleep

    def test_connection(self) -> None:
        self._retry(self._test_connection_once)

    def _test_connection_once(self) -> None:
        client = self._connect()
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise ConnectionError("163 inbox is unavailable")
        finally:
            with suppress(Exception):
                client.logout()

    def fetch(self) -> list[MailItem]:
        return self._retry(self._fetch_once)

    def _fetch_once(self) -> list[MailItem]:
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
                        if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], bytes)
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
            with suppress(Exception):
                client.logout()

    def _retry(self, operation: Callable[[], object]):
        for attempt in range(3):
            try:
                return operation()
            except PermissionError:
                raise
            except (imaplib.IMAP4.abort, ConnectionError, OSError, TimeoutError):
                if attempt == 2:
                    raise
                self.sleep(attempt + 1)
        raise AssertionError("unreachable")

    def _connect(self) -> object:
        if not re.fullmatch(r"[^@\s\"]+@[^@\s\"]+\.[^@\s\"]+", self.email):
            raise ValueError("invalid email address")
        client = self.client_factory("imap.163.com", 993, timeout=15)
        status, _ = client.login(self.email, self.authorization_code)
        if status != "OK":
            client.logout()
            raise PermissionError("163 authentication failed")
        status, _ = client.xatom(
            "ID",
            (
                '("name" "CareerPilot" "version" "0.1.0" '
                f'"vendor" "CareerPilot" "support-email" "{self.email}")'
            ),
        )
        if status != "OK":
            client.logout()
            raise PermissionError("163 client identity was rejected")
        return client


_PATTERNS = {
    "公司名称": re.compile(r"(?:公司名称|公司)[：:]\s*([^\n\r<]+)"),
    "岗位": re.compile(r"(?:岗位名称|岗位|职位)[：:]\s*([^\n\r<]+)"),
    "当前阶段": re.compile(r"(?:当前阶段|阶段)[：:]\s*([^\n\r<]+)"),
    "截止时间": re.compile(r"(?:截止时间|截止日期)[：:]\s*(\d{4}-\d{2}-\d{2})"),
    "JD 链接": re.compile(r"(?:JD\s*链接|职位链接)[：:]\s*(https?://[^\s<]+)"),
}
_JOB_KEYWORDS = re.compile(
    r"招聘|应聘|职位|岗位|简历|筛选|面试|笔试|测评|录用|offer|"
    r"application|interview|assessment",
    re.IGNORECASE,
)


def _is_role(value: str, company: str = "") -> bool:
    if len(value) > 100 or re.search(r"[，。；！？]", value):
        return False
    if re.search(
        r"(?:人力资源部|招聘(?:团队|部门|组)|校园招聘(?:团队|组)|人才招聘(?:中心|团队))$",
        value,
    ):
        return False
    return not (
        company
        and re.fullmatch(
            rf"{re.escape(company)}20\d{{2}}(?:届)?(?:校园招聘|校招)[。！!]*",
            value,
        )
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
    role = str(facts.get("岗位") or "")
    if role and not _is_role(role, str(facts.get("公司名称") or "")):
        facts.pop("岗位", None)
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
                if role and _is_role(role, str(facts.get("公司名称") or "")):
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
        if re.search(
            r"很遗憾.{0,40}(?:未通过|无法进入|不能进入)|"
            r"未能通过|不再进入下一轮|不予录用|"
            r"无法邀请.{0,30}(?:继续参与|进入).{0,20}后续流程|"
            r"(?:招聘|应聘|面试|笔试)?流程.{0,8}(?:终止|结束)",
            text,
        ):
            step = next(
                (candidate for candidate in reversed(PROCESS_FIELDS) if candidate in text),
                "简历通过" if "简历" in text else "流程",
            )
            if step in PROCESS_FIELDS:
                facts[step] = "未通过"
            display_step = "简历" if step == "简历通过" else step
            facts["当前阶段"] = terminal_label(display_step, "未通过")
        elif re.search(
            r"AI\s*面试.{0,20}(?:邀请|安排)|邀请.{0,20}AI\s*面试",
            text,
            re.IGNORECASE,
        ):
            facts["一面"] = "AI 面试"
            facts["当前阶段"] = "一面"
        elif re.search(
            r"(?:线上|在线)?测评.{0,20}(?:邀请|安排)|邀请.{0,20}(?:线上|在线)?测评", text
        ):
            facts["测评"] = "待完成"
            facts["当前阶段"] = "测评"
        elif re.search(r"(?:笔试|考试).{0,20}(?:邀请|安排)|邀请.{0,20}(?:笔试|考试)", text):
            facts["笔试"] = "待完成"
            facts["当前阶段"] = "笔试"
        elif re.search(r"面试.{0,20}(?:邀请|安排)|邀请.{0,20}面试", text):
            facts["一面"] = "待参加"
            facts["当前阶段"] = "一面"
        elif re.search(r"(?:笔试|考试)成绩.{0,12}(?:查询|公布|发布|开放|可查|已开通)", text):
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


def classify_mail(value: str) -> str:
    if re.search(
        r"AI\s*面试.{0,20}(?:邀请|安排)|邀请.{0,20}AI\s*面试",
        value,
        re.IGNORECASE,
    ):
        return "ai_interview"
    if re.search(r"(?:线上|在线)?测评.{0,20}(?:邀请|安排)|邀请.{0,20}(?:线上|在线)?测评", value):
        return "assessment"
    if re.search(r"(?:笔试|考试).{0,20}(?:邀请|安排)|邀请.{0,20}(?:笔试|考试)", value):
        return "written_test"
    if re.search(r"面试.{0,20}(?:邀请|安排)|邀请.{0,20}面试", value):
        return "interview"
    if re.search(
        r"投递成功|提交成功|感谢.{0,8}(?:投递|应聘)|"
        r"(?:已经|已|我们已经)?收到.{0,4}(?:您的)?(?:简历|申请)",
        value,
    ):
        return "application_received"
    return "status"


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
        resume_payload: dict[str, object] | None = None,
    ) -> dict[str, int]:
        job = self.jobs.create("mail_sync", idempotency_key)
        if resume_payload:
            self.jobs.progress(job.job_id, "configured", resume_payload)
        try:
            return self._sync(adapter, account_id, tracker_path, job, idempotency_key)
        except Exception as exc:
            self.jobs.fail(
                job.job_id,
                "mail.sync_failed",
                "Mailbox synchronization failed after bounded retries.",
            )
            raise MailSyncError(job.job_id) from exc

    def _sync(
        self,
        adapter: MailAdapter,
        account_id: str,
        tracker_path: Path,
        job: PersistentJob,
        idempotency_key: str,
    ) -> dict[str, int]:
        baseline_hash = self.excel.fingerprint(tracker_path)
        tracker_key = str(tracker_path.resolve())
        pending = [
            previous
            for previous in self.jobs.list()
            if previous.job_type in {"mail_sync", "tracker_write"}
            and (previous.checkpoint or {}).get("tracker_key") == tracker_key
            and (previous.checkpoint or {}).get("export_pending")
        ]
        if pending:
            if any(previous.checkpoint["baseline_hash"] != baseline_hash for previous in pending):
                raise ValueError("Excel changed after interrupted sync; reconcile before retrying")
        elif tracker_path.exists():
            self.excel.import_workbook(tracker_path, f"{idempotency_key}:tracker-import")
        self.jobs.progress(
            job.job_id,
            "baseline_ready",
            {
                "tracker_key": tracker_key,
                "baseline_hash": baseline_hash,
                "export_pending": True,
            },
        )
        stats = {
            "processed": 0,
            "new_emails": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "unlinked": 0,
            "conflicts": 0,
        }
        created_ids: set[UUID] = set()
        updated_ids: set[UUID] = set()
        fetched = adapter.fetch()
        items = (
            sorted(
                fetched,
                key=lambda item: (
                    self._naive_utc(item.sent_at)
                    if item.sent_at
                    else datetime.min.replace(tzinfo=UTC).replace(tzinfo=None)
                ),
            )
            if isinstance(fetched, list)
            else fetched
        )
        for item in items:
            if not is_job_candidate(item):
                continue
            exists, _ = self.emails.find(account_id, item.raw_hash, item.message_id)
            if exists and not self.emails.can_reprocess(account_id, item.raw_hash, item.message_id):
                continue  # Deleted and manually corrected records must not be replayed.
            text = f"{item.subject}\n{item.text}"
            facts = extract_facts(text, item.sender)
            mail_kind = classify_mail(text)
            company, role = facts.get("公司名称"), facts.get("岗位")
            application = None
            same_company = [
                a
                for a in self.applications.list()
                if company and normalize_identity(a.company) == normalize_identity(str(company))
            ]
            if company and role:
                matches = [
                    a
                    for a in same_company
                    if normalize_identity(a.role) == normalize_identity(str(role))
                ]
                if len(matches) == 1:
                    application = matches[0]
                elif not matches:
                    application = self.applications.create(
                        str(company),
                        str(role),
                        idempotency_key=f"mail-app:{account_id}:{item.raw_hash}",
                    )
                    created_ids.add(application.application_id)
            elif company and mail_kind == "application_received":
                application = self.applications.create(
                    str(company),
                    "岗位待确认",
                    idempotency_key=f"mail-receipt:{account_id}:{item.raw_hash}",
                )
                created_ids.add(application.application_id)
            elif len(same_company) == 1:
                application = same_company[0]
            application_id = application.application_id if application else None
            if application:
                before = application.version
                updates = {k: v for k, v in facts.items() if k not in {"公司名称", "岗位"}}
                if item.sent_at and mail_kind == "application_received":
                    updates.setdefault("投递时间", item.sent_at.date())
                prior = [e for e in self.emails.linked() if e.application_id == application_id]
                for field, value in updates.items():
                    latest = max(
                        (
                            self._naive_utc(e.sent_at)
                            for e in prior
                            if field in e.facts
                            or (field == "投递时间" and e.facts.get("当前阶段") == "已投递")
                        ),
                        default=None,
                    )
                    sent = self._naive_utc(item.sent_at) if item.sent_at else None
                    if latest and (sent is None or sent <= latest):
                        continue
                    current = self.applications.get(application_id)
                    if str(current.values.get(field)) == str(value):
                        continue
                    user_changed = self.applications.latest_user_change(application_id, field)
                    manual = user_changed is not None or (
                        not prior and current.values.get(field) not in (None, "")
                    )
                    conflict = manual and (
                        sent is None
                        or user_changed is None
                        or sent <= self._naive_utc(user_changed)
                    )
                    source = "mail_conflict" if conflict else "mail_authoritative"
                    self.applications.apply_field_change(
                        application_id,
                        field,
                        value,
                        source=source,
                        idempotency_key=f"mail:{application_id}:{item.raw_hash}:{field}",
                        evidence=f"{field}: {value}"[:500],
                    )
                    stats["conflicts"] += int(conflict)
                after = self.applications.get(application_id)
                if after.version != before and item.sent_at:
                    latest_update = after.values.get("最近更新时间")
                    if not isinstance(latest_update, datetime) or self._naive_utc(
                        item.sent_at
                    ) > self._naive_utc(latest_update):
                        self.applications.apply_field_change(
                            application_id,
                            "最近更新时间",
                            self._naive_utc(item.sent_at),
                            source="mail_authoritative",
                            idempotency_key=f"mail:{item.raw_hash}:updated",
                            evidence="Mail event time",
                        )
                if after.version != before and application_id not in created_ids:
                    updated_ids.add(application_id)
                elif application_id not in created_ids:
                    stats["unchanged"] += 1
            else:
                stats["unlinked"] += 1
            if exists:
                if application_id:
                    self.emails.link(item.raw_hash, application_id, facts, mail_kind)
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
                    mail_kind=mail_kind,
                )
                stats["new_emails"] += 1
            stats["processed"] += int(not exists or application_id is not None)
            self.jobs.progress(
                job.job_id, "message_committed", {"last_message_id": item.message_id, **stats}
            )
        stats["created"], stats["updated"] = len(created_ids), len(updated_ids)
        if self.excel.fingerprint(tracker_path) != baseline_hash:
            raise ValueError("Excel changed during mail sync; no overwrite performed")
        self.excel.export_workbook(tracker_path)
        for previous in pending:
            self.jobs.complete(
                previous.job_id, {"export_pending": False, "recovered_by": str(job.job_id)}
            )
        self.jobs.complete(job.job_id, {**stats, "export_pending": False})
        return stats

    @staticmethod
    def _naive_utc(value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
