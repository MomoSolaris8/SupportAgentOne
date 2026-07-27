from pydantic import BaseModel, Field

from supportagent.evaluation.schemas import EvaluationCheck


class OnlineRAGTrialResult(BaseModel):
    case_id: str
    category: str
    trial: int
    passed: bool
    latency_ms: float = Field(ge=0)
    llm_latency_ms: float = Field(ge=0)
    llm_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    evidence_status: str | None = None
    actual_sources: list[str] = Field(default_factory=list)
    answer: str | None = None
    error: str | None = None
    checks: list[EvaluationCheck] = Field(default_factory=list)


class OnlineModelBenchmark(BaseModel):
    model_id: str
    provider: str
    provider_model: str
    total_trials: int
    successful_trials: int
    passed_trials: int
    pass_rate: float
    source_recall: float
    refusal_accuracy: float | None = None
    citation_validity_rate: float | None = None
    stability_rate: float
    error_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    llm_calls: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    estimated_cost: float | None = None
    threshold_passed: bool
    trials: list[OnlineRAGTrialResult]


class OnlineRAGBenchmarkReport(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    generated_at: str
    mode: str = "online_rag"
    suite: str = "rag-qa"
    dataset_fingerprint: str
    trials_per_case: int
    minimum_pass_rate: float
    pricing_currency: str | None = None
    pricing_effective_date: str | None = None
    threshold_passed: bool
    models: list[OnlineModelBenchmark]
