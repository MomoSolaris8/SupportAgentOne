import logging
from dataclasses import dataclass
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from supportagent.agent.evidence import EvidenceDecision, check_evidence
from supportagent.agent.query_rewrite import QueryRewrite, rewrite_query
from supportagent.agent.router import RouteDecision, route_question
from supportagent.core.answer import (
    REFUSAL_TEXT,
    answer_reports_insufficient_evidence,
    generate_answer,
)
from supportagent.integrations.langfuse_client import get_langfuse_client
from supportagent.llm import resolve_model
from supportagent.memory import ChatMessage, LongMemory, load_memory_context, save_memory_turn
from supportagent.mcp_client.tool_agent import MCPToolCallTrace, run_dynamic_mcp_agent_sync
from supportagent.rag.retrieval import retrieve
from supportagent.skills import get_skill_instructions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    answer: str
    chunks: list[dict]
    route: RouteDecision
    rewrite: QueryRewrite
    evidence: EvidenceDecision
    short_memory_count: int = 0
    long_memory_count: int = 0
    mcp_tool_calls: list[MCPToolCallTrace] | None = None
    mcp_error: str | None = None
    enabled_skills: list[str] | None = None
    model: str = "qwen-plus"
    image_count: int = 0


class AgentState(TypedDict, total=False):
    question: str
    thread_id: str | None
    user_id: str | None
    source_filter: str | None
    model: str
    image_contexts: list[str]
    enabled_mcp_servers: list[str] | None
    enabled_skills: list[str] | None
    skill_instructions: list[str]
    effective_source_filter: str | None
    short_history: list[ChatMessage]
    long_memories: list[LongMemory]
    route: RouteDecision
    rewrite: QueryRewrite
    chunks: list[dict]
    evidence: EvidenceDecision
    answer: str
    mcp_tool_calls: list[MCPToolCallTrace]
    mcp_error: str | None


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
        with client.start_as_current_observation(
            as_type="span",
            name="answer_with_agent",
        ) as span:
            span.update(
                input={
                    "question": question,
                    "source_filter": source_filter,
                },
                output={
                    "answer": result.answer,
                },
                metadata={
                    "effective_source_filter": effective_source_filter,
                    "short_memory_count": result.short_memory_count,
                    "long_memory_count": result.long_memory_count,
                    "route_source": result.route.source,
                    "route_reason": result.route.reason,
                    "rewrite_changed": result.rewrite.changed,
                    "rewritten_query": result.rewrite.rewritten_query,
                    "evidence_status": result.evidence.status,
                    "evidence_reason": result.evidence.reason,
                    "chunk_count": len(result.chunks),
                    "mcp_tool_calls": [
                        {
                            "server": tool_call.server,
                            "tool": tool_call.tool,
                            "arguments": tool_call.arguments,
                        }
                        for tool_call in result.mcp_tool_calls or []
                    ],
                    "mcp_error": result.mcp_error,
                    "enabled_skills": result.enabled_skills or [],
                    "model": result.model,
                    "image_count": result.image_count,
                },
            )

        client.flush()
    except Exception:
        logger.exception("langfuse_trace_failed")


def route_node(state: AgentState) -> AgentState:
    question = state["question"]
    source_filter = state.get("source_filter")
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
    return {
        "route": decision,
        "effective_source_filter": effective_source_filter,
    }


def load_memory_node(state: AgentState) -> AgentState:
    short_history, long_memories = load_memory_context(
        thread_id=state.get("thread_id"),
        user_id=state.get("user_id"),
        question=state["question"],
    )
    logger.info(
        "memory_loaded short_count=%d long_count=%d",
        len(short_history),
        len(long_memories),
    )
    return {
        "short_history": short_history,
        "long_memories": long_memories,
        "skill_instructions": get_skill_instructions(state.get("enabled_skills")),
    }


def mcp_tool_node(state: AgentState) -> AgentState:
    result = run_dynamic_mcp_agent_sync(
        state["question"],
        user_id=state.get("user_id"),
        enabled_mcp_servers=state.get("enabled_mcp_servers"),
        model=state.get("model"),
    )
    if result.error:
        logger.warning("mcp_dynamic_agent_error error=%s", result.error)
    if result.tool_calls:
        logger.info(
            "mcp_dynamic_tool_calls tools=%s",
            [(tool_call.server, tool_call.tool) for tool_call in result.tool_calls],
        )
    if result.answer and result.tool_calls:
        return {
            "answer": result.answer,
            "chunks": [],
            "route": RouteDecision(source="both", reason="Answered through dynamic MCP tool calling."),
            "rewrite": QueryRewrite(
                original_query=state["question"],
                normalized_query=state["question"],
                rewritten_query=state["question"],
                changed=False,
                reason="MCP tool result answered the request before RAG retrieval.",
            ),
            "evidence": EvidenceDecision(
                status="sufficient",
                reason="Dynamic MCP tool call returned an answer.",
            ),
            "mcp_tool_calls": result.tool_calls,
            "mcp_error": result.error,
        }
    return {
        "mcp_tool_calls": result.tool_calls,
        "mcp_error": result.error,
    }


