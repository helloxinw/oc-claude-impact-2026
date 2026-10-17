"""Orchestrates one uploaded document through extraction, classification against the IHH
admission criteria, and persistence.

Kept separate from the router so the Claude-calling logic can be exercised by a standalone script
without spinning up FastAPI or a database.
"""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.claude_client import classify_referral, extract_packet, load_criteria
from app.models import Document, Finding
from app.pdf_bookmarks import add_bookmarks, build_outline_entries
from app.pdf_extract import extract_pages

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _status_for_decision(decision: str) -> str:
    return {'yes': 'ready_for_review', 'no': 'ready_for_review', 'maybe': 'needs_info'}[decision]


def _build_extraction_findings(document: Document, extraction: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = [Finding(
        id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
        category='extraction', key='patient_summary', value=extraction['patient_summary'],
        needs_verification=False,
    )]

    for field in extraction.get('fields', []):
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='extraction', key=field['key'], value=field['value'],
            source_page=field.get('source_page'), verdict=None,
            needs_verification=field.get('confidence') == 'low',
        ))

    for doc in extraction.get('documents_present', []):
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='missing_document' if not doc['present'] else 'extraction',
            key=f"document:{doc['doc_id']}", value=doc.get('note') or ('Found in packet' if doc['present'] else 'Not found in packet'),
            source_page=doc.get('source_page'), verdict='present' if doc['present'] else 'missing',
            needs_verification=not doc['present'],
        ))

    return findings


def _build_classification_findings(document: Document, classification: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for rule in classification.get('rule_verdicts', []):
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='eligibility_rule', key=rule['rule_id'], value=rule['reasoning'],
            evidence=rule.get('value_found'), rule_id=rule['rule_id'], source_page=rule.get('evidence_page'),
            verdict=rule['verdict'], needs_verification=rule['verdict'] in ('not_met', 'unclear'),
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
        criteria = load_criteria()
        extraction = extract_packet(pages, criteria)
        classification = classify_referral(extraction, criteria)

        try:
            add_bookmarks(document.file_path, build_outline_entries(extraction, classification))
        except Exception:
            logger.exception('Failed to write PDF bookmarks for document %s; continuing without them.', document.id)

        db.add_all(_build_extraction_findings(document, extraction))
        db.add_all(_build_classification_findings(document, classification))
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
