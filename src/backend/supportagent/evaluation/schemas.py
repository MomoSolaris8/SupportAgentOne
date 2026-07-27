from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluationCheck(BaseModel):
    name: str
    passed: bool
    expected: Any
    actual: Any


class EvaluationCaseResult(BaseModel):
    case_id: str
    fixture_id: str
    passed: bool
    duration_ms: float = Field(ge=0)
    checks: list[EvaluationCheck]


class EvaluationMetric(BaseModel):
    name: str
    value: float
    threshold: float
    comparator: Literal["gte", "lte"]
    passed: bool


class EvaluationReport(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    generated_at: str
    mode: Literal["offline_deterministic"]
    suite: str
    dataset_fingerprint: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    threshold_passed: bool
    metrics: list[EvaluationMetric]
    cases: list[EvaluationCaseResult]
