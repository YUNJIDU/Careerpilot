from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Callable
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from careerpilot.adapters.contracts import MAIL_ADAPTER_CONTRACT_VERSION, MailItem
from careerpilot.mail import MAX_MESSAGE_BYTES, _attachment_content, parse_message

MAX_PROVIDER_RESPONSE_BYTES = 4 * MAX_MESSAGE_BYTES // 3 + 1024
HttpGet = Callable[[str, str, str], bytes]
TokenGetter = Callable[[], str]


def authorized_get(url: str, token: str, accept: str = "application/json") -> bytes:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "User-Agent": "CareerPilot/0.1",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read(MAX_PROVIDER_RESPONSE_BYTES)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise PermissionError("mail provider authentication failed") from exc
        raise ConnectionError("mail provider request failed") from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise ConnectionError("mail provider request failed") from exc
    if len(body) >= MAX_PROVIDER_RESPONSE_BYTES:
        raise ValueError("mail provider response exceeds the safe limit")
    return body


class GmailApiAdapter:
    contract_version = MAIL_ADAPTER_CONTRACT_VERSION
    base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(
        self,
        token: TokenGetter,
        *,
        since: date,
        limit: int = 100,
        http_get: HttpGet = authorized_get,
    ) -> None:
        self.token = token
        self.since = since
        self.limit = min(max(limit, 1), 500)
        self.http_get = http_get

    def test_connection(self) -> None:
        self._json(f"{self.base_url}/profile")

    def fetch(self) -> list[MailItem]:
        query = urlencode(
            {
                "q": f"after:{self.since:%Y/%m/%d}",
                "maxResults": self.limit,
            }
        )
        payload = self._json(f"{self.base_url}/messages?{query}")
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            raise ConnectionError("Gmail returned an invalid message list")
        items: list[MailItem] = []
        for value in messages[: self.limit]:
            message_id = value.get("id") if isinstance(value, dict) else None
            if not isinstance(message_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", message_id):
                continue
            try:
                raw = self._raw(message_id)
                digest = hashlib.sha256(raw).hexdigest()
                items.append(parse_message(raw, source_id=f"gmail:{message_id}:{digest}"))
            except PermissionError:
                raise
            except (ConnectionError, ValueError):
                continue
        return items

    def fetch_attachment(self, source_id: str) -> bytes:
        match = re.fullmatch(r"gmail:([A-Za-z0-9_-]+):([0-9a-f]{64}):(\d+)", source_id)
        if not match:
            raise ValueError("attachment source is invalid")
        raw = self._raw(match.group(1))
        if hashlib.sha256(raw).hexdigest() != match.group(2):
            raise ValueError("email changed before attachment approval")
        return _attachment_content(raw, int(match.group(3)))

    def _raw(self, message_id: str) -> bytes:
        payload = self._json(f"{self.base_url}/messages/{message_id}?format=raw")
        encoded = payload.get("raw")
        if not isinstance(encoded, str):
            raise ConnectionError("Gmail message content is unavailable")
        try:
            return base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            )
        except (ValueError, TypeError) as exc:
            raise ValueError("Gmail message content is invalid") from exc

    def _json(self, url: str) -> dict[str, object]:
        try:
            payload = json.loads(self.http_get(url, self.token(), "application/json"))
        except json.JSONDecodeError as exc:
            raise ConnectionError("Gmail returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ConnectionError("Gmail returned invalid JSON")
        return payload


class OutlookGraphAdapter:
    contract_version = MAIL_ADAPTER_CONTRACT_VERSION
    base_url = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        token: TokenGetter,
        *,
        since: date,
        limit: int = 100,
        http_get: HttpGet = authorized_get,
    ) -> None:
        self.token = token
        self.since = since
        self.limit = min(max(limit, 1), 500)
        self.http_get = http_get

    def test_connection(self) -> None:
        self._json(f"{self.base_url}/me?$select=id")

    def fetch(self) -> list[MailItem]:
        query = urlencode(
            {
                "$select": "id",
                "$filter": f"receivedDateTime ge {self.since.isoformat()}T00:00:00Z",
                "$orderby": "receivedDateTime desc",
                "$top": self.limit,
            }
        )
        payload = self._json(f"{self.base_url}/me/messages?{query}")
        messages = payload.get("value", [])
        if not isinstance(messages, list):
            raise ConnectionError("Microsoft Graph returned an invalid message list")
        items: list[MailItem] = []
        for value in messages[: self.limit]:
            message_id = value.get("id") if isinstance(value, dict) else None
            if not isinstance(message_id, str) or len(message_id) > 500:
                continue
            try:
                raw = self._raw(message_id)
                digest = hashlib.sha256(raw).hexdigest()
                encoded_id = base64.urlsafe_b64encode(message_id.encode()).decode().rstrip("=")
                if len(encoded_id) > 210:
                    continue
                items.append(parse_message(raw, source_id=f"outlook:{encoded_id}:{digest}"))
            except PermissionError:
                raise
            except (ConnectionError, UnicodeError, ValueError):
                continue
        return items

    def fetch_attachment(self, source_id: str) -> bytes:
        match = re.fullmatch(r"outlook:([A-Za-z0-9_-]+):([0-9a-f]{64}):(\d+)", source_id)
        if not match:
            raise ValueError("attachment source is invalid")
        try:
            encoded = match.group(1)
            message_id = base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            ).decode()
        except (UnicodeError, ValueError) as exc:
            raise ValueError("attachment source is invalid") from exc
        raw = self._raw(message_id)
        if hashlib.sha256(raw).hexdigest() != match.group(2):
            raise ValueError("email changed before attachment approval")
        return _attachment_content(raw, int(match.group(3)))

    def _raw(self, message_id: str) -> bytes:
        return self.http_get(
            f"{self.base_url}/me/messages/{quote(message_id, safe='')}/$value",
            self.token(),
            "message/rfc822",
        )

    def _json(self, url: str) -> dict[str, object]:
        try:
            payload = json.loads(self.http_get(url, self.token(), "application/json"))
        except json.JSONDecodeError as exc:
            raise ConnectionError("Microsoft Graph returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ConnectionError("Microsoft Graph returned invalid JSON")
        return payload
