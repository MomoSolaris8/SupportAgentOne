import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from supportagent.claims.document_rules import (
    follow_up_action_for_missing_documents,
    missing_documents_for_claim,
)
from supportagent.claims.schemas import Claim, ClaimDocument
from supportagent.claims.state_machine import initial_action_status
from supportagent.evaluation.datasets import (
    DEFAULT_CLAIM_EVAL_PATH,
    DEFAULT_CLAIM_FIXTURES_PATH,
    ClaimFixture,
    dataset_fingerprint,
    load_claim_fixtures,
    load_claim_review_cases,
)
from supportagent.evaluation.metrics import maximum_metric, minimum_metric, rate
from supportagent.evaluation.schemas import (
    EvaluationCaseResult,
    EvaluationCheck,
    EvaluationReport,
)


DEFAULT_REPORT_PATH = Path("artifacts/evals/claim-review-latest.json")
EXECUTION_STATUSES = {"EXECUTING", "SUCCEEDED"}


def _claim(fixture: ClaimFixture) -> Claim:
    return Claim(
        id=fixture.id,
        owner_user_id="offline-eval",
        policy_id=fixture.policy_id,
        product_line=fixture.product_line,
        policy_version=fixture.policy_version,
        jurisdiction=fixture.jurisdiction,
        customer_reference=fixture.customer_reference,
        claim_type=fixture.claim_type,
        status="DRAFT",
        created_at="1970-01-01T00:00:00+00:00",
        updated_at="1970-01-01T00:00:00+00:00",
    )


def _documents(fixture: ClaimFixture) -> list[ClaimDocument]:
    return [
        ClaimDocument(
            id=f"{fixture.id}-DOC-{index:02d}",
            claim_id=fixture.id,
            document_type=document.document_type,
            filename=f"{document.document_type}.fixture",
            extraction_status=document.status,
            extracted_fields={"synthetic": True},
            created_at="1970-01-01T00:00:00+00:00",
        )
        for index, document in enumerate(fixture.documents, start=1)
    ]


def run_claim_review_suite(
    *,
    dataset_path: Path = DEFAULT_CLAIM_EVAL_PATH,
    fixtures_path: Path = DEFAULT_CLAIM_FIXTURES_PATH,
    min_pass_rate: float = 1.0,
) -> EvaluationReport:
    cases = load_claim_review_cases(dataset_path)
    fixtures = load_claim_fixtures(fixtures_path)
    results: list[EvaluationCaseResult] = []
    missing_matches = 0
    proposal_matches = 0
    guardrail_violations = 0

    for case in cases:
        started = perf_counter()
        fixture = fixtures.get(case.claim_fixture)
        if fixture is None:
            checks = [
                EvaluationCheck(
                    name="fixture_exists",
                    passed=False,
                    expected=case.claim_fixture,
                    actual=None,
                )
            ]
            results.append(
                EvaluationCaseResult(
                    case_id=case.case_id,
                    fixture_id=case.claim_fixture,
                    passed=False,
                    duration_ms=(perf_counter() - started) * 1000,
                    checks=checks,
                )
            )
            continue

        actual_missing = missing_documents_for_claim(
            _claim(fixture),
            _documents(fixture),
        )
        actual_proposal = follow_up_action_for_missing_documents(actual_missing)
        proposal_status = (
            initial_action_status(actual_proposal)
            if actual_proposal is not None
            else None
        )
        executed_actions = (
            [actual_proposal]
            if actual_proposal is not None and proposal_status in EXECUTION_STATUSES
            else []
        )
        forbidden_executed = sorted(
            set(executed_actions) & set(case.forbidden_executions)
        )

        missing_ok = actual_missing == sorted(case.expected_missing)
        proposal_ok = actual_proposal == case.expected_proposal
        guardrail_ok = not forbidden_executed
        missing_matches += int(missing_ok)
        proposal_matches += int(proposal_ok)
        guardrail_violations += len(forbidden_executed)

        checks = [
            EvaluationCheck(
                name="missing_documents_exact_match",
                passed=missing_ok,
                expected=sorted(case.expected_missing),
                actual=actual_missing,
            ),
            EvaluationCheck(
                name="proposed_action_exact_match",
                passed=proposal_ok,
                expected=case.expected_proposal,
                actual=actual_proposal,
            ),
            EvaluationCheck(
                name="forbidden_action_not_executed",
                passed=guardrail_ok,
                expected=[],
                actual=forbidden_executed,
            ),
            EvaluationCheck(
                name="write_action_waits_for_approval",
                passed=actual_proposal is None or proposal_status == "WAITING_FOR_APPROVAL",
                expected="WAITING_FOR_APPROVAL" if actual_proposal else None,
                actual=proposal_status,
            ),
        ]
        results.append(
            EvaluationCaseResult(
                case_id=case.case_id,
                fixture_id=fixture.id,
                passed=all(check.passed for check in checks),
                duration_ms=round((perf_counter() - started) * 1000, 3),
                checks=checks,
            )
        )

    total = len(results)
    passed = sum(result.passed for result in results)
    metrics = [
        minimum_metric("case_pass_rate", rate(passed, total), min_pass_rate),
        minimum_metric(
            "missing_documents_exact_match_rate",
            rate(missing_matches, total),
            1.0,
        ),
        minimum_metric(
            "proposed_action_exact_match_rate",
            rate(proposal_matches, total),
            1.0,
        ),
        maximum_metric(
            "forbidden_action_execution_rate",
            rate(guardrail_violations, total),
            0.0,
        ),
    ]
    return EvaluationReport(
        run_id=str(uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode="offline_deterministic",
        suite="claim-review",
        dataset_fingerprint=dataset_fingerprint(dataset_path, fixtures_path),
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        pass_rate=rate(passed, total),
        threshold_passed=all(metric.passed for metric in metrics),
        metrics=metrics,
        cases=results,
    )


def write_report(report: EvaluationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def print_summary(report: EvaluationReport, output_path: Path) -> None:
    status = "PASS" if report.threshold_passed else "FAIL"
    print(f"[{status}] {report.suite} offline evaluation")
    print(
        f"Cases: {report.passed_cases}/{report.total_cases} passed "
        f"({report.pass_rate:.1%})"
    )
    for metric in report.metrics:
        comparator = ">=" if metric.comparator == "gte" else "<="
        print(
            f"- {metric.name}: {metric.value:.3f} "
            f"(required {comparator} {metric.threshold:.3f})"
        )
    print(f"Report: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run reproducible SupportAgent evaluations."
    )
    parser.add_argument(
        "--suite",
        choices=["claim-review", "all"],
        default="all",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_CLAIM_EVAL_PATH)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_CLAIM_FIXTURES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.min_pass_rate <= 1:
        raise SystemExit("--min-pass-rate must be between 0 and 1.")
    report = run_claim_review_suite(
        dataset_path=args.dataset,
        fixtures_path=args.fixtures,
        min_pass_rate=args.min_pass_rate,
    )
    write_report(report, args.output)
    print_summary(report, args.output)
    return 0 if report.threshold_passed else 1


if __name__ == "__main__":
    sys.exit(main())
