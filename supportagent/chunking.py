from .models import Document


def chunk_document(doc: Document) -> list[dict]:
    """Split a Document into retrievable chunks.

    Confluence pages are split per heading section (title + one H2 section
    each), per architecture proposal 6.2. Jira issues are kept as a single
    issue-level chunk, since summary/description/comments are short and
    context-dependent.
    """
    if doc.metadata["source"] != "confluence":
        return [_make_chunk(doc, 0, doc.text)]

    title, *sections = doc.text.split("\n\n")
    if not sections:
        return [_make_chunk(doc, 0, doc.text)]

    return [
        _make_chunk(doc, index, f"{title}\n\n{section.strip()}")
        for index, section in enumerate(sections)
    ]


def _make_chunk(doc: Document, chunk_index: int, content: str) -> dict:
    return {
        "document_id": doc.metadata["source_id"],
        "chunk_index": chunk_index,
        "content": content,
        "metadata": doc.metadata,
    }
