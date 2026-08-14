from supportagent.core.models import Document
from supportagent.rag.chunking import chunk_document


def _confluence_doc(text: str) -> Document:
    return Document(text=text, metadata={"source": "confluence", "source_id": "page-1"})


def _jira_doc(text: str) -> Document:
    return Document(text=text, metadata={"source": "jira", "source_id": "issue-1"})


def test_confluence_page_is_split_per_section_with_title_prefix():
    doc = _confluence_doc("Page Title\n\nSection A\nText A.\n\nSection B\nText B.")

    chunks = chunk_document(doc)

    assert [c["content"] for c in chunks] == [
        "Page Title\n\nSection A\nText A.",
        "Page Title\n\nSection B\nText B.",
    ]
    assert [c["chunk_index"] for c in chunks] == [0, 1]
    assert all(c["document_id"] == "page-1" for c in chunks)
    assert all(c["metadata"] == doc.metadata for c in chunks)


def test_confluence_page_without_sections_is_a_single_chunk():
    doc = _confluence_doc("Page Title")

    chunks = chunk_document(doc)

    assert chunks == [
        {
            "document_id": "page-1",
            "chunk_index": 0,
            "content": "Page Title",
            "metadata": doc.metadata,
        }
    ]


def test_jira_issue_is_kept_as_a_single_chunk():
    doc = _jira_doc("Summary\n\nDescription\n\nComment")

    chunks = chunk_document(doc)

    assert chunks == [
        {
            "document_id": "issue-1",
            "chunk_index": 0,
            "content": "Summary\n\nDescription\n\nComment",
            "metadata": doc.metadata,
        }
    ]
