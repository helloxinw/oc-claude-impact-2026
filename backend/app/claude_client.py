"""Server-side Claude calls: read a scanned referral packet, then classify it against IHH's
admission criteria. Two separate tool-forced calls so the raw extraction can be shown to the
coordinator independently of the classification that was reasoned from it.

ANTHROPIC_API_KEY must be set in the backend's environment (see .env.example). It is never sent
to, or read by, the frontend.
"""
import json
import os
from pathlib import Path
from typing import Any

import anthropic

from app.pdf_extract import PageContent

MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-5-5')
MAX_TOKENS = 8000
CLASSIFY_MAX_TOKENS = 12000
CRITERIA_PATH = Path(__file__).resolve().parent / 'data' / 'admission_criteria.json'

_client: anthropic.Anthropic | None = None


class ClaudeNotConfiguredError(RuntimeError):
    pass


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ClaudeNotConfiguredError(
                'ANTHROPIC_API_KEY is not set. Add it to backend/.env (server-only).'
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def load_criteria() -> dict[str, Any]:
    return json.loads(CRITERIA_PATH.read_text(encoding='utf-8'))


def _checklist_text(criteria: dict[str, Any]) -> str:
    items = criteria['referral_checklist']['items']
    return '\n'.join(f"- {item['id']}: {item['text']}" for item in items)


LOW_CONFIDENCE_THRESHOLD = 60  # Tesseract's 0-100 mean word confidence


def _pages_to_text(pages: list[PageContent]) -> str:
    sections = []
    for page in pages:
        header = f'--- Page {page.page_number} ---'
        if page.mean_confidence is not None and page.mean_confidence < LOW_CONFIDENCE_THRESHOLD:
            header += f' (OCR confidence low: {page.mean_confidence:.0f}/100 — verify against the original scan)'
        body = page.text if page.text.strip() else '(blank or unreadable page)'
        sections.append(f'{header}\n{body}')
    return '\n\n'.join(sections)


EXTRACTION_TOOL = {
    'name': 'record_extraction',
    'description': 'Record the clinical and eligibility-relevant facts read from the referral packet.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'patient_summary': {
                'type': 'string',
                'description': 'A 2-4 sentence neutral clinical/situational summary. Do not invent an un-redacted '
                               'name or identifier; refer to "the patient".',
            },
            'fields': {
                'type': 'array',
                'description': 'Every discrete fact relevant to recuperative-care eligibility: diagnosis, housing '
                                'situation, ADLs, mobility/ambulation/DME use, mental health and cognition (AOx4, '
                                'suicidal ideation, hallucinations), behavior, substance use/detox compliance, '
                                'medication self-administration, infection control results (MRSA/COVID/TB), '
                                'isolation status, diabetes, cardiac, respiratory, wounds, sex-offender-registry '
                                'status, hospice, IV access/home health, vitals, and anything else a reviewer '
                                'checking the IHH admission criteria would need. One fact per entry.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'key': {'type': 'string', 'description': 'Short snake_case label, e.g. "ambulation_distance"'},
                        'value': {'type': 'string'},
                        'source_page': {'type': 'integer', 'description': 'Page number this was read from.'},
                        'confidence': {'type': 'string', 'enum': ['high', 'low']},
                    },
                    'required': ['key', 'value', 'confidence'],
                },
            },
            'documents_present': {
                'type': 'array',
                'description': 'One entry for every DOC-id in the referral checklist given in the prompt.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'doc_id': {'type': 'string'},
                        'present': {'type': 'boolean'},
                        'source_page': {'type': 'integer'},
                        'note': {'type': 'string'},
                    },
                    'required': ['doc_id', 'present'],
                },
            },
        },
        'required': ['patient_summary', 'fields', 'documents_present'],
    },
}


