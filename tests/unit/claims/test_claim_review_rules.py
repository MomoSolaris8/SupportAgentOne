from supportagent.claims.document_rules import (
    conditional_documents_for_claim,
    completed_document_types,
    missing_documents_for_claim,
    optional_documents_for_claim,
    requirements_for_claim,
    required_documents_for_claim,
)
from supportagent.claims.review_workflow import verify_claim_evidence
from supportagent.claims.schemas import Claim, ClaimDocument


def claim(
    claim_type: str = "water_damage",
    product_line: str = "residential_building",
) -> Claim:
    return Claim(
        id="claim-1",
        owner_user_id="user-1",
        policy_id="POL-1",
        product_line=product_line,
        policy_version="2026.1",
        jurisdiction="DE",
        customer_reference="CUSTOMER-1",
        claim_type=claim_type,
        status="DRAFT",
        created_at="2026-07-21T00:00:00+00:00",
        updated_at="2026-07-21T00:00:00+00:00",
    )


def document(document_type: str, status: str = "COMPLETED") -> ClaimDocument:
    return ClaimDocument(
        id=f"doc-{document_type}",
        claim_id="claim-1",
        document_type=document_type,
        filename=f"{document_type}.pdf",
        extraction_status=status,
        created_at="2026-07-21T00:00:00+00:00",
    )


def test_water_damage_document_requirements_are_deterministic():
    assert required_documents_for_claim(claim()) == [
        "claim_form",
        "damage_cause_report",
        "damage_photo",
        "repair_invoice",
    ]
    assert optional_documents_for_claim(claim()) == ["repair_estimate"]
    assert conditional_documents_for_claim(claim()) == [
        "police_report",
        "purchase_receipt",
    ]


def test_pending_document_does_not_count_as_present():
    documents = [
        document("claim-form"),
        document("damage photo"),
        document("damage_cause_report", status="PENDING"),
    ]
    assert completed_document_types(documents) == ["claim_form", "damage_photo"]
    assert missing_documents_for_claim(claim(), documents) == [
        "damage_cause_report",
        "repair_invoice",
    ]


def test_unknown_claim_type_still_requires_source_backed_general_documents():
    assert required_documents_for_claim(claim("other")) == [
        "claim_form",
        "damage_photo",
    ]


def test_every_requirement_is_traceable_to_a_source():
    for requirement in requirements_for_claim(claim()):
        assert requirement.source_id.startswith("seed-")
        assert requirement.source_title
        assert requirement.evidence_excerpt


def test_claim_evidence_requires_approved_confluence_source():
    assert verify_claim_evidence([])[0] == "insufficient"
    assert verify_claim_evidence(
        [{"content": "ticket", "metadata": {"source": "jira"}}]
    )[0] == "insufficient"
    assert verify_claim_evidence(
        [{"content": "policy", "metadata": {"source": "confluence"}}]
    )[0] == "sufficient"
