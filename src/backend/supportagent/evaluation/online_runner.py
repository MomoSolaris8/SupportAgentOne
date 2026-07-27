import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from dotenv import load_dotenv

from supportagent.agent.workflow import answer_with_agent
from supportagent.core.answer import answer_reports_insufficient_evidence
from supportagent.core.language import detect_response_language
from supportagent.evaluation.datasets import (
    DEFAULT_RAG_EVAL_PATH,
    RAGEvalCase,
    dataset_fingerprint,
    load_rag_eval_cases,
)
from supportagent.evaluation.online_schemas import (
    OnlineModelBenchmark,
    OnlineRAGBenchmarkReport,
    OnlineRAGTrialResult,
)
from supportagent.evaluation.pricing import PricingCatalog, load_pricing_catalog
from supportagent.evaluation.schemas import EvaluationCheck
from supportagent.llm import capture_llm_usage, resolve_model


DEFAULT_ONLINE_REPORT_PATH = Path("artifacts/evals/online-rag-latest.json")
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * 0.95 + 0.5)))
    return ordered[index]


def _evaluate_trial(
    case: RAGEvalCase,
    result: Any,
) -> tuple[list[EvaluationCheck], list[str]]:
    actual_sources = [chunk["metadata"]["title"] for chunk in result.chunks]
    expected_sources = set(case.expected_sources)
    source_hits = expected_sources & set(actual_sources)
    sources_ok = not expected_sources or source_hits == expected_sources

    refused = (
        result.evidence.status == "insufficient"
        and answer_reports_insufficient_evidence(result.answer)
    )
    refusal_ok = refused if case.expect_refusal else not refused

    citations = [int(value) for value in CITATION_PATTERN.findall(result.answer)]
    citations_ok = case.expect_refusal or (
        bool(citations)
        and bool(result.chunks)
        and all(1 <= citation <= len(result.chunks) for citation in citations)
    )
    language_ok = detect_response_language(result.answer) == detect_response_language(
        case.question
    )
    checks = [
        EvaluationCheck(
            name="expected_sources_retrieved",
            passed=sources_ok,
            expected=sorted(expected_sources),
            actual=actual_sources,
        ),
        EvaluationCheck(
            name="refusal_behavior",
            passed=refusal_ok,
            expected=case.expect_refusal,
            actual=refused,
        ),
        EvaluationCheck(
            name="citations_are_present_and_valid",
            passed=citations_ok,
            expected="valid numbered citations" if not case.expect_refusal else "not required",
            actual=citations,
        ),
        EvaluationCheck(
            name="response_language_matches_request",
            passed=language_ok,
            expected=detect_response_language(case.question),
            actual=detect_response_language(result.answer),
        ),
    ]
    return checks, actual_sources


def _run_trial(
    case: RAGEvalCase,
    model_id: str,
    trial: int,
    pricing: PricingCatalog | None,
    answer_fn: Callable[..., Any],
) -> OnlineRAGTrialResult:
    started = perf_counter()
    calls = []
    try:
        with capture_llm_usage() as calls:
            result = answer_fn(
                case.question,
                requested_model=model_id,
                enabled_mcp_servers=[],
                enabled_skills=[],
            )
        checks, actual_sources = _evaluate_trial(case, result)
        usage = [call.usage for call in calls]
        return OnlineRAGTrialResult(
            case_id=case.case_id,
            category=case.category,
            trial=trial,
            passed=all(check.passed for check in checks),
            latency_ms=round((perf_counter() - started) * 1000, 3),
            llm_latency_ms=round(sum(call.latency_ms for call in calls), 3),
            llm_calls=len(calls),
            input_tokens=sum(item.input_tokens for item in usage),
            output_tokens=sum(item.output_tokens for item in usage),
            cached_input_tokens=sum(item.cached_input_tokens for item in usage),
            reasoning_tokens=sum(item.reasoning_tokens for item in usage),
            estimated_cost=pricing.estimate(calls) if pricing else None,
            evidence_status=result.evidence.status,
            actual_sources=actual_sources,
            answer=result.answer,
            checks=checks,
        )
    except Exception as error:
        error_message = " ".join(str(error).split())
        return OnlineRAGTrialResult(
            case_id=case.case_id,
            category=case.category,
            trial=trial,
            passed=False,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            llm_latency_ms=round(sum(call.latency_ms for call in calls), 3),
            llm_calls=len(calls),
            input_tokens=sum(call.usage.input_tokens for call in calls),
            output_tokens=sum(call.usage.output_tokens for call in calls),
            cached_input_tokens=sum(
                call.usage.cached_input_tokens for call in calls
            ),
            reasoning_tokens=sum(call.usage.reasoning_tokens for call in calls),
            estimated_cost=pricing.estimate(calls) if pricing else None,
            error=f"{type(error).__name__}: {error_message}"[:500],
        )


