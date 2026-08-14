from supportagent.adf_utils import adf_to_text, text_to_adf


def test_text_to_adf_splits_paragraphs_on_blank_lines():
    adf = text_to_adf("First paragraph.\n\nSecond paragraph.")
    assert adf == {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "First paragraph."}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Second paragraph."}]},
        ],
    }


def test_text_to_adf_ignores_blank_paragraphs():
    adf = text_to_adf("First.\n\n\n\nSecond.")
    assert [p["content"][0]["text"] for p in adf["content"]] == ["First.", "Second."]


def test_adf_to_text_round_trip_for_paragraphs():
    text = "First paragraph.\n\nSecond paragraph."
    assert adf_to_text(text_to_adf(text)) == "First paragraph.\nSecond paragraph."


def test_adf_to_text_joins_heading_words_with_spaces():
    heading = {
        "type": "heading",
        "content": [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}],
    }
    assert adf_to_text(heading) == "Hello World"


def test_adf_to_text_handles_missing_content():
    assert adf_to_text(None) == ""
    assert adf_to_text({"type": "paragraph"}) == ""
