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
from app.criteria import UNSCORED_KINDS, always_applicable_rule_ids, condition_groups, rule_index
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


def _bbox_columns(bbox: tuple[float, float, float, float] | None) -> dict[str, float | None]:
    return {
        'bbox_x0': bbox[0] if bbox else None, 'bbox_y0': bbox[1] if bbox else None,
        'bbox_x1': bbox[2] if bbox else None, 'bbox_y1': bbox[3] if bbox else None,
    }


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
            needs_verification=field.get('confidence') == 'low', **_bbox_columns(bbox),
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


# Verdicts a coordinator still has to act on. not_applicable and answered questions don't.
VERDICTS_NEEDING_VERIFICATION = ('not_met', 'unclear', 'pending_arrangement', 'unanswered')


def reconcile_classification(classification: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """Checks Claude's classification against the criteria index and repairs what it can, in place:
    `ask` rules scored as pass/fail are moved to question_answers, `note` rules are dropped from the
    verdicts, and every always-applicable rule Claude skipped gets an "unclear" placeholder (plus a
    human-review flag, and a "yes" is downgraded to "maybe"). Scoping mismatches between
    patient_conditions and the verdicts are logged, since code can't re-diagnose the patient."""
    index = rule_index(criteria)
    known_groups = set(condition_groups(criteria))
    declared = {c['group'] for c in classification.get('patient_conditions', [])}
    for group in declared - known_groups:
        logger.warning('Classifier declared unknown condition group %r', group)

    verdicts: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = list(classification.get('question_answers', []))
    answered_ids = {a['rule_id'] for a in answers}
    for verdict in classification.get('rule_verdicts', []):
        rule = index.get(verdict['rule_id'])
        if rule is None:
            logger.warning('Classifier returned a verdict for unknown rule id %r', verdict['rule_id'])
        elif rule.kind == 'ask':
            if rule.id not in answered_ids:
                answers.append({
                    'rule_id': rule.id, 'answer': verdict.get('value_found'),
                    'evidence_page': verdict.get('evidence_page'), 'quote': verdict.get('quote'),
                })
                answered_ids.add(rule.id)
            continue
        elif rule.kind == 'note':
            continue
        elif rule.group is not None and rule.group not in declared:
            logger.warning('Classifier evaluated %s (%s) but did not list %s in patient_conditions', rule.id, rule.group, rule.group)
        verdicts.append(verdict)

    evaluated = {v['rule_id'] for v in verdicts}
    missing = [rule_id for rule_id in always_applicable_rule_ids(index) if rule_id not in evaluated]
    if missing:
        logger.warning('Classifier skipped always-applicable rules: %s', ', '.join(missing))
        verdicts.extend({
            'rule_id': rule_id, 'value_found': None, 'verdict': 'unclear',
            'reasoning': 'Not evaluated by the AI screen; check this rule against the packet manually.',
        } for rule_id in missing)
        classification.setdefault('flags_for_human_review', []).append({
            'topic': 'Criteria the AI did not evaluate',
            'reasoning': f"The AI screen returned no verdict for {', '.join(missing)}; review these manually.",
        })
        if classification['overall_decision'] == 'yes':
            classification['overall_decision'] = 'maybe'

    for group in declared & known_groups:
        group_rules = [r for r in index.values() if r.group == group]
        # by_system groups only need verdicts for the listed conditions that match the patient.
        required = [r.id for r in group_rules if r.kind not in UNSCORED_KINDS and not r.by_system]
        skipped = [rule_id for rule_id in required if rule_id not in evaluated]
        skipped += [r.id for r in group_rules if r.kind == 'ask' and r.id not in answered_ids]
        if group_rules[0].by_system and not any(r.id in evaluated for r in group_rules):
            skipped.append(f'any {group} entry')
        if skipped:
            logger.warning('Classifier listed %s in patient_conditions but skipped: %s', group, ', '.join(skipped))

    classification['rule_verdicts'] = verdicts
    classification['question_answers'] = answers
    return classification


def _build_classification_findings(document: Document, classification: dict[str, Any], criteria: dict[str, Any], pages_by_number: dict[int, PageContent]) -> list[Finding]:
    findings: list[Finding] = []
    index = rule_index(criteria)

    for rule in classification.get('rule_verdicts', []):
        bbox = _match_bbox(pages_by_number, rule.get('evidence_page'), rule.get('quote'))
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='eligibility_rule', key=rule['rule_id'], value=rule['reasoning'],
            evidence=rule.get('value_found'), rule_id=rule['rule_id'], source_page=rule.get('evidence_page'),
            verdict=rule['verdict'], needs_verification=rule['verdict'] in VERDICTS_NEEDING_VERIFICATION,
            **_bbox_columns(bbox),
        ))

    # `ask` items: the question itself goes in `value` and the packet's answer in `evidence`, with
    # answered/unanswered in place of a pass/fail verdict.
    for answer in classification.get('question_answers', []):
        rule = index.get(answer['rule_id'])
        bbox = _match_bbox(pages_by_number, answer.get('evidence_page'), answer.get('quote'))
        verdict = 'answered' if answer.get('answer') else 'unanswered'
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='eligibility_rule', key=answer['rule_id'], value=rule.text if rule else answer['rule_id'],
            evidence=answer.get('answer'), rule_id=answer['rule_id'], source_page=answer.get('evidence_page'),
            verdict=verdict, needs_verification=verdict in VERDICTS_NEEDING_VERIFICATION,
            **_bbox_columns(bbox),
        ))

    # Which condition groups the diagnosis-specific rules were screened for, so the coordinator can
    # spot one the AI missed.
    for condition in classification.get('patient_conditions', []):
        findings.append(Finding(
            id=str(uuid4()), document_id=document.id, referral_id=document.referral_id,
            category='decision', key=f"condition:{condition['group']}", value=condition['diagnosis'],
            needs_verification=False,
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
        classification = reconcile_classification(classify_referral(extraction, criteria), criteria)

        try:
            add_bookmarks(document.file_path, build_outline_entries(extraction, classification))
        except Exception:
            logger.exception('Failed to write PDF bookmarks for document %s; continuing without them.', document.id)

        db.add_all(_build_extraction_findings(document, extraction, pages_by_number))
        db.add_all(_build_classification_findings(document, classification, criteria, pages_by_number))
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
