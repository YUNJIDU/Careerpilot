from typing import Any, Protocol


class MailAdapter(Protocol):
    def fetch(self, checkpoint: str | None = None) -> list[dict[str, Any]]: ...


class ModelGateway(Protocol):
    def generate(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class SummaryProvider(Protocol):
    def summarize(self, application_id: str) -> str: ...


class AttachmentParser(Protocol):
    def parse(self, path: str) -> str: ...


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...


class DeferredService:
    def run(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("Deferred until a later release")


BackupService = RestoreService = DeleteService = DeferredService

