import logging
from dataclasses import dataclass

from supportagent.agent.router import route_question, RouteDecision
from supportagent.retrieval import retrieve
from supportagent.agent.evidence import check_evidence, EvidenceDecision
from supportagent.answer import REFUSAL_TEXT, generate_answer
from supportagent.agent.query_rewrite import QueryRewrite, rewrite_query

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    answer: str
    chunks: list[dict]
    route: RouteDecision
    rewrite: QueryRewrite
    evidence: EvidenceDecision


def answer_with_agent(question: str, source_filter: str | None = None) -> AgentResult:
    logger.info("agent_start source_filter=%s question=%r", source_filter, question)
    decision = route_question(question)
    logger.info(
        "agent_route source=%s reason=%s",
        decision.source,
        decision.reason,
    )
    if source_filter is not None:
        effective_source_filter = source_filter
    elif decision.source == "both":
        effective_source_filter = None
    else:
        effective_source_filter = decision.source
    logger.info("agent_effective_source_filter source_filter=%s", effective_source_filter)
    rewrite = rewrite_query(question)
    logger.info(
        "query_rewrite changed=%s rewritten_query=%r reason=%s",
        rewrite.changed,
        rewrite.rewritten_query,
        rewrite.reason,
    )
    chunks = retrieve(rewrite.rewritten_query, source_filter=effective_source_filter)
    logger.info("retrieval_complete chunk_count=%d", len(chunks))
    evidence = check_evidence(chunks)
    logger.info(
        "evidence_check status=%s reason=%s",
        evidence.status,
        evidence.reason,
    )
    if evidence.status == "insufficient":
        logger.info("agent_refusal reason=%s", evidence.reason)
        return AgentResult(
            answer=REFUSAL_TEXT,
            chunks=chunks,
            route=decision,
            evidence=evidence,
            rewrite=rewrite,
        )

    answer = generate_answer(question, chunks)
    logger.info("agent_answer_generated chunk_count=%d", len(chunks))

    return AgentResult(
        answer=answer,
        chunks=chunks,
        route=decision,
        evidence=evidence,
        rewrite=rewrite,
    )
