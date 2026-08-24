"""Invariants that make the derived gold labels trustworthy.

If any of these break, ``expected_sources`` stops being ground truth and the
evaluation set silently becomes noise - so they are asserted, not assumed.
"""

import re

import pytest
from pydantic import ValidationError

from supportagent.corpus.evalgen import generate_gold_set
from supportagent.corpus.generate import generate
from supportagent.corpus.world import World, load_world, variant_key
from supportagent.evaluation.datasets import RAGEvalCase


@pytest.fixture(scope="module")
def world() -> World:
    return load_world()


@pytest.fixture(scope="module")
def corpus(world):
    return generate(world)


@pytest.fixture(scope="module")
def gold(world, corpus):
    return generate_gold_set(world, corpus)


@pytest.fixture(scope="module")
def pages_by_title(corpus) -> dict:
    return {page["title"]: page for page in corpus.pages}


@pytest.fixture(scope="module")
def issues_by_summary(corpus) -> dict:
    return {issue["summary"]: issue for issue in corpus.issues}


def _issue_text(issue: dict) -> str:
    return " ".join([issue["description"], *issue["comments"]])


def test_world_model_loads_and_validates(world):
    assert world.facts
    assert world.products
    assert world.jira_only_patterns


def test_every_fact_variant_has_exactly_one_home(world, corpus):
    expected = {
        variant_key(fact.id, variant.tariff)
        for fact in world.facts
        for variant in fact.variants
    }

    assert set(corpus.homes) == expected


def test_home_states_the_value(world, corpus, pages_by_title, issues_by_summary):
    for fact in world.facts:
        for variant in fact.variants:
            home = corpus.homes[variant_key(fact.id, variant.tariff)]
            if home.kind == "confluence":
                body = pages_by_title[home.title]["body"]
            else:
                body = _issue_text(issues_by_summary[home.title])
            assert variant.value in body, f"{fact.id}/{variant.tariff} missing from its home"


def test_distractor_issues_never_restate_a_numeric_value(world, corpus, issues_by_summary):
    """Jira issues about Confluence-homed facts must point at the page, not answer.

    Restricted to values containing digits, so the check cannot trip over a
    common German word appearing in the narrative template.
    """
    for issue in corpus.issues:
        fact_id = issue["fact_id"]
        if fact_id is None:
            continue
        fact = world.facts_by_id[fact_id]
        if fact.placement != "confluence":
            continue
        text = _issue_text(issue)
        for variant in fact.variants:
            if not re.search(r"\d", variant.value):
                continue
            assert variant.value not in text, f"{issue['summary']} leaks {fact_id}"


def test_jira_only_facts_are_homed_in_jira(world, corpus):
    jira_only = [fact for fact in world.facts if fact.placement == "jira_only"]
    assert jira_only, "world model should exercise cross-source retrieval"

    for fact in jira_only:
        for variant in fact.variants:
            assert corpus.homes[variant_key(fact.id, variant.tariff)].kind == "jira"


def test_restricted_facts_are_marked_and_never_expected_as_sources(world, corpus, gold, pages_by_title):
    restricted_titles = {
        page["title"] for page in corpus.pages if page["visibility"] == "restricted"
    }
    assert restricted_titles

    for fact in world.facts:
        if fact.visibility != "restricted":
            continue
        for variant in fact.variants:
            assert corpus.homes[variant_key(fact.id, variant.tariff)].restricted

    for case in gold:
        assert not restricted_titles & set(case.expected_sources)

    permission_cases = [case for case in gold if case.category == "permission_boundary"]
    assert permission_cases
    for case in permission_cases:
        assert case.expect_refusal
        assert set(case.must_not_use) <= restricted_titles


def test_gold_sources_resolve_to_real_documents(gold, pages_by_title, issues_by_summary):
    known = set(pages_by_title) | set(issues_by_summary)

    for case in gold:
        assert set(case.expected_sources) <= known, case.case_id
        assert set(case.must_not_use) <= known, case.case_id
        assert not set(case.expected_sources) & set(case.must_not_use), case.case_id


def test_answerable_cases_have_exactly_one_expected_source(gold):
    for case in gold:
        if case.expect_refusal:
            assert case.expected_sources == []
        else:
            assert len(case.expected_sources) == 1, case.case_id
            assert case.expected_answer


def test_recency_cases_list_the_superseded_page_as_forbidden(corpus, gold):
    archive_titles = {page["title"] for page in corpus.pages if page["project"] == "archiv"}
    recency_cases = [case for case in gold if case.category == "recency_conflict"]
    assert recency_cases

    for case in recency_cases:
        assert archive_titles & set(case.must_not_use), case.case_id


def test_out_of_scope_questions_expect_refusal(gold):
    cases = [case for case in gold if case.category == "out_of_scope_refusal"]
    assert cases
    assert all(case.expect_refusal and not case.expected_sources for case in cases)


def test_generation_is_deterministic(world):
    first, second = generate(world), generate(world)

    assert first.pages == second.pages
    assert first.issues == second.issues
    assert first.homes == second.homes


def test_gold_cases_load_as_rag_eval_cases(gold):
    for case in gold:
        loaded = RAGEvalCase.model_validate(case.to_dict())
        assert loaded.case_id == case.case_id


def test_world_model_rejects_mixed_tariff_variants():
    payload = {
        "insurer": {"name": "Test"},
        "sections": [{"key": "s", "title": "S", "body": "<p>s</p>"}],
        "products": [
            {"key": "p", "section": "s", "name": "P", "summary": "s", "tariffs": ["Basis"]}
        ],
        "processes": [],
        "facts": [
            {
                "id": "p.mixed",
                "subject": "p",
                "topic": "T",
                "attribute": "A",
                # A shared variant next to a tariff-specific one would give a
                # question two valid homes.
                "variants": [{"value": "x"}, {"tariff": "Basis", "value": "y"}],
            }
        ],
        "jira_patterns": [],
    }

    with pytest.raises(ValidationError, match="mixes tariff-specific and shared variants"):
        World.model_validate(payload)


def test_world_model_rejects_unknown_tariff():
    payload = {
        "insurer": {"name": "Test"},
        "sections": [{"key": "s", "title": "S", "body": "<p>s</p>"}],
        "products": [
            {"key": "p", "section": "s", "name": "P", "summary": "s", "tariffs": ["Basis"]}
        ],
        "processes": [],
        "facts": [
            {
                "id": "p.unknown",
                "subject": "p",
                "topic": "T",
                "attribute": "A",
                "variants": [{"tariff": "Gold", "value": "y"}],
            }
        ],
        "jira_patterns": [],
    }

    with pytest.raises(ValidationError, match="tariff Gold not in p"):
        World.model_validate(payload)
