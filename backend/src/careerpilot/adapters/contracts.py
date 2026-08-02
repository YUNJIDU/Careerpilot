from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Protocol, runtime_checkable

MAIL_ADAPTER_CONTRACT_VERSION: Literal["1"] = "1"


@dataclass(frozen=True, slots=True)
class MailAttachmentMetadata:
    source_id: str
    filename: str
    content_type: str
    size: int | None = None


@dataclass
class MailItem:
    message_id: str | None
    sender: str
    subject: str
    sent_at: datetime | None
    text: str
    raw_hash: str
    source_id: str | None = None
    attachments: tuple[MailAttachmentMetadata, ...] = ()


@runtime_checkable
class MailAdapter(Protocol):
    contract_version: ClassVar[Literal["1"]]

    def test_connection(self) -> None: ...

    def fetch(self) -> Iterable[MailItem]: ...

    def fetch_attachment(self, source_id: str) -> bytes: ...
