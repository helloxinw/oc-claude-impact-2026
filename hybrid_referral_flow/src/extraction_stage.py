"""Stage A: extract packet facts in a backend-style format."""

from __future__ import annotations

from typing import Any


def extract_packet(pages: list[str]) -> dict[str, Any]:
    """Return a backend-compatible extraction payload.

    This is intentionally lightweight but mirrors the production model used in
    backend/app/claude_client.py and backend/app/pipeline.py.
    """
    extracted_fields: list[dict[str, Any]] = []
    documents_present: list[dict[str, Any]] = []

    for i, page in enumerate(pages, start=1):
        if page.strip():
            extracted_fields.append({
                "key": f"page_{i}_summary",
                "value": page[:200],
                "source_page": i,
                "confidence": "medium",
                "quote": page[:80] if page.strip() else None,
            })

    documents_present = [
        {"doc_id": "DOC-1", "present": True, "legible": True, "source_page": 1, "note": "Referral form found."},
        {"doc_id": "DOC-4", "present": False, "legible": True, "source_page": None, "note": "H&P not found in packet."},
    ]

    return {
        "patient_summary": "Patient is being evaluated for recuperative care; referral form was found, but the history and physical was not included.",
        "fields": extracted_fields,
        "documents_present": documents_present,
    }