def _aggregate_model(
    model_id: str,
    provider: str,
    provider_model: str,
    cases: list[RAGEvalCase],
    trials: list[OnlineRAGTrialResult],
    min_pass_rate: float,
) -> OnlineModelBenchmark:
    successful = [trial for trial in trials if trial.error is None]
    expected_source_count = 0
    source_hit_count = 0
    refusal_checks = []
    citation_checks = []
    by_case: dict[str, list[OnlineRAGTrialResult]] = defaultdict(list)
    for trial in trials:
        by_case[trial.case_id].append(trial)
        case = next(item for item in cases if item.case_id == trial.case_id)
        source_check = next(
            (check for check in trial.checks if check.name == "expected_sources_retrieved"),
            None,
        )
        if source_check is not None:
            expected = set(case.expected_sources)
            actual = set(trial.actual_sources)
            expected_source_count += len(expected)
            source_hit_count += len(expected & actual)
        refusal_check = next(
            (check for check in trial.checks if check.name == "refusal_behavior"),
            None,
        )
        if case.expect_refusal and refusal_check is not None:
            refusal_checks.append(refusal_check.passed)
        citation_check = next(
            (
                check
                for check in trial.checks
                if check.name == "citations_are_present_and_valid"
            ),
            None,
        )
        if not case.expect_refusal and citation_check is not None:
            citation_checks.append(citation_check.passed)

    total = len(trials)
    pass_rate = sum(trial.passed for trial in trials) / total if total else 0.0
    latencies = [trial.latency_ms for trial in successful]
    costs = [trial.estimated_cost for trial in trials]
    complete_cost = (
        sum(cost for cost in costs if cost is not None)
        if costs and all(cost is not None for cost in costs)
        else None
    )
    stability_rate = (
        sum(all(trial.passed for trial in case_trials) for case_trials in by_case.values())
        / len(by_case)
        if by_case
        else 0.0
    )
    return OnlineModelBenchmark(
        model_id=model_id,
        provider=provider,
        provider_model=provider_model,
        total_trials=total,
        successful_trials=len(successful),
        passed_trials=sum(trial.passed for trial in trials),
        pass_rate=pass_rate,
        source_recall=(
            source_hit_count / expected_source_count
            if expected_source_count
            else 1.0
        ),
        refusal_accuracy=(
            sum(refusal_checks) / len(refusal_checks) if refusal_checks else None
        ),
        citation_validity_rate=(
            sum(citation_checks) / len(citation_checks) if citation_checks else None
        ),
        stability_rate=stability_rate,
        error_rate=(total - len(successful)) / total if total else 0.0,
        latency_p50_ms=round(median(latencies), 3) if latencies else 0.0,
        latency_p95_ms=round(_percentile_95(latencies), 3),
        llm_calls=sum(trial.llm_calls for trial in trials),
        input_tokens=sum(trial.input_tokens for trial in trials),
        output_tokens=sum(trial.output_tokens for trial in trials),
        cached_input_tokens=sum(trial.cached_input_tokens for trial in trials),
        reasoning_tokens=sum(trial.reasoning_tokens for trial in trials),
        estimated_cost=round(complete_cost, 8) if complete_cost is not None else None,
        threshold_passed=pass_rate >= min_pass_rate,
        trials=trials,
    )


