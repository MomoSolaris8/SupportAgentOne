"""Confluence storage-format rendering for generated pages.

Deliberately uses the messy parts of real Confluence - structured macros, tables
and ``ac:link`` cross references - so the ingestion path is exercised against
markup it will actually meet, not against clean paragraphs.
"""

from __future__ import annotations

from html import escape

from .world import Fact, FactVariant


def para(text: str) -> str:
    return f"<p>{escape(text.strip())}</p>"


def heading(text: str, level: int = 2) -> str:
    return f"<h{level}>{escape(text.strip())}</h{level}>"


def bullets(items: list[str]) -> str:
    entries = "".join(f"<li>{escape(item.strip())}</li>" for item in items)
    return f"<ul>{entries}</ul>"


def info_macro(text: str, macro: str = "info") -> str:
    """A Confluence structured macro - common in real spaces, noisy to parse."""
    return (
        f'<ac:structured-macro ac:name="{macro}">'
        f"<ac:rich-text-body><p>{escape(text.strip())}</p></ac:rich-text-body>"
        f"</ac:structured-macro>"
    )


def page_link(title: str) -> str:
    return (
        f'<ac:link><ri:page ri:content-title="{escape(title)}" />'
        f"<ac:plain-text-link-body><![CDATA[{title}]]></ac:plain-text-link-body></ac:link>"
    )


def see_also(titles: list[str]) -> str:
    if not titles:
        return ""
    entries = "".join(f"<li>{page_link(title)}</li>" for title in titles)
    return heading("Siehe auch", 2) + f"<ul>{entries}</ul>"


def regulation_table(rows: list[tuple[str, str]]) -> str:
    """Two-column 'Merkmal / Regelung' table - the shape most product pages use."""
    header = "<tr><th>Merkmal</th><th>Regelung</th></tr>"
    body = "".join(
        f"<tr><td>{escape(attribute)}</td><td>{escape(value)}</td></tr>"
        for attribute, value in rows
    )
    return f"<table><tbody>{header}{body}</tbody></table>"


def fact_section(fact: Fact, variant: FactVariant) -> str:
    """Render one fact variant as its own section - this is its canonical statement."""
    parts = [heading(fact.attribute, 3), para(f"{fact.attribute}: {variant.value}.")]
    if variant.detail:
        parts.append(para(variant.detail))
    return "".join(parts)
