from supportagent.claims.document_rules import (
    conditional_documents_for_claim,
    completed_document_types,
    missing_documents_for_claim,
    optional_documents_for_claim,
    requirements_for_claim,
    required_documents_for_claim,
)
from supportagent.claims.review_workflow import verify_claim_evidence
from supportagent.claims.schemas import Claim, ClaimDetail, ClaimDocument, ProposedAction


def claim(claim_type: str = "water_damage", product_line: str = "residential_building") -> Claim:
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
    assert conditional_documents_for_claim(claim()) == ["police_report", "purchase_receipt"]


def test_pending_document_does_not_count_as_present():
    documents = [
        document("claim-form"),
        document("damage photo"),
        document("damage_cause_report", status="PENDING"),
    ]
    assert completed_document_types(documents) == ["claim_form", "damage_photo"]
    assert missing_documents_for_claim(claim(), documents) == ["damage_cause_report", "repair_invoice"]


def test_unknown_claim_type_still_requires_source_backed_general_documents():
    assert required_documents_for_claim(claim("other")) == ["claim_form", "damage_photo"]


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


def test_unknown_product_line_is_not_given_product_specific_rules():
    from supportagent.claims.review_workflow import retrieve_policy_node, verify_evidence_node

    unknown = claim(product_line="unknown")
    assert required_documents_for_claim(unknown) == ["claim_form", "damage_photo"]
    retrieved = retrieve_policy_node({"claim": unknown})
    assert retrieved["chunks"] == []
    decision = verify_evidence_node({"claim": unknown, "chunks": []})
    assert decision["evidence_status"] == "insufficient"
    assert "product_line is unknown" in decision["evidence_reason"]


def proposed_action(run_id: str) -> ProposedAction:
    return ProposedAction(
        id="action-1",
        claim_id="claim-1",
        run_id=run_id,
        action_type="CREATE_JIRA_ISSUE",
        tool_server="jira_mcp",
        tool_name="create_issue",
        arguments={"summary": "Missing documents"},
        reason="Required documents are missing.",
        risk_level="medium",
        status="WAITING_FOR_APPROVAL",
        proposed_by="user-1",
        created_at="2026-07-21T00:00:00+00:00",
        updated_at="2026-07-21T00:00:00+00:00",
    )


def test_review_graph_uses_verified_evidence_and_only_proposes_write(monkeypatch):
    from supportagent.claims import review_workflow

    documents = [document("claim_form")]
    monkeypatch.setattr(
        review_workflow,
        "get_claim",
        lambda claim_id, owner_user_id: ClaimDetail(claim=claim(), documents=documents),
    )
    monkeypatch.setattr(
        review_workflow,
        "retrieve",
        lambda query, source_filter=None: [
            {
                "content": "Approved policy evidence.",
                "metadata": {
                    "source": "confluence",
                    "source_id": "policy-1",
                    "title": "Water damage policy",
                    "url": "https://example.invalid/policy-1",
                },
            }
        ],
    )
    monkeypatch.setattr(
        review_workflow,
        "generate_answer",
        lambda question, chunks: "Evidence-backed manual review recommendation [1].",
    )
    proposed_requests = []

    def fake_create_proposed_action(claim_id, owner_user_id, request):
        proposed_requests.append(request)
        return proposed_action(request.run_id)

    monkeypatch.setattr(review_workflow, "create_proposed_action", fake_create_proposed_action)

    result = review_workflow.review_claim("claim-1", "user-1")

    assert result.evidence_status == "sufficient"
    assert result.missing_documents == ["damage_cause_report", "damage_photo", "repair_invoice"]
    assert result.recommendation.endswith("[1].")
    assert result.proposed_action is not None
    assert result.proposed_action.status == "WAITING_FOR_APPROVAL"
    assert proposed_requests[0].action_type == "CREATE_JIRA_ISSUE"


def test_review_graph_refuses_without_policy_evidence_and_does_not_call_model(monkeypatch):
    from supportagent.claims import review_workflow
    from supportagent.core.answer import REFUSAL_TEXT

    monkeypatch.setattr(
        review_workflow,
        "get_claim",
        lambda claim_id, owner_user_id: ClaimDetail(claim=claim(), documents=[document("claim_form")]),
    )
    monkeypatch.setattr(
        review_workflow,
        "retrieve",
        lambda query, source_filter=None: [
            {"content": "Unapproved ticket", "metadata": {"source": "jira"}}
        ],
    )

    def model_must_not_run(*args, **kwargs):
        raise AssertionError("The model must not run without approved policy evidence.")

    monkeypatch.setattr(review_workflow, "generate_answer", model_must_not_run)
    monkeypatch.setattr(
        review_workflow,
        "create_proposed_action",
        lambda claim_id, owner_user_id, request: proposed_action(request.run_id),
    )

    result = review_workflow.review_claim("claim-1", "user-1")

    assert result.evidence_status == "insufficient"
    assert result.recommendation == REFUSAL_TEXT
    assert result.evidence == []
    assert result.proposed_action is not None
    assert result.proposed_action.status == "WAITING_FOR_APPROVAL"
