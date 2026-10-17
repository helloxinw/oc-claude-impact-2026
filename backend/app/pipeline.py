"""Orchestrates one uploaded document through extraction, classification against the IHH
admission criteria, and persistence.

Kept separate from the router so the Claude-calling logic can be exercised by a standalone script
without spinning up FastAPI or a database.
"""
import difflib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.claude_client import classify_referral, extract_packet, load_criteria
from app.models import Document, Finding
from app.pdf_bookmarks import add_bookmarks, build_outline_entries
from app.pdf_extract import PageContent, extract_pages

logger = logging.getLogger(__name__)

# Below this line-text similarity, a quote is treated as unmatched rather than highlighting the
# wrong spot on the page (quotes are short and OCR is noisy, so this stays fairly forgiving).
QUOTE_MATCH_THRESHOLD = 0.6


def _match_bbox(pages_by_number: dict[int, PageContent], page_number: int | None, quote: str | None) -> tuple[float, float, float, float] | None:
    """Finds the OCR line on page_number that best matches quote (a short verbatim snippet Claude
    copied from that page's OCR text) and returns its bounding box, or None if nothing matches well
    enough to trust. Best-effort only: a missed match just means no highlight box, not an error."""
    if not page_number or not quote or not quote.strip():
        return None
    page = pages_by_number.get(page_number)
    if not page or not page.lines:
        return None
    quote_norm = quote.strip().lower()
    best_bbox = None
    best_score = 0.0
    for line in page.lines:
        line_norm = line.text.lower()
        score = difflib.SequenceMatcher(None, quote_norm, line_norm).ratio()
        if quote_norm in line_norm:
            score = max(score, 0.95)
        if score > best_score:
            best_score, best_bbox = score, line.bbox
    return best_bbox if best_score >= QUOTE_MATCH_THRESHOLD else None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _status_for_decision(decision: str) -> str:
    return {'yes': 'ready_for_review', 'no': 'ready_for_review', 'maybe': 'needs_info'}[decision]


def _build_extraction_findings(document: Document, extraction: dict[str, Any], pages_by_number: dict[int, PageContent]) -> list[Finding]:
    findings: list[Finding] = [Finding(
        id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
        category='extraction', key='patient_summary', value=extraction['patient_summary'],
        needs_verification=False,
    )]

    for field in extraction.get('fields', []):
        bbox = _match_bbox(pages_by_number, field.get('source_page'), field.get('quote'))
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='extraction', key=field['key'], value=field['value'],
            source_page=field.get('source_page'), verdict=None,
            needs_verification=field.get('confidence') == 'low',
            bbox_x0=bbox[0] if bbox else None, bbox_y0=bbox[1] if bbox else None,
            bbox_x1=bbox[2] if bbox else None, bbox_y1=bbox[3] if bbox else None,
        ))

    for doc in extraction.get('documents_present', []):
        present = doc['present']
        legible = doc.get('legible', True)
        if not present:
            verdict, category, default_note = 'missing', 'missing_document', 'Not found in packet'
        elif not legible:
            verdict, category, default_note = 'present_unclear', 'missing_document', 'In packet, but key information is redacted or illegible'
        else:
            verdict, category, default_note = 'present', 'extraction', 'Found in packet'
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category=category,
            key=f"document:{doc['doc_id']}", value=doc.get('note') or default_note,
            source_page=doc.get('source_page'), verdict=verdict,
            needs_verification=verdict != 'present',
        ))

    return findings


def _build_classification_findings(document: Document, classification: dict[str, Any], pages_by_number: dict[int, PageContent]) -> list[Finding]:
    findings: list[Finding] = []

    for rule in classification.get('rule_verdicts', []):
        bbox = _match_bbox(pages_by_number, rule.get('evidence_page'), rule.get('quote'))
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='eligibility_rule', key=rule['rule_id'], value=rule['reasoning'],
            evidence=rule.get('value_found'), rule_id=rule['rule_id'], source_page=rule.get('evidence_page'),
            verdict=rule['verdict'], needs_verification=rule['verdict'] in ('not_met', 'unclear'),
            bbox_x0=bbox[0] if bbox else None, bbox_y0=bbox[1] if bbox else None,
            bbox_x1=bbox[2] if bbox else None, bbox_y1=bbox[3] if bbox else None,
        ))

    for flag in classification.get('flags_for_human_review', []):
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='decision', key=f"flag:{flag['topic']}", value=flag['reasoning'],
            needs_verification=True,
        ))

    findings.append(Finding(
        id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
        category='decision', key='overall_decision', value=classification['overall_decision'],
        needs_verification=True,
    ))
    findings.append(Finding(
        id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
        category='decision', key='overall_reasoning', value=classification['overall_reasoning'],
        needs_verification=True,
    ))
    return findings


def process_document(db: Session, document: Document, file_bytes: bytes) -> None:
    document.status = 'processing'
    document.referral.document_status = 'processing'
    document.referral.document_filename = document.filename
    db.commit()

    try:
        pages = extract_pages(file_bytes)
        document.page_count = len(pages)
        pages_by_number = {p.page_number: p for p in pages}
        criteria = load_criteria()
        extraction = extract_packet(pages, criteria)
        classification = classify_referral(extraction, criteria)

        try:
            add_bookmarks(document.file_path, build_outline_entries(extraction, classification))
        except Exception:
            logger.exception('Failed to write PDF bookmarks for document %s; continuing without them.', document.id)

        db.add_all(_build_extraction_findings(document, extraction, pages_by_number))
        db.add_all(_build_classification_findings(document, classification, pages_by_number))
        document.status = 'processed'
        document.error_message = None

        referral = document.referral
        referral.ai_decision = classification['overall_decision']
        referral.ai_decision_summary = classification['overall_reasoning']
        referral.ai_processed_at = _utc_now()
        referral.status = _status_for_decision(classification['overall_decision'])
    except Exception as exc:
        document.status = 'failed'
        document.error_message = str(exc)[:2000]

    document.referral.document_status = document.status
    document.referral.document_page_count = document.page_count
    db.commit()
