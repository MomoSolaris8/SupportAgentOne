from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from supportagent.claims.document_rules import (
    completed_document_types,
    conditional_documents_for_claim,
    missing_documents_for_claim,
    optional_documents_for_claim,
    required_documents_for_claim,
    requirements_for_claim,
)
from supportagent.claims.few_shot import format_claim_review_few_shots
from supportagent.claims.schemas import (
    Claim,
    ClaimDocument,
    ClaimEvidence,
    ClaimReviewResponse,
    CreateProposedActionRequest,
    ProposedAction,
)
from supportagent.claims.service import create_proposed_action, get_claim
from supportagent.core.answer import REFUSAL_TEXT, generate_answer
from supportagent.rag.retrieval import retrieve


class ClaimReviewState(TypedDict, total=False):
    run_id: str
    claim_id: str
    owner_user_id: str
    claim: Claim
    documents: list[ClaimDocument]
    required_documents: list[str]
    present_documents: list[str]
    missing_documents: list[str]
    optional_documents: list[str]
    conditional_documents: list[str]
    document_requirements: list[dict]
    retrieval_query: str
    chunks: list[dict]
    evidence_status: Literal["sufficient", "insufficient"]
    evidence_reason: str
    recommendation: str
    proposed_action: ProposedAction | None


def verify_claim_evidence(chunks: list[dict]) -> tuple[Literal["sufficient", "insufficient"], str]:
    if not chunks:
        return "insufficient", "No policy evidence was retrieved."
    approved = [chunk for chunk in chunks if chunk.get("metadata", {}).get("source") == "confluence"]
    if not approved:
        return "insufficient", "No approved Confluence policy evidence was retrieved."
    return "sufficient", f"{len(approved)} approved policy evidence chunk(s) were retrieved."


def load_claim_node(state: ClaimReviewState) -> ClaimReviewState:
    detail = get_claim(state["claim_id"], state["owner_user_id"])
    return {"claim": detail.claim, "documents": detail.documents}


def check_documents_node(state: ClaimReviewState) -> ClaimReviewState:
    claim = state["claim"]
    documents = state["documents"]
    return {
        "required_documents": required_documents_for_claim(claim),
        "present_documents": completed_document_types(documents),
        "missing_documents": missing_documents_for_claim(claim, documents),
        "optional_documents": optional_documents_for_claim(claim),
        "conditional_documents": conditional_documents_for_claim(claim),
        "document_requirements": [
            requirement.model_dump() for requirement in requirements_for_claim(claim)
        ],
    }


def retrieve_policy_node(state: ClaimReviewState) -> ClaimReviewState:
    claim = state["claim"]
    query = (
        f"Versicherungspolice {claim.policy_id}, Produkt {claim.product_line}, "
        f"Version {claim.policy_version or 'unbekannt'}, Rechtsraum {claim.jurisdiction}: "
        f"Anforderungen und Schadenprozess fuer Schadenart {claim.claim_type}"
    )
    if claim.product_line == "unknown":
        return {"retrieval_query": query, "chunks": []}
    return {
        "retrieval_query": query,
        "chunks": retrieve(query, source_filter="confluence"),
    }


def verify_evidence_node(state: ClaimReviewState) -> ClaimReviewState:
    if state["claim"].product_line == "unknown":
        return {
            "evidence_status": "insufficient",
            "evidence_reason": "Claim product_line is unknown; product-specific review is blocked.",
        }
    status, reason = verify_claim_evidence(state["chunks"])
    return {"evidence_status": status, "evidence_reason": reason}


def route_after_evidence(state: ClaimReviewState) -> Literal["generate_recommendation", "refuse_recommendation"]:
    return "generate_recommendation" if state["evidence_status"] == "sufficient" else "refuse_recommendation"


def refuse_recommendation_node(state: ClaimReviewState) -> ClaimReviewState:
    return {"recommendation": REFUSAL_TEXT}


