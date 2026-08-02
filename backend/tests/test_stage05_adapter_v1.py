from datetime import date
from pathlib import Path

import pytest

from careerpilot import extensions
from careerpilot.adapters.contracts import (
    MAIL_ADAPTER_CONTRACT_VERSION,
    MailAdapter,
    MailItem,
)
from careerpilot.api import BUILTIN_MAIL_ADAPTERS
from careerpilot.mail import FixtureMailAdapter, Imap163Adapter


def test_mail_item_keeps_existing_positional_api_and_future_defaults() -> None:
    item = MailItem(None, "jobs@example.com", "Role", None, "Body", "a" * 64)

    assert item.source_id is None
    assert item.attachments == ()


def test_fixture_adapter_implements_v1_contract(tmp_path: Path) -> None:
    adapter = FixtureMailAdapter(tmp_path)

    adapter.test_connection()
    assert isinstance(adapter, MailAdapter)
    assert adapter.contract_version == MAIL_ADAPTER_CONTRACT_VERSION
    assert adapter.fetch() == []
    with pytest.raises(ValueError, match="source is invalid"):
        adapter.fetch_attachment("attachment-1")


def test_imap163_adapter_implements_v1_contract_without_connecting() -> None:
    adapter = Imap163Adapter(
        "candidate@example.com",
        "not-used",
        since=date(2026, 1, 1),
    )

    assert isinstance(adapter, MailAdapter)
    assert adapter.contract_version == MAIL_ADAPTER_CONTRACT_VERSION
    with pytest.raises(ValueError, match="source is invalid"):
        adapter.fetch_attachment("attachment-1")


def test_runtime_registry_exposes_only_builtin_mail_adapters() -> None:
    assert BUILTIN_MAIL_ADAPTERS == {"imap163": Imap163Adapter}
    assert not hasattr(extensions, "MailAdapter")
