from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_VERSION = "1.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationStage(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"
    ARCHIVED = "archived"


class ErrorResponse(StrictModel):
    code: str
    message: str
    request_id: UUID
    location: str | None = None


class Evidence(StrictModel):
    source_type: str
    source_id: str
    excerpt: str = Field(max_length=500)


class ApplicationSnapshot(StrictModel):
    application_id: UUID = Field(default_factory=uuid4)
    company: str = Field(max_length=200)
    role: str = Field(max_length=200)
    stage: ApplicationStage = ApplicationStage.DRAFT
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timezone is required")
        return value


class Checkpoint(StrictModel):
    step: str
    payload: dict[str, Any] = Field(default_factory=dict)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(StrictModel):
    job_id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: JobStatus = JobStatus.PENDING
    current_step: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    checkpoint: Checkpoint | None = None
    idempotency_key: str
    error_code: str | None = None
    error_message_safe: str | None = None
    retryable: bool = False
    recovery_action: str | None = None
    retry_count: int = 0
    processor_version: str = "1.0"

