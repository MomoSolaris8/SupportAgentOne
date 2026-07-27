import json
from types import SimpleNamespace

import pytest

from supportagent.evaluation import online_runner
from supportagent.evaluation.pricing import ModelPrice, PricingCatalog
from supportagent.llm.schemas import ModelProfile, TokenUsage
from supportagent.llm.usage import LLMCallUsage, record_llm_usage


def test_online_rag_benchmark_uses_same_case_and_captures_usage(
    tmp_path,
    monkeypatch,
):
    dataset = tmp_path / "rag.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "household-coverage",
                "question": "Was deckt die Hausratversicherung ab?",
                "category": "coverage",
                "expected_sources": ["Hausratversicherung"],
                "expect_refusal": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        online_runner,
        "resolve_model",
        lambda model_id, task: ModelProfile(
            id=model_id,
            label=model_id,
            provider="qwen",
            provider_model=model_id,
            capabilities=frozenset({"text"}),
        ),
    )

    def answer_fn(question, **kwargs):
        record_llm_usage(
            LLMCallUsage(
                provider="qwen",
                model_id=kwargs["requested_model"],
                provider_model=kwargs["requested_model"],
                latency_ms=42.5,
                usage=TokenUsage(input_tokens=120, output_tokens=30),
            )
        )
        return SimpleNamespace(
            answer="Die Hausratversicherung deckt Hausrat gegen Schäden ab [1].",
            chunks=[{"metadata": {"title": "Hausratversicherung"}}],
            evidence=SimpleNamespace(status="sufficient"),
        )

    report = online_runner.run_online_rag_benchmark(
        models=["qwen3-max"],
        dataset_path=dataset,
        trials_per_case=2,
        answer_fn=answer_fn,
    )

    result = report.models[0]
    assert result.total_trials == 2
    assert result.pass_rate == 1
    assert result.source_recall == 1
    assert result.citation_validity_rate == 1
    assert result.stability_rate == 1
    assert result.input_tokens == 240
    assert result.output_tokens == 60
    assert result.llm_calls == 2
    assert all(trial.llm_latency_ms == 42.5 for trial in result.trials)


def test_pricing_catalog_accounts_for_cached_and_created_tokens():
    catalog = PricingCatalog(
        currency="USD",
        effective_date="2026-07-27",
        models={
            "claude-sonnet-4": ModelPrice(
                input_per_million=3,
                output_per_million=15,
                cached_input_per_million=0.3,
                cache_creation_input_per_million=3.75,
                source="official",
            )
        },
    )
    calls = [
        LLMCallUsage(
            provider="anthropic",
            model_id="claude-sonnet-4",
            provider_model="claude-sonnet-4-20250514",
            latency_ms=1,
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=20,
                cached_input_tokens=25,
                cache_creation_input_tokens=5,
            ),
        )
    ]

    assert catalog.estimate(calls) == pytest.approx(0.00053625)


def test_online_report_writes_json_and_markdown(tmp_path):
    report = online_runner.OnlineRAGBenchmarkReport(
        run_id="run-1",
        generated_at="2026-07-27T00:00:00+00:00",
        dataset_fingerprint="sha256:test",
        trials_per_case=1,
        minimum_pass_rate=0.75,
        threshold_passed=True,
        models=[],
    )
    json_path = tmp_path / "benchmark.json"

    markdown_path = online_runner.write_online_report(report, json_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["run_id"] == "run-1"
    assert "# SupportAgent Online RAG Benchmark" in markdown_path.read_text(
        encoding="utf-8"
    )


def test_online_cli_requires_explicit_live_confirmation():
    with pytest.raises(SystemExit, match="--confirm-live"):
        online_runner.main(["--models", "qwen3-max"])