def generate_recommendation_node(state: ClaimReviewState) -> ClaimReviewState:
    claim = state["claim"]
    missing = state["missing_documents"]
    question = (
        f"Pruefe Schaden {claim.id} zur Police {claim.policy_id}, Produkt {claim.product_line} "
        f"({claim.claim_type}). "
        f"Fehlende Pflichtunterlagen: {', '.join(missing) if missing else 'keine'}. "
        "Formuliere eine vorsichtige Empfehlung fuer die manuelle Schadenbearbeitung.\n\n"
        "Behavior examples (these define behavior, not policy facts):\n"
        f"{format_claim_review_few_shots()}"
    )
    return {"recommendation": generate_answer(question, state["chunks"])}


def propose_jira_node(state: ClaimReviewState) -> ClaimReviewState:
    missing = state["missing_documents"]
    if not missing:
        return {"proposed_action": None}
    claim = state["claim"]
    action = create_proposed_action(
        claim.id,
        state["owner_user_id"],
        CreateProposedActionRequest(
            run_id=state["run_id"],
            action_type="CREATE_JIRA_ISSUE",
            tool_server="jira_mcp",
            tool_name="create_issue",
            arguments={
                "project": "CLAIMS",
                "summary": f"Claim {claim.id}: missing required documents",
                "description": (
                    f"Policy: {claim.policy_id}\n"
                    f"Claim type: {claim.claim_type}\n"
                    f"Missing documents: {', '.join(missing)}"
                ),
                "labels": ["supportagent", "missing-documents"],
            },
            reason="Required claim documents are missing and need manual follow-up.",
        ),
    )
    return {"proposed_action": action}


def build_claim_review_graph():
    graph = StateGraph(ClaimReviewState)
    graph.add_node("load_claim", load_claim_node)
    graph.add_node("check_documents", check_documents_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("verify_evidence", verify_evidence_node)
    graph.add_node("generate_recommendation", generate_recommendation_node)
    graph.add_node("refuse_recommendation", refuse_recommendation_node)
    graph.add_node("propose_jira", propose_jira_node)
    graph.add_edge(START, "load_claim")
    graph.add_edge("load_claim", "check_documents")
    graph.add_edge("check_documents", "retrieve_policy")
    graph.add_edge("retrieve_policy", "verify_evidence")
    graph.add_conditional_edges(
        "verify_evidence",
        route_after_evidence,
        ["generate_recommendation", "refuse_recommendation"],
    )
    graph.add_edge("generate_recommendation", "propose_jira")
    graph.add_edge("refuse_recommendation", "propose_jira")
    graph.add_edge("propose_jira", END)
    return graph.compile()


CLAIM_REVIEW_GRAPH = build_claim_review_graph()


def _evidence_from_chunks(chunks: list[dict]) -> list[ClaimEvidence]:
    evidence: list[ClaimEvidence] = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if metadata.get("source") != "confluence":
            continue
        evidence.append(
            ClaimEvidence(
                source_id=str(metadata.get("source_id", "")),
                title=str(metadata.get("title", "Untitled source")),
                url=str(metadata.get("url", "")),
                source="confluence",
            )
        )
    return evidence


def review_claim(claim_id: str, owner_user_id: str) -> ClaimReviewResponse:
    state = CLAIM_REVIEW_GRAPH.invoke(
        {"run_id": str(uuid4()), "claim_id": claim_id, "owner_user_id": owner_user_id}
    )
    return ClaimReviewResponse(
        run_id=state["run_id"],
        claim_id=claim_id,
        required_documents=state["required_documents"],
        present_documents=state["present_documents"],
        missing_documents=state["missing_documents"],
        optional_documents=state["optional_documents"],
        conditional_documents=state["conditional_documents"],
        document_requirements=state["document_requirements"],
        evidence_status=state["evidence_status"],
        evidence_reason=state["evidence_reason"],
        evidence=_evidence_from_chunks(state["chunks"]),
        recommendation=state["recommendation"],
        proposed_action=state.get("proposed_action"),
    )
