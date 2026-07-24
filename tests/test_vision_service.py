from supportagent.vision.service import analyze_image, summarize_image
from supportagent.llm import ChatCompletion


def test_summarize_image_returns_fallback_without_vision_model(monkeypatch):
    monkeypatch.delenv("VISION_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_BASE_URL", raising=False)

    summary = summarize_image(b"fake-image", "image/png", "damage.png")

    assert "damage.png" in summary
    assert "kein Vision-Modell konfiguriert" in summary


def test_analyze_image_parses_structured_vision_response(monkeypatch):
    def fake_complete_chat(messages, **kwargs):
        return ChatCompletion(
            content="""
        {
          "ocr_text": "Rechnung Nr. 42",
          "visible_objects": ["Dokument", "Totalsumme"],
          "dates": ["15.07.2026"],
          "amounts": ["123,45 EUR"],
          "names": ["ACME Versicherung"],
          "insurance_relevant_facts": ["Es ist eine Rechnung sichtbar."],
          "limitations": "Ein Bereich ist unscharf."
        }
        """,
            model_id="qwen-vl-plus",
            provider="qwen",
        )

    monkeypatch.setenv("VISION_MODEL", "qwen-vl-plus")
    monkeypatch.setattr("supportagent.vision.service.complete_chat", fake_complete_chat)

    analysis = analyze_image(b"fake-image", "image/png", "invoice.png")

    assert analysis.ocr_text == "Rechnung Nr. 42"
    assert analysis.amounts == ["123,45 EUR"]
    assert "Rechnung" in analysis.summary("invoice.png")


def test_analyze_image_keeps_non_json_response_as_fact(monkeypatch):
    def fake_complete_chat(messages, **kwargs):
        return ChatCompletion(
            content="Das Bild zeigt einen sichtbaren Schaden.",
            model_id="qwen-vl-plus",
            provider="qwen",
        )

    monkeypatch.setenv("VISION_MODEL", "qwen-vl-plus")
    monkeypatch.setattr("supportagent.vision.service.complete_chat", fake_complete_chat)

    analysis = analyze_image(b"fake-image", "image/png", "damage.png")

    assert analysis.insurance_relevant_facts == ["Das Bild zeigt einen sichtbaren Schaden."]
    assert "keine gueltige JSON-Struktur" in analysis.limitations
