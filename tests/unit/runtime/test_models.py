import pytest
from pydantic import ValidationError

from supportagent.runtime.models import (
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
    RunType,
)


def test_new_run_starts_queued() -> None:
    run = Run(
        id="run-001",
        run_type=RunType.INSURANCE_QA,
        owner_user_id="user-001",
        input_data={"question": "What is covered?"},
    )

    assert run.status is RunStatus.QUEUED
    assert run.current_step is None
    assert run.output_data is None
    assert run.error is None
    assert run.started_at is None
    assert run.completed_at is None


def test_run_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError, match="status"):
        Run(
            id="run-002",
            run_type=RunType.INSURANCE_QA,
            owner_user_id="user-001",
            status="UNKNOWN",
        )


def test_run_event_uses_ordered_protocol_value() -> None:
    event = RunEvent(
        id="event-001",
        run_id="run-001",
        sequence=1,
        event_type=RunEventType.STEP_STARTED,
        step="retrieve",
        payload={"source": "confluence"},
    )

    serialized = event.model_dump(mode="json")

    assert event.sequence == 1
    assert serialized["event_type"] == "step.started"
    assert serialized["payload"] == {"source": "confluence"}


def test_run_event_rejects_non_positive_sequence() -> None:
    with pytest.raises(ValidationError, match="sequence"):
        RunEvent(
            id="event-002",
            run_id="run-001",
            sequence=0,
            event_type=RunEventType.RUN_STARTED,
        )
