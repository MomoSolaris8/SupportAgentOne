from supportagent.agent.router import route_question, RouteDecision
from supportagent.retrieval import retrieve
from supportagent.agent.evidence import check_evidence, EvidenceDecision
from supportagent.answer import REFUSAL_TEXT, generate_answer
from dataclasses import dataclass
from supportagent.agent.query_rewrite import QueryRewrite,rewrite_query

@dataclass(frozen=True)
class AgentResult:
    answer: str
    chunks: list[dict]
    route: RouteDecision
    rewrite: QueryRewrite
    evidence: EvidenceDecision

def answer_with_agent(question: str, source_filter: str | None = None) -> AgentResult:
    decision = route_question(question)

    if source_filter is not None:
        effective_source_filter = source_filter
    elif decision.source == "both":
        effective_source_filter = None
    else:
        effective_source_filter = decision.source

    rewrite = rewrite_query(question)
    chunks = retrieve(rewrite.rewritten_query, source_filter=effective_source_filter)

    evidence = check_evidence(chunks)
    if evidence.status == "insufficient":
        return AgentResult(
            answer=REFUSAL_TEXT,
            chunks=chunks,
            route=decision,
            evidence=evidence,
            rewrite=rewrite,
        )

    answer = generate_answer(question, chunks)

    return AgentResult(
        answer=answer,
        chunks=chunks,
        route=decision,
        evidence=evidence,
        rewrite=rewrite,
    )
