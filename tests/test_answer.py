from supportagent.core.answer import (
    REFUSAL_TEXT,
    answer_reports_insufficient_evidence,
    enforce_answer_contract,
    generate_answer,
)
from supportagent.llm import ChatCompletion


def test_generate_answer_refuses_when_no_chunks_are_retrieved():
    assert generate_answer("Was ist versichert?", []) == REFUSAL_TEXT


def test_answer_contract_removes_content_mixed_with_refusal():
    answer = (
        "Der Begriff **Schädigung** bezeichnet allgemein einen Schaden.\n\n"
        f"{REFUSAL_TEXT}"
    )

    assert enforce_answer_contract(answer) == REFUSAL_TEXT


def test_answer_contract_preserves_grounded_markdown():
    answer = "**Haftpflichtversicherung**: Deckt bestimmte Schäden [1]."

    assert enforce_answer_contract(answer) == answer


def test_terminology_gap_reports_insufficient_evidence():
    answer = (
        "Der Begriff **„Schädigung“** ist in den freigegebenen Quellen nicht "
        "ausdrücklich definiert. Meinen Sie einen Schaden?"
    )

    assert answer_reports_insufficient_evidence(answer) is True
    assert answer_reports_insufficient_evidence(
        "Die **Selbstbeteiligung** ist ein vertraglich vereinbarter Anteil [1]."
    ) is False


def test_generate_answer_uses_image_context_without_chunks(monkeypatch):
    captured = {}

    def fake_complete_chat(messages, **kwargs):
        captured["messages"] = messages
        captured.update(kwargs)
        return ChatCompletion(
            content="Das Bild zeigt einen sichtbaren Schaden. Fuer Deckungsfragen fehlen Quellen.",
            model_id="qwen-plus",
            provider="qwen",
        )

    monkeypatch.setattr("supportagent.core.answer.complete_chat", fake_complete_chat)

    answer = generate_answer(
        "Was siehst du?",
        [],
        image_contexts=["Image id: img-1\nObservation: Sichtbarer Fahrzeugschaden."],
    )

    assert "sichtbaren Schaden" in answer
    assert "Sichtbarer Fahrzeugschaden" in captured["messages"][-1]["content"]
    assert "keine verlässlichen Wissensquellen" in captured["messages"][0]["content"]


def test_generate_answer_includes_image_context(monkeypatch):
    captured = {}

    def fake_complete_chat(messages, **kwargs):
        captured["messages"] = messages
        captured.update(kwargs)
        return ChatCompletion(
            content="answer",
            model_id="qwen-plus",
            provider="qwen",
        )

    monkeypatch.setattr("supportagent.core.answer.complete_chat", fake_complete_chat)

    answer = generate_answer(
        "Welche Unterlagen brauche ich fuer eine Schadenmeldung?",
        [
            {
                "content": "Schadenmeldungen benoetigen Fotos des Schadens.",
                "metadata": {"source": "confluence", "title": "Schadenmeldung"},
            }
        ],
        image_contexts=["Image id: img-1\nObservation: Sichtbarer Fahrzeugschaden."],
    )

    assert answer == "answer"
    prompt = captured["messages"][-1]["content"]
    assert "Sichtbarer Fahrzeugschaden" in prompt
    assert "Bildbeobachtungen duerfen fuer sichtbare Bildinhalte verwendet werden" in prompt
    assert len(captured["messages"]) == 8
    assert captured["messages"][0]["role"] == "system"
    assert [message["role"] for message in captured["messages"][1:7]] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert captured["messages"][-1]["role"] == "user"


def test_generate_answer_prefers_image_path_for_image_question(monkeypatch):
    captured = {}

    def fake_complete_chat(messages, **kwargs):
        captured["messages"] = messages
        captured.update(kwargs)
        return ChatCompletion(
            content="Das Bild zeigt einen sichtbaren Fahrzeugschaden.",
            model_id="qwen-plus",
            provider="qwen",
        )

    monkeypatch.setattr("supportagent.core.answer.complete_chat", fake_complete_chat)

    answer = generate_answer(
        "Was siehst du auf dem Bild?",
        [
            {
                "content": "Schadenmeldungen benoetigen Fotos des Schadens.",
                "metadata": {"source": "confluence", "title": "Schadenmeldung"},
            }
        ],
        image_contexts=["Image id: img-1\nObservation: Sichtbarer Fahrzeugschaden."],
    )

    assert "Fahrzeugschaden" in answer
    assert "keine verlässlichen Wissensquellen" in captured["messages"][0]["content"]
    assert "Quellen:" not in captured["messages"][-1]["content"]
