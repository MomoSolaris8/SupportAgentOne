import logging
from dataclasses import dataclass

from supportagent.agent.evidence import EvidenceDecision, check_evidence
from supportagent.agent.query_rewrite import QueryRewrite, rewrite_query
from supportagent.agent.router import RouteDecision, route_question
from supportagent.answer import REFUSAL_TEXT, generate_answer
from supportagent.langfuse_client import get_langfuse_client
from supportagent.retrieval import retrieve
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    answer: str
    chunks: list[dict]
    route: RouteDecision
    rewrite: QueryRewrite
    evidence: EvidenceDecision


def record_langfuse_trace(
    question: str,
    source_filter: str | None,
    effective_source_filter: str | None,
    result: AgentResult,
) -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.trace(
            name="answer_with_agent",
            input={
                "question": question,
                "source_filter": source_filter,
            },
            output={
                "answer": result.answer,
            },
            metadata={
                "effective_source_filter": effective_source_filter,
                "route_source": result.route.source,
                "route_reason": result.route.reason,
                "rewrite_changed": result.rewrite.changed,
                "rewritten_query": result.rewrite.rewritten_query,
                "evidence_status": result.evidence.status,
                "evidence_reason": result.evidence.reason,
                "chunk_count": len(result.chunks),
            },
        )
    except Exception:
        logger.exception("langfuse_trace_failed")


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
        result = AgentResult(
            answer=REFUSAL_TEXT,
            chunks=chunks,
            route=decision,
            evidence=evidence,
            rewrite=rewrite,
        )
        record_langfuse_trace(
            question=question,
            source_filter=source_filter,
            effective_source_filter=effective_source_filter,
            result=result,
        )
        return result

    answer = generate_answer(question, chunks)
    logger.info("agent_answer_generated chunk_count=%d", len(chunks))

    result = AgentResult(
        answer=answer,
        chunks=chunks,
        route=decision,
        evidence=evidence,
        rewrite=rewrite,
    )
    record_langfuse_trace(
        question=question,
        source_filter=source_filter,
        effective_source_filter=effective_source_filter,
        result=result,
    )
    return result
