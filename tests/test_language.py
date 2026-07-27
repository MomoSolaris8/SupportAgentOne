import pytest

from supportagent.core.language import detect_response_language, response_language_name


@pytest.mark.parametrize(
    ("question", "language", "name"),
    [
        ("Wie spät ist es in Zürich?", "de", "German"),
        ("What time is it in Zurich?", "en", "English"),
        ("苏黎世现在几点了？", "zh", "Chinese"),
    ],
)
def test_detects_supported_response_languages(question, language, name):
    assert detect_response_language(question) == language
    assert response_language_name(question) == name
