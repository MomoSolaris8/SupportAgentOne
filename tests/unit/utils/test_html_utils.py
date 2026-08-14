from supportagent.html_utils import html_to_text


def test_heading_sections_are_separated_by_blank_line():
    html = "<h2>Section A</h2><p>Text A.</p><h2>Section B</h2><p>Text B.</p>"
    assert html_to_text(html) == "Section A\nText A.\n\nSection B\nText B."


def test_list_items_are_on_separate_lines():
    html = "<p>Intro</p><ul><li>One</li><li>Two</li></ul>"
    assert html_to_text(html) == "Intro\nOne\nTwo"


def test_whitespace_is_collapsed():
    html = "<p>Some   text   with   extra   spaces</p>"
    assert html_to_text(html) == "Some text with extra spaces"
