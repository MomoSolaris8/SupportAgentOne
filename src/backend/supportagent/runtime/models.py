from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunType(str, Enum):
    """Identifies the program executed by a run."""

    INSURANCE_QA = "INSURANCE_QA"
    CLAIM_REVIEW = "CLAIM_REVIEW"
    MCP_ACTION = "MCP_ACTION"


class RunStatus(str, Enum):
    """Represents the lifecycle state of a run."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunEventType(str, Enum):
    """Identifies an event emitted during a run."""

    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    OUTPUT_DELTA = "output.delta"
    APPROVAL_REQUIRED = "approval.required"
    CHECKPOINT_SAVED = "checkpoint.saved"
    RUN_SUCCEEDED = "run.succeeded"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Run(BaseModel):
    """Represents one execution managed by the runtime."""

    id: str
    run_type: RunType
    owner_user_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    status: RunStatus = RunStatus.QUEUED
    current_step: str | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunEvent(BaseModel):
    """Represents one ordered event emitted during a run."""

    id: str
    run_id: str
    sequence: int = Field(ge=1)
    event_type: RunEventType
    step: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
