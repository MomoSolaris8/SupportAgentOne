from supportagent.agent.workflow import answer_with_agent
from supportagent.core.answer import REFUSAL_TEXT


def disable_mcp_tools(monkeypatch):
    monkeypatch.setattr(
        "supportagent.agent.workflow.run_dynamic_mcp_agent_sync",
        lambda *args, **kwargs: type("MCPResult", (), {"answer": None, "tool_calls": [], "error": None})(),
    )


def test_agent_routes_jira_question_to_jira(monkeypatch):
    disable_mcp_tools(monkeypatch)
    captured = {}
    def fake_retrieve(question, source_filter=None):
        captured["question"] = question
        captured["source_filter"] = source_filter
        return [{"content": "fake chunk", "metadata": {}, "distance": 0.1}]

    def fake_generate_answer(question, chunks, short_history=None, long_memories=None, **kwargs):
        return "fake answer"

    monkeypatch.setattr("supportagent.agent.workflow.retrieve", fake_retrieve)
    monkeypatch.setattr("supportagent.agent.workflow.generate_answer", fake_generate_answer)

    result = answer_with_agent("Gibt es ein Jira Ticket zur Dokumentationslücke?")

    assert result.answer == "fake answer"
    assert captured["source_filter"] == "jira"
    assert result.route.source == "jira"
    assert result.evidence.status == "sufficient"

def test_agent_routes_confluence_question_to_confluence(monkeypatch):
    disable_mcp_tools(monkeypatch)
    captured = {}

    def fake_retrieve(question, source_filter=None):
        captured["question"] = question
        captured["source_filter"] = source_filter
        return [{"content": "fake chunk", "metadata": {}, "distance": 0.1}]

    def fake_generate_answer(question, chunks, short_history=None, long_memories=None, **kwargs):
        return "fake answer"

    monkeypatch.setattr("supportagent.agent.workflow.retrieve", fake_retrieve)
    monkeypatch.setattr("supportagent.agent.workflow.generate_answer", fake_generate_answer)

    result = answer_with_agent("Welche Unterlagen brauche ich fuer eine Schadenmeldung?")

    assert result.answer == "fake answer"
    assert captured["source_filter"] == "confluence"


def test_manual_source_filter_overrides_router(monkeypatch):
    disable_mcp_tools(monkeypatch)
    captured = {}

    def fake_retrieve(question, source_filter=None):
        captured["question"] = question
        captured["source_filter"] = source_filter
        return [{"content": "fake chunk", "metadata": {}, "distance": 0.1}]

    def fake_generate_answer(question, chunks, short_history=None, long_memories=None, **kwargs):
        return "fake answer"

    monkeypatch.setattr("supportagent.agent.workflow.retrieve", fake_retrieve)
    monkeypatch.setattr("supportagent.agent.workflow.generate_answer", fake_generate_answer)

    result = answer_with_agent(
        "Gibt es ein Jira Ticket zur Dokumentationslücke?",
        source_filter="confluence",
    )

    assert result.answer == "fake answer"
    assert captured["source_filter"] == "confluence"


def test_agent_refuses_when_evidence_is_insufficient(monkeypatch):
    disable_mcp_tools(monkeypatch)
    def fake_retrieve(question, source_filter=None):
        return []

    def fake_generate_answer(question, chunks, short_history=None, long_memories=None, **kwargs):
        raise AssertionError("generate_answer should not be called when evidence is insufficient")

    monkeypatch.setattr("supportagent.agent.workflow.retrieve", fake_retrieve)
    monkeypatch.setattr("supportagent.agent.workflow.generate_answer", fake_generate_answer)

    result = answer_with_agent("Was ist versichert?")

    assert result.answer == REFUSAL_TEXT
    assert result.chunks == []
    assert result.evidence.status == "insufficient"


def test_agent_marks_model_refusal_as_insufficient_evidence(monkeypatch):
    disable_mcp_tools(monkeypatch)
    monkeypatch.setattr(
        "supportagent.agent.workflow.retrieve",
        lambda question, source_filter=None: [
            {"content": "related candidate", "metadata": {}, "distance": 0.2}
        ],
    )
    monkeypatch.setattr(
        "supportagent.agent.workflow.generate_answer",
        lambda *args, **kwargs: REFUSAL_TEXT,
    )

    result = answer_with_agent("Was bedeutet Schädigung?")

    assert result.answer == REFUSAL_TEXT
    assert result.evidence.status == "insufficient"
    assert result.evidence.reason == "Retrieved candidates did not support a reliable answer."


def test_agent_marks_unsupported_terminology_as_insufficient_evidence(monkeypatch):
    disable_mcp_tools(monkeypatch)
    monkeypatch.setattr(
        "supportagent.agent.workflow.retrieve",
        lambda question, source_filter=None: [
            {"content": "related candidate", "metadata": {}, "distance": 0.2}
        ],
    )
    monkeypatch.setattr(
        "supportagent.agent.workflow.generate_answer",
        lambda *args, **kwargs: (
            "Der Begriff **„Schädigung“** ist in den freigegebenen Quellen nicht "
            "ausdrücklich definiert. Meinen Sie einen Schaden?"
        ),
    )

    result = answer_with_agent("Was bedeutet Schädigung?")

    assert result.evidence.status == "insufficient"
    assert result.evidence.reason == "Retrieved candidates did not support a reliable answer."


def test_agent_uses_rewritten_query_for_retrieval(monkeypatch):
    disable_mcp_tools(monkeypatch)
    captured = {}

    def fake_retrieve(question, source_filter=None):
        captured["question"] = question
        captured["source_filter"] = source_filter
        return [{"content": "fake chunk", "metadata": {}, "distance": 0.1}]

    def fake_generate_answer(question, chunks, short_history=None, long_memories=None, **kwargs):
        captured["answer_question"] = question
        return "fake answer"

    monkeypatch.setattr("supportagent.agent.workflow.retrieve", fake_retrieve)
    monkeypatch.setattr("supportagent.agent.workflow.generate_answer", fake_generate_answer)

    result = answer_with_agent("Was brauche ich nach einem Autounfall?")

    assert result.rewrite.changed is True
    assert "Kfz-Schadenmeldung" in captured["question"]
    assert "Verkehrsunfall" in captured["question"]
    assert captured["answer_question"] == "Was brauche ich nach einem Autounfall?"