def route_after_mcp(state: AgentState) -> Literal["route", "__end__"]:
    if state.get("answer") and state.get("mcp_tool_calls"):
        return "__end__"
    return "route"


def rewrite_node(state: AgentState) -> AgentState:
    rewrite = rewrite_query(state["question"])
    logger.info(
        "query_rewrite changed=%s rewritten_query=%r reason=%s",
        rewrite.changed,
        rewrite.rewritten_query,
        rewrite.reason,
    )
    return {"rewrite": rewrite}


def retrieve_node(state: AgentState) -> AgentState:
    rewrite = state["rewrite"]
    effective_source_filter = state.get("effective_source_filter")
    chunks = retrieve(rewrite.rewritten_query, source_filter=effective_source_filter)
    logger.info("retrieval_complete chunk_count=%d", len(chunks))
    return {"chunks": chunks}


def check_evidence_node(state: AgentState) -> AgentState:
    chunks = state["chunks"]
    evidence = check_evidence(chunks)
    logger.info(
        "evidence_check status=%s reason=%s",
        evidence.status,
        evidence.reason,
    )
    return {"evidence": evidence}


def route_after_evidence(state: AgentState) -> Literal["refuse_answer", "generate_answer"]:
    if state["evidence"].status == "insufficient" and not state.get("image_contexts"):
        return "refuse_answer"
    return "generate_answer"


def refuse_answer_node(state: AgentState) -> AgentState:
    logger.info("agent_refusal reason=%s", state["evidence"].reason)
    return {"answer": REFUSAL_TEXT}


def generate_answer_node(state: AgentState) -> AgentState:
    chunks = state["chunks"]
    answer = generate_answer(
        state["rewrite"].normalized_query,
        chunks,
        short_history=state.get("short_history", []),
        long_memories=state.get("long_memories", []),
        skill_instructions=state.get("skill_instructions", []),
        image_contexts=state.get("image_contexts", []),
        model=state.get("model"),
    )
    logger.info("agent_answer_generated chunk_count=%d", len(chunks))
    if answer_reports_insufficient_evidence(answer):
        return {
            "answer": answer,
            "evidence": EvidenceDecision(
                status="insufficient",
                reason="Retrieved candidates did not support a reliable answer.",
            ),
        }
    return {"answer": answer}


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("mcp_tools", mcp_tool_node)
    graph.add_node("route", route_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("check_evidence", check_evidence_node)
    graph.add_node("refuse_answer", refuse_answer_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "mcp_tools")
    graph.add_conditional_edges(
        "mcp_tools",
        route_after_mcp,
        {
            "route": "route",
            "__end__": END,
        },
    )
    graph.add_edge("route", "rewrite")
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("retrieve", "check_evidence")
    graph.add_conditional_edges(
        "check_evidence",
        route_after_evidence,
        ["refuse_answer", "generate_answer"],
    )
    graph.add_edge("refuse_answer", END)
    graph.add_edge("generate_answer", END)
    return graph.compile()


AGENT_GRAPH = build_agent_graph()


def answer_with_agent(
    question: str,
    source_filter: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    requested_model: str | None = None,
    image_contexts: list[str] | None = None,
    enabled_mcp_servers: list[str] | None = None,
    enabled_skills: list[str] | None = None,
) -> AgentResult:
    logger.info("agent_start source_filter=%s question=%r", source_filter, question)
    model = resolve_model(requested_model, task="chat").id
    state = AGENT_GRAPH.invoke(
        {
            "question": question,
            "source_filter": source_filter,
            "thread_id": thread_id,
            "user_id": user_id,
            "model": model,
            "image_contexts": image_contexts or [],
            "enabled_mcp_servers": enabled_mcp_servers,
            "enabled_skills": enabled_skills,
        }
    )
    chunks = state["chunks"]
    evidence = state["evidence"]
    decision = state["route"]
    rewrite = state["rewrite"]
    effective_source_filter = state.get("effective_source_filter")

    result = AgentResult(
        answer=state["answer"],
        chunks=chunks,
        route=decision,
        evidence=evidence,
        rewrite=rewrite,
        short_memory_count=len(state.get("short_history", [])),
        long_memory_count=len(state.get("long_memories", [])),
        mcp_tool_calls=state.get("mcp_tool_calls", []),
        mcp_error=state.get("mcp_error"),
        enabled_skills=enabled_skills or [],
        model=model,
        image_count=len(image_contexts or []),
    )
    save_memory_turn(
        thread_id=thread_id,
        user_id=user_id,
        question=question,
        answer=result.answer,
    )
    record_langfuse_trace(
        question=question,
        source_filter=source_filter,
        effective_source_filter=effective_source_filter,
        result=result,
    )
    return result
