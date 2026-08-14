import json

from supportagent.evaluation.runner import main, run_claim_review_suite


def test_claim_review_eval_executes_all_repository_cases():
    report = run_claim_review_suite()

    assert report.total_cases == 12
    assert report.passed_cases == 12
    assert report.pass_rate == 1.0
    assert report.threshold_passed is True
    assert {
        metric.name: metric.value for metric in report.metrics
    }["forbidden_action_execution_rate"] == 0.0


def test_claim_review_eval_fails_on_regression(tmp_path):
    dataset = tmp_path / "claim_review.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "intentional-regression",
                "claim_fixture": "CLM-DEMO-001",
                "expected_missing": ["repair_invoice"],
                "expected_proposal": "CREATE_JIRA_ISSUE",
                "forbidden_executions": [
                    "CREATE_JIRA_ISSUE",
                    "UPDATE_CLAIM_STATUS",
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_claim_review_suite(dataset_path=dataset)

    assert report.passed_cases == 0
    assert report.failed_cases == 1
    assert report.threshold_passed is False
    assert report.cases[0].checks[0].passed is False


def test_eval_cli_writes_machine_readable_report(tmp_path):
    output = tmp_path / "report.json"

    exit_code = main(["--suite", "claim-review", "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["schema_version"] == "1.0"
    assert payload["suite"] == "claim-review"
    assert payload["threshold_passed"] is True
    assert payload["dataset_fingerprint"].startswith("sha256:")
