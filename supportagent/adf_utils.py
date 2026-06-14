from typing import Any


def text_to_adf(text: str) -> dict:
    """Wrap plain text (paragraphs separated by blank lines) into minimal ADF for Jira."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": paragraph}]}
            for paragraph in paragraphs
        ],
    }


def adf_to_text(node: Any) -> str:
    """Extract plain text from a Jira Atlassian Document Format (ADF) node."""
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")

    parts = [adf_to_text(child) for child in node.get("content", [])]
    parts = [part for part in parts if part]

    if node_type in {"paragraph", "heading", "listItem", "codeBlock"}:
        return " ".join(parts)
    return "\n".join(parts)