def run_online_rag_benchmark(
    *,
    models: list[str],
    dataset_path: Path = DEFAULT_RAG_EVAL_PATH,
    trials_per_case: int = 1,
    case_ids: set[str] | None = None,
    min_pass_rate: float = 0.75,
    pricing_path: Path | None = None,
    answer_fn: Callable[..., Any] = answer_with_agent,
) -> OnlineRAGBenchmarkReport:
    cases = [
        case
        for case in load_rag_eval_cases(dataset_path)
        if not case_ids or case.case_id in case_ids
    ]
    if not cases:
        raise ValueError("No RAG evaluation cases matched the requested filter.")
    pricing = load_pricing_catalog(pricing_path)
    model_results = []
    for model_id in models:
        profile = resolve_model(model_id, task="chat")
        if profile.id != model_id:
            raise ValueError(
                f"Requested benchmark model {model_id!r} resolved to "
                f"{profile.id!r}; configure and allowlist it first."
            )
        trial_results = [
            _run_trial(case, model_id, trial, pricing, answer_fn)
            for case in cases
            for trial in range(1, trials_per_case + 1)
        ]
        model_results.append(
            _aggregate_model(
                model_id,
                profile.provider,
                profile.provider_model,
                cases,
                trial_results,
                min_pass_rate,
            )
        )
    return OnlineRAGBenchmarkReport(
        run_id=str(uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        dataset_fingerprint=dataset_fingerprint(dataset_path),
        trials_per_case=trials_per_case,
        minimum_pass_rate=min_pass_rate,
        pricing_currency=pricing.currency if pricing else None,
        pricing_effective_date=pricing.effective_date if pricing else None,
        threshold_passed=all(model.threshold_passed for model in model_results),
        models=model_results,
    )


def write_online_report(
    report: OnlineRAGBenchmarkReport,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path = output_path.with_suffix(".md")
    markdown_path.write_text(render_online_markdown(report), encoding="utf-8")
    return markdown_path


def render_online_markdown(report: OnlineRAGBenchmarkReport) -> str:
    lines = [
        "# SupportAgent Online RAG Benchmark",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Generated: `{report.generated_at}`",
        f"- Dataset: `{report.dataset_fingerprint}`",
        f"- Trials per case: `{report.trials_per_case}`",
        f"- Minimum pass rate: `{report.minimum_pass_rate:.0%}`",
        f"- Overall gate: `{'PASS' if report.threshold_passed else 'FAIL'}`",
        "",
        "| Model | Pass | Source recall | Refusal | Citations | Stability | "
        "Error | p50 / p95 | Tokens in / out | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in report.models:
        refusal = (
            f"{model.refusal_accuracy:.0%}"
            if model.refusal_accuracy is not None
            else "n/a"
        )
        citations = (
            f"{model.citation_validity_rate:.0%}"
            if model.citation_validity_rate is not None
            else "n/a"
        )
        cost = (
            f"{report.pricing_currency} {model.estimated_cost:.6f}"
            if model.estimated_cost is not None and report.pricing_currency
            else "n/a"
        )
        lines.append(
            f"| {model.model_id} | {model.pass_rate:.0%} | "
            f"{model.source_recall:.0%} | {refusal} | {citations} | "
            f"{model.stability_rate:.0%} | {model.error_rate:.0%} | "
            f"{model.latency_p50_ms:.0f} / {model.latency_p95_ms:.0f} ms | "
            f"{model.input_tokens} / {model.output_tokens} | {cost} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            "- Every model receives the same versioned dataset through the same "
            "production RAG workflow.",
            "- MCP tools and skills are disabled so this suite measures retrieval "
            "and answer generation rather than tool routing.",
            "- Quality checks are deterministic: expected-source recall, refusal "
            "behavior, citation validity, and response language.",
            "- Latency covers the full RAG request. LLM latency and chat-token usage "
            "come from provider responses; embedding tokens are not included.",
            "- Cost is shown only when a dated pricing catalog covers every recorded "
            "model call.",
            "",
        ]
    )
    return "\n".join(lines)


def print_online_summary(
    report: OnlineRAGBenchmarkReport,
    output_path: Path,
    markdown_path: Path,
) -> None:
    print(
        "| model | pass | recall | refusal | citations | stable | p50/p95 | "
        "tokens in/out | cost |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for model in report.models:
        refusal = (
            f"{model.refusal_accuracy:.0%}"
            if model.refusal_accuracy is not None
            else "n/a"
        )
        citations = (
            f"{model.citation_validity_rate:.0%}"
            if model.citation_validity_rate is not None
            else "n/a"
        )
        cost = (
            f"{report.pricing_currency} {model.estimated_cost:.6f}"
            if model.estimated_cost is not None and report.pricing_currency
            else "n/a"
        )
        print(
            f"| {model.model_id} | {model.pass_rate:.0%} | "
            f"{model.source_recall:.0%} | {refusal} | {citations} | "
            f"{model.stability_rate:.0%} | "
            f"{model.latency_p50_ms:.0f}/{model.latency_p95_ms:.0f} ms | "
            f"{model.input_tokens}/{model.output_tokens} | {cost} |"
        )
    print(f"\nJSON report: {output_path}")
    print(f"Markdown report: {markdown_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare configured LLMs on the live SupportAgent RAG pipeline."
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated allowlisted model ids.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_RAG_EVAL_PATH)
    parser.add_argument("--cases", default="", help="Optional comma-separated case ids.")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--min-pass-rate", type=float, default=0.75)
    parser.add_argument("--pricing", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_ONLINE_REPORT_PATH)
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required acknowledgement that real provider APIs and billable tokens are used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm_live:
        raise SystemExit(
            "Online benchmark not started. Add --confirm-live to acknowledge "
            "real API calls and possible provider charges."
        )
    if args.trials < 1:
        raise SystemExit("--trials must be at least 1.")
    if not 0 <= args.min_pass_rate <= 1:
        raise SystemExit("--min-pass-rate must be between 0 and 1.")
    load_dotenv()
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if not models:
        raise SystemExit("--models must contain at least one model id.")
    case_ids = {item.strip() for item in args.cases.split(",") if item.strip()}
    report = run_online_rag_benchmark(
        models=models,
        dataset_path=args.dataset,
        trials_per_case=args.trials,
        case_ids=case_ids or None,
        min_pass_rate=args.min_pass_rate,
        pricing_path=args.pricing,
    )
    markdown_path = write_online_report(report, args.output)
    print_online_summary(report, args.output, markdown_path)
    return 0 if report.threshold_passed else 1


if __name__ == "__main__":
    sys.exit(main())
