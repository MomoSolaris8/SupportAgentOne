from supportagent.vision.service import analyze_image, summarize_image


def test_summarize_image_returns_fallback_without_vision_model(monkeypatch):
    monkeypatch.delenv("VISION_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_BASE_URL", raising=False)

    summary = summarize_image(b"fake-image", "image/png", "damage.png")

    assert "damage.png" in summary
    assert "kein Vision-Modell konfiguriert" in summary


def test_analyze_image_parses_structured_vision_response(monkeypatch):
    class FakeMessage:
        content = """
        {
          "ocr_text": "Rechnung Nr. 42",
          "visible_objects": ["Dokument", "Totalsumme"],
          "dates": ["15.07.2026"],
          "amounts": ["123,45 EUR"],
          "names": ["ACME Versicherung"],
          "insurance_relevant_facts": ["Es ist eine Rechnung sichtbar."],
          "limitations": "Ein Bereich ist unscharf."
        }
        """

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("VISION_MODEL", "qwen-vl-plus")
    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("supportagent.vision.service.OpenAI", lambda **kwargs: FakeClient())

    analysis = analyze_image(b"fake-image", "image/png", "invoice.png")

    assert analysis.ocr_text == "Rechnung Nr. 42"
    assert analysis.amounts == ["123,45 EUR"]
    assert "Rechnung" in analysis.summary("invoice.png")


def test_analyze_image_keeps_non_json_response_as_fact(monkeypatch):
    class FakeMessage:
        content = "Das Bild zeigt einen sichtbaren Schaden."

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setenv("VISION_MODEL", "qwen-vl-plus")
    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("supportagent.vision.service.OpenAI", lambda **kwargs: FakeClient())

    analysis = analyze_image(b"fake-image", "image/png", "damage.png")

    assert analysis.insurance_relevant_facts == ["Das Bild zeigt einen sichtbaren Schaden."]
    assert "keine gueltige JSON-Struktur" in analysis.limitations
