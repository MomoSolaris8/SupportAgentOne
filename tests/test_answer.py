from supportagent.core.answer import REFUSAL_TEXT, generate_answer


def test_generate_answer_refuses_when_no_chunks_are_retrieved():
    assert generate_answer("Was ist versichert?", []) == REFUSAL_TEXT


def test_generate_answer_uses_image_context_without_chunks(monkeypatch):
    captured = {}

    class FakeMessage:
        content = "Das Bild zeigt einen sichtbaren Schaden. Fuer Deckungsfragen fehlen Quellen."

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("supportagent.core.answer.OpenAI", lambda **kwargs: FakeClient())

    answer = generate_answer(
        "Was siehst du?",
        [],
        image_contexts=["Image id: img-1\nObservation: Sichtbarer Fahrzeugschaden."],
    )

    assert "sichtbaren Schaden" in answer
    assert "Sichtbarer Fahrzeugschaden" in captured["messages"][1]["content"]
    assert "keine verlaesslichen Wissensquellen" in captured["messages"][0]["content"]


def test_generate_answer_includes_image_context(monkeypatch):
    captured = {}

    class FakeMessage:
        content = "answer"

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("supportagent.core.answer.OpenAI", lambda **kwargs: FakeClient())

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
    prompt = captured["messages"][1]["content"]
    assert "Sichtbarer Fahrzeugschaden" in prompt
    assert "Bildbeobachtungen duerfen fuer sichtbare Bildinhalte verwendet werden" in prompt


def test_generate_answer_prefers_image_path_for_image_question(monkeypatch):
    captured = {}

    class FakeMessage:
        content = "Das Bild zeigt einen sichtbaren Fahrzeugschaden."

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("supportagent.core.answer.OpenAI", lambda **kwargs: FakeClient())

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
    assert "keine verlaesslichen Wissensquellen" in captured["messages"][0]["content"]
    assert "Quellen:" not in captured["messages"][1]["content"]
