from supportagent.agent.workflow import answer_with_agent


def stub_agent_dependencies(monkeypatch):
    monkeypatch.setattr(
        "supportagent.agent.workflow.load_memory_context",
        lambda **kwargs: ([], []),
    )
    monkeypatch.setattr("supportagent.agent.workflow.save_memory_turn", lambda **kwargs: None)
    monkeypatch.setattr(
        "supportagent.agent.workflow.run_dynamic_mcp_agent_sync",
        lambda *args, **kwargs: type("MCPResult", (), {"answer": None, "tool_calls": [], "error": None})(),
    )
    monkeypatch.setattr(
        "supportagent.agent.workflow.resolve_model",
        lambda *args, **kwargs: type("Model", (), {"id": "qwen-plus"})(),
    )
    monkeypatch.setattr(
        "supportagent.agent.workflow.retrieve",
        lambda question, source_filter=None: [{"content": "fake chunk", "metadata": {}, "distance": 0.1}],
    )
    monkeypatch.setattr(
        "supportagent.agent.workflow.generate_answer",
        lambda *args, **kwargs: "fake answer",
    )


def test_each_agent_node_is_a_child_of_one_trace(monkeypatch, langfuse_spans):
    stub_agent_dependencies(monkeypatch)

    answer_with_agent("Gibt es ein Jira Ticket zur Dokumentationslücke?", thread_id="thread-1", user_id="user-1")

    spans = {span.name: span for span in langfuse_spans()}
    root = spans["answer_with_agent"]
    assert root.parent is None
    assert root.attributes["user.id"] == "user-1"
    assert root.attributes["session.id"] == "thread-1"
    for node in ["load_memory", "mcp_tools", "route", "rewrite", "retrieve", "check_evidence", "generate_answer"]:
        assert spans[node].parent.span_id == root.context.span_id, node
