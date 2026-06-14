"""Extract sections from a German insurance terms PDF (Musterbedingungen/AVB)
and turn them into Confluence page drafts ({title, labels, body}).

Typical workflow:

1. Dry run to see how the PDF splits into sections:
     python -m supportagent.pdf_to_confluence path/to/bedingungen.pdf

2. Once the split looks reasonable, save as draft pages:
     python -m supportagent.pdf_to_confluence path/to/bedingungen.pdf \\
         --labels hausrat,produkt --out data/confluence_pages_from_pdf.json

3. Open data/confluence_pages_from_pdf.json, clean up titles/text by hand
   (PDF extraction is messy: line breaks, headers/footers, hyphenation).

4. Run `python -m supportagent.seed` - it picks up
   data/confluence_pages_from_pdf.json automatically if present.
"""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

# Matches German Bedingungen section headings like "§ 1 Versicherte Sachen"
SECTION_PATTERN = re.compile(r"^§\s*(\d+[a-z]?)\s+(.+)$")


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def split_into_sections(text: str) -> list[dict]:
    sections: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = SECTION_PATTERN.match(line)
        if match:
            if current_title:
                sections.append({"title": current_title, "lines": current_lines})
            current_title = f"§ {match.group(1)} {match.group(2)}"
            current_lines = []
        elif current_title:
            if line:
                current_lines.append(line)

    if current_title:
        sections.append({"title": current_title, "lines": current_lines})

    return sections


def section_to_page(section: dict, labels: list[str], project: str | None) -> dict:
    body = "".join(f"<p>{line}</p>" for line in section["lines"])
    page = {"title": section["title"], "labels": labels, "body": body}
    if project:
        page["project"] = project
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--labels", default="", help="comma-separated labels, e.g. hausrat,produkt")
    parser.add_argument(
        "--project",
        default=None,
        help="project key to nest these pages under, e.g. privatkunden, kfz, schadenbearbeitung (see seed_content.PROJECTS)",
    )
    parser.add_argument("--out", type=Path, default=None, help="JSON file to write (appends if it exists)")
    args = parser.parse_args()

    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    sections = split_into_sections(extract_text(args.pdf_path))
    pages = [section_to_page(section, labels, args.project) for section in sections]

    if not args.out:
        for page in pages:
            preview = re.sub(r"<[^>]+>", " ", page["body"]).strip()
            print(f"=== {page['title']} ===")
            print(preview[:300])
            print()
        print(f"{len(pages)} sections found.")
        print("If this split looks right, re-run with --labels and --out to save as JSON.")
        return

    existing = json.loads(args.out.read_text()) if args.out.exists() else []
    existing.extend(pages)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    print(f"Wrote {len(pages)} pages to {args.out} (total now {len(existing)})")


if __name__ == "__main__":
    main()
