"""Writes real PDF bookmarks (an outline) into the stored packet, generated from what extraction
and classification found on each page. Scanned fax packets never carry their own outline, so any
PDF viewer with an outline/bookmarks panel (Chrome's built-in viewer included) shows nothing for
them by default; this gives the coordinator that navigation for free, even if they open the file
outside our app.
"""
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

MAX_LABEL_ITEMS = 4


def _page_labels(extraction: dict[str, Any], classification: dict[str, Any]) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}

    def add(page: int | None, label: str) -> None:
        if page:
            pages.setdefault(page, [])
            if label not in pages[page]:
                pages[page].append(label)

    for field in extraction.get('fields', []):
        add(field.get('source_page'), field['key'].replace('_', ' '))

    for doc in extraction.get('documents_present', []):
        if doc.get('present'):
            add(doc.get('source_page'), doc['doc_id'])

    for rule in classification.get('rule_verdicts', []):
        add(rule.get('evidence_page'), rule['rule_id'])

    return pages


def build_outline_entries(extraction: dict[str, Any], classification: dict[str, Any]) -> list[tuple[int, str]]:
    """Returns (1-indexed page number, bookmark title) pairs, one per page with any finding on it."""
    pages = _page_labels(extraction, classification)
    entries = []
    for page in sorted(pages):
        labels = pages[page]
        shown = ', '.join(labels[:MAX_LABEL_ITEMS])
        if len(labels) > MAX_LABEL_ITEMS:
            shown += f' (+{len(labels) - MAX_LABEL_ITEMS} more)'
        entries.append((page, f'p.{page} — {shown}'))
    return entries


def add_bookmarks(pdf_path: str, entries: list[tuple[int, str]]) -> None:
    """Rewrites the PDF at pdf_path in place with an outline built from entries. No-op if entries
    is empty. Raises on failure; callers should treat this as a best-effort enhancement."""
    if not entries:
        return
    path = Path(pdf_path)
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.append(reader)
    for page_number, title in entries:
        if 1 <= page_number <= len(reader.pages):
            writer.add_outline_item(title, page_number - 1)

    tmp_path = path.with_suffix('.tmp.pdf')
    with open(tmp_path, 'wb') as f:
        writer.write(f)
    tmp_path.replace(path)
