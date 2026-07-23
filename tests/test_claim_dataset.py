import json
from pathlib import Path

from supportagent.claims.document_rules import missing_documents_for_claim
from supportagent.claims.few_shot import CLAIM_REVIEW_FEW_SHOTS
from supportagent.claims.schemas import Claim, ClaimDocument
from supportagent.rag.builtin_seed import builtin_documents


ROOT = Path(__file__).resolve().parents[1]


def load_claim_fixtures():
    return json.loads((ROOT / "data" / "synthetic_claims.json").read_text())


def load_eval_cases():
    return [json.loads(line) for line in (ROOT / "evals" / "claim_review.jsonl").read_text().splitlines()]


def fixture_claim(item):
    return Claim(
        id=item["id"],
        owner_user_id="synthetic-user",
        policy_id=item["policy_id"],
        product_line=item["product_line"],
        policy_version=item["policy_version"],
        jurisdiction=item["jurisdiction"],
        customer_reference=item["customer_reference"],
        claim_type=item["claim_type"],
        status="DRAFT",
        created_at="2026-07-21T00:00:00+00:00",
        updated_at="2026-07-21T00:00:00+00:00",
    )


def fixture_documents(item):
    return [
        ClaimDocument(
            id=f"{item['id']}-{index}",
            claim_id=item["id"],
            document_type=document["document_type"],
            filename=f"{document['document_type']}.pdf",
            extraction_status=document["status"],
            created_at="2026-07-21T00:00:00+00:00",
        )
        for index, document in enumerate(item["documents"])
    ]


def test_synthetic_claim_dataset_matches_source_backed_rules():
    fixtures = load_claim_fixtures()
    assert len(fixtures) >= 12
    assert len({item["id"] for item in fixtures}) == len(fixtures)
    for item in fixtures:
        actual = missing_documents_for_claim(fixture_claim(item), fixture_documents(item))
        assert actual == item["expected"]["missing_required"], item["id"]


def test_eval_cases_reference_real_fixtures_and_match_expectations():
    fixtures = {item["id"]: item for item in load_claim_fixtures()}
    cases = load_eval_cases()
    assert len(cases) >= 12
    for case in cases:
        fixture = fixtures[case["claim_fixture"]]
        assert case["expected_missing"] == fixture["expected"]["missing_required"]
        assert "UPDATE_CLAIM_STATUS" in case["forbidden_executions"]


def test_few_shots_teach_behavior_without_policy_identifiers():
    assert len(CLAIM_REVIEW_FEW_SHOTS) >= 6
    serialized = json.dumps(CLAIM_REVIEW_FEW_SHOTS).casefold()
    assert "pol-" not in serialized
    assert "2026.1" not in serialized


def test_approved_knowledge_has_governance_metadata():
    documents = builtin_documents()
    approved = [document for document in documents if document.metadata["source"] == "confluence"]
    assert approved
    for document in approved:
        assert document.metadata["approval_status"] == "approved"
        assert document.metadata["product_line"]
        assert document.metadata["jurisdiction"] == "DE"
        assert document.metadata["effective_from"]
        assert document.metadata["owner_team"]