def extract_packet(pages: list[PageContent], criteria: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()
    instructions = (
        "Below is OCR text read from every page of a scanned hospital referral packet for "
        "Illumination Health + Home's recuperative care program. The OCR is imperfect — expect "
        "garbled words, and expect checkbox fill-state (whether a box was checked) to usually be "
        "lost entirely, since OCR only reads character shapes, not marks. Pages flagged with a low "
        "confidence score are more likely to contain OCR errors; treat facts read from them, and any "
        "yes/no value that depends on seeing which checkbox was marked, as confidence \"low\" unless "
        "the surrounding text makes the value unambiguous (e.g. a value is handwritten in a blank "
        "rather than a box was ticked). Any patient name, MRN, DOB, SSN or other direct identifier "
        "has already been redacted by the hospital — do not attempt to infer or reconstruct one.\n\n"
        "Call record_extraction once with every eligibility-relevant fact you find, each tied to the "
        "page you read it from. Then, for each of these checklist documents, say whether it appears "
        f"anywhere in the packet:\n{_checklist_text(criteria)}\n\n"
        f"OCR TEXT:\n{_pages_to_text(pages)}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[EXTRACTION_TOOL],
        tool_choice={'type': 'auto'},  # claude-sonnet-5-5 doesn't support forcing tool_choice
        messages=[{'role': 'user', 'content': instructions}],
    )
    return _tool_input(message, 'record_extraction')


CLASSIFICATION_TOOL = {
    'name': 'record_classification',
    'description': 'Record the eligibility decision for this referral against IHH admission criteria.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'rule_verdicts': {
                'type': 'array',
                'description': 'One entry per admission-criteria rule evaluated. Include every rule in '
                                '`general` and `rules`, every FORM-X4/FORM-X5 check, and any applicable '
                                '`by_system` entries — even ones where nothing was found (value_found null, '
                                'verdict "unclear").',
                'items': {
                    'type': 'object',
                    'properties': {
                        'rule_id': {'type': 'string'},
                        'value_found': {
                            'type': ['string', 'null'],
                            'description': 'The specific fact from the packet this verdict is based on, close to '
                                            'how it reads in the extracted data (e.g. "Ambulates 100+ ft with '
                                            'walker, modified independence, p.8"). Null if nothing relevant to '
                                            'this rule was found anywhere in the packet.',
                        },
                        'verdict': {'type': 'string', 'enum': ['met', 'not_met', 'unclear']},
                        'reasoning': {
                            'type': 'string',
                            'description': 'Why value_found does or does not satisfy this rule. If value_found is '
                                            'null, say so plainly (e.g. "Not documented anywhere in the packet").',
                        },
                        'evidence_page': {'type': 'integer'},
                    },
                    'required': ['rule_id', 'value_found', 'verdict', 'reasoning'],
                },
            },
            'missing_documents': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {'doc_id': {'type': 'string'}, 'reason': {'type': 'string'}},
                    'required': ['doc_id', 'reason'],
                },
            },
            'flags_for_human_review': {
                'type': 'array',
                'description': 'Case-by-case or judgment-call items (e.g. registered sex offender, '
                                'immediately post-neurosurgery) that must never be auto-decided.',
                'items': {
                    'type': 'object',
                    'properties': {'topic': {'type': 'string'}, 'reasoning': {'type': 'string'}},
                    'required': ['topic', 'reasoning'],
                },
            },
            'overall_decision': {'type': 'string', 'enum': ['yes', 'no', 'maybe']},
            'overall_reasoning': {
                'type': 'string',
                'description': 'A short paragraph a coordinator can read as-is, citing rule ids.',
            },
        },
        'required': ['rule_verdicts', 'missing_documents', 'flags_for_human_review', 'overall_decision', 'overall_reasoning'],
    },
}


def classify_referral(extraction: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()
    instructions = (
        "You are an eligibility-screening assistant for Illumination Health + Home's recuperative "
        "care program, helping (never replacing) a human referral coordinator. Below is the admission "
        "criteria outline (IHH's internal rulebook, which wins over the simplified hospital-facing "
        "referral form on any conflict) as JSON, followed by the facts extracted from this referral's "
        "packet.\n\n"
        "Precedence notes already settled, apply them silently: a registered sex offender is "
        "case-by-case (never an automatic denial) with violent offenses likely denied — put this "
        "in flags_for_human_review, not rule_verdicts, and do not let it alone drive overall_decision "
        "to \"no\"; a wheelchair-dependent patient who transfers and uses the chair independently "
        "satisfies mobility; tuberculosis and refusal of detox are exclusions from the referral form "
        "(FORM-X4, FORM-X5) even though this outline is silent on them — evaluate those two as "
        "ordinary exclude-type rule_verdicts alongside everything else.\n\n"
        "rule_verdicts must cover every rule in `general` and `rules`, FORM-X4 and FORM-X5, plus any "
        "applicable eligible/ineligible entries under `by_system` for the diagnoses mentioned — "
        "including rules where nothing relevant was found (value_found null, verdict \"unclear\", "
        "reasoning explains it wasn't documented). Never guess a fact that isn't in the extracted data. "
        "Compare documents_present against the checklist for missing_documents. overall_decision is "
        "\"no\" only when a must/exclude rule is clearly violated outside of a flagged case-by-case "
        "item; \"maybe\" when anything required is unclear, undocumented, or flagged for human review; "
        "\"yes\" only when every must rule is met, no exclusion applies, and nothing is flagged. Call "
        "record_classification once with your full reasoning.\n\n"
        f"ADMISSION CRITERIA JSON:\n{json.dumps(criteria)}\n\n"
        f"EXTRACTED FACTS:\n{json.dumps(extraction)}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=CLASSIFY_MAX_TOKENS,
        tools=[CLASSIFICATION_TOOL],
        tool_choice={'type': 'auto'},  # claude-sonnet-5-5 doesn't support forcing tool_choice
        messages=[{'role': 'user', 'content': instructions}],
    )
    return _tool_input(message, 'record_classification')


def _tool_input(message: anthropic.types.Message, tool_name: str) -> dict[str, Any]:
    for block in message.content:
        if block.type == 'tool_use' and block.name == tool_name:
            return block.input
    raise RuntimeError(f'Claude did not call {tool_name}; stop_reason={message.stop_reason}')
