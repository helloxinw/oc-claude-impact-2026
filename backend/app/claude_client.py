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

from app.criteria import UNSCORED_KINDS, RuleInfo, always_applicable_rule_ids, condition_groups, rule_index
from app.pdf_extract import PageContent

MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-5-5')
MAX_TOKENS = 8000
CLASSIFY_MAX_TOKENS = 16000
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
                        'quote': {
                            'type': ['string', 'null'],
                            'description': 'A short run of words (3-12) copied VERBATIM from the OCR text on '
                                            'source_page that this fact was read from — exactly as it '
                                            'appears there, garbled OCR and all, not paraphrased. Used to locate '
                                            'and highlight it on the page image. Null if there is no single '
                                            'supporting snippet (e.g. a fact inferred from absence of a field).',
                        },
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
                        'legible': {
                            'type': 'boolean',
                            'description': 'Only meaningful when present is true. False if the document itself '
                                            'is in the packet but its key content is blacked out/redacted, '
                                            'illegible, or otherwise unusable (e.g. a lab report page is there '
                                            'but the result value is covered). This is a different problem from '
                                            'the document never being sent — do not conflate the two. True (or '
                                            'omit) if present and its content can actually be read.',
                        },
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
        "anywhere in the packet (present), and if it does, whether its key content is actually legible "
        "(legible) — a document that's physically there but whose critical values are blacked out, "
        "covered, or otherwise unreadable is present=true, legible=false, NOT the same as the document "
        "never being sent (present=false). Those are different problems for the coordinator and must "
        f"not be conflated:\n{_checklist_text(criteria)}\n\n"
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
        # Field order here is also roughly the order Claude tends to generate them in. The two
        # scalar decision fields are listed first and kept short so they land safely inside the
        # token budget even if the (much longer) rule_verdicts array ends up truncated.
        'properties': {
            'overall_decision': {'type': 'string', 'enum': ['yes', 'no', 'maybe']},
            'overall_reasoning': {
                'type': 'string',
                'description': 'A short paragraph (3-5 sentences) a coordinator can read as-is, citing rule ids.',
            },
            'flags_for_human_review': {
                'type': 'array',
                'description': 'Case-by-case or judgment-call items (e.g. registered sex offender, '
                                'immediately post-neurosurgery) that must never be auto-decided. One sentence each.',
                'items': {
                    'type': 'object',
                    'properties': {'topic': {'type': 'string'}, 'reasoning': {'type': 'string'}},
                    'required': ['topic', 'reasoning'],
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
            'patient_conditions': {
                'type': 'array',
                'description': 'Every condition group (from the list in the prompt) that this patient’s '
                                'documented diagnoses fall under. This decides which diagnosis-specific rules '
                                'and questions get evaluated, so list a group only if the patient actually has '
                                'a condition in it, and do not leave out one they do have.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'group': {'type': 'string', 'description': 'Exactly one of the condition group names given in the prompt.'},
                        'diagnosis': {'type': 'string', 'description': 'The diagnosis from the packet that puts the patient in this group, as a short phrase.'},
                    },
                    'required': ['group', 'diagnosis'],
                },
            },
            'rule_verdicts': {
                'type': 'array',
                'description': 'One entry per pass/fail rule evaluated: every always-applicable rule id listed in '
                                'the prompt, plus the rules of each group in patient_conditions as the prompt '
                                'describes. Never include `ask` or `note` rules here. Keep value_found and '
                                'reasoning to one short sentence each (a phrase is fine) so the full list fits '
                                'the response budget.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'rule_id': {'type': 'string'},
                        'value_found': {
                            'type': ['string', 'null'],
                            'description': 'One short phrase/sentence: the specific fact from the packet this '
                                            'verdict is based on (e.g. "Ambulates 100+ ft with walker, modified '
                                            'independence, p.8"). Null if nothing relevant was found.',
                        },
                        'verdict': {
                            'type': 'string',
                            'enum': ['met', 'not_met', 'unclear', 'not_applicable', 'pending_arrangement'],
                            'description': 'Always read as "is the patient OK on this rule", per the kind '
                                            'mapping in the prompt. not_applicable: the rule’s own trigger or '
                                            'condition does not hold for this patient. pending_arrangement: '
                                            'conditional rules only — the trigger is present but the required '
                                            'arrangement is not yet confirmed in the packet.',
                        },
                        'reasoning': {
                            'type': 'string',
                            'description': 'One short sentence: why value_found does or does not satisfy this '
                                            'rule. If value_found is null, say so plainly and briefly.',
                        },
                        'evidence_page': {'type': 'integer'},
                        'quote': {
                            'type': ['string', 'null'],
                            'description': 'A short run of words (3-12) copied VERBATIM from the OCR text on '
                                            'evidence_page that this verdict is based on — exactly as it '
                                            'appears there, garbled OCR and all, not paraphrased. Used to locate '
                                            'and highlight it on the page image. Null if value_found is null.',
                        },
                    },
                    'required': ['rule_id', 'value_found', 'verdict', 'reasoning'],
                },
            },
            'question_answers': {
                'type': 'array',
                'description': 'One entry per `ask` rule in each group listed in patient_conditions. These are '
                                'questions IHH wants answered, never pass/fail: record what the packet says, '
                                'or null if it does not answer the question.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'rule_id': {'type': 'string'},
                        'answer': {
                            'type': ['string', 'null'],
                            'description': 'One short phrase answering the question from the packet. Null if the packet does not say.',
                        },
                        'evidence_page': {'type': 'integer'},
                        'quote': {
                            'type': ['string', 'null'],
                            'description': 'A short verbatim OCR snippet (3-12 words) from evidence_page, as for rule_verdicts. Null if answer is null.',
                        },
                    },
                    'required': ['rule_id', 'answer'],
                },
            },
        },
        'required': [
            'overall_decision', 'overall_reasoning', 'flags_for_human_review', 'missing_documents',
            'patient_conditions', 'rule_verdicts', 'question_answers',
        ],
    },
}


def _condition_groups_text(criteria: dict[str, Any], index: dict[str, RuleInfo]) -> str:
    lines = []
    for group in condition_groups(criteria):
        rules = [r for r in index.values() if r.group == group]
        scored = ', '.join(r.id for r in rules if r.kind not in UNSCORED_KINDS)
        questions = ', '.join(r.id for r in rules if r.kind == 'ask')
        kind = 'by_system condition list' if rules and rules[0].by_system else 'rules section'
        lines.append(f'- {group} ({kind}): {scored}' + (f'; questions: {questions}' if questions else ''))
    return '\n'.join(lines)


def classify_referral(extraction: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()
    index = rule_index(criteria)
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
        "WHICH RULES TO COVER. These apply to every patient regardless of diagnosis; each must get a "
        "rule_verdicts entry even where nothing relevant was found (value_found null, verdict "
        "\"unclear\" if the rule applies but the packet doesn't settle it):\n"
        f"{', '.join(always_applicable_rule_ids(index))}\n"
        "Then identify the patient's diagnosed condition(s) from the extracted facts and record each "
        "matching condition group in patient_conditions. The condition groups and their rule ids are:\n"
        f"{_condition_groups_text(criteria, index)}\n"
        "For each group in patient_conditions: a \"rules section\" group gets a rule_verdicts entry for "
        "every one of its rules (not_applicable where a rule's own condition doesn't hold), plus a "
        "question_answers entry for every one of its questions. A \"by_system condition list\" group "
        "lists specific conditions, so give verdicts only for the entries that match or could match "
        "this patient's condition(s); leave out entries about conditions the patient plainly doesn't "
        "have. Leave every group not in patient_conditions out entirely — no verdicts, no answers. "
        "Never guess a fact that isn't in the extracted data.\n\n"
        "HOW EACH KIND MAPS TO A VERDICT. A verdict always reads \"is the patient OK on this rule\":\n"
        "- must: met / not_met / unclear. not_applicable only when the rule opens with a condition "
        "that doesn't hold for this patient (e.g. MOB-4 for a patient who isn't wheelchair dependent, "
        "MH-4 when not admitted with acute alcohol intoxication, CARD-4 with no atrial fibrillation).\n"
        "- exclude: met = checked and the exclusion does not apply; not_met = the exclusion applies; "
        "unclear = the packet doesn't say.\n"
        "- document: met = sent in the packet; not_met = not sent; not_applicable when the rule's own "
        "condition doesn't hold (e.g. \"if coming from inpatient\" for an ED referral, \"if patient had "
        "a troponin\" when none was drawn).\n"
        "- conditional (allowed only if an arrangement is confirmed before admission — OTH-3, EOL-1, "
        "DM-4, ID-3, RESP-3, and the by_system entries marked conditional): not_applicable when the "
        "triggering situation isn't present (no IV access/IV medication, not a hospice patient, no "
        "oxygen requirement, not an ED referral of a poorly controlled diabetic). Treat a trigger as "
        "absent when the packet says so, or when it would be documented (orders, medication list, "
        "lines, nursing notes) and appears nowhere; use unclear only when the packet hints it might be "
        "present but is ambiguous. pending_arrangement when the trigger IS present but the arrangement "
        "(home health, hospice services, PCP follow-up and glucose plan, oxygen tank, wound care, PT, "
        "etc.) isn't confirmed in the packet. met when the trigger is present and the arrangement is "
        "confirmed. not_met only when the packet shows the arrangement can't or won't happen.\n"
        "- ask: never a verdict. Answer it in question_answers instead.\n"
        "- note: never a verdict; a human_review note goes in flags_for_human_review when it applies.\n"
        "- general (GEN-1..3) is any-of: the patient needs at least one met. Evaluate each honestly; "
        "once one is met the others don't affect overall_decision.\n"
        "- by_system eligible entries (no kind of their own): met if the patient's condition fits; "
        "unclear if it might. Eligible entries marked conditional follow the conditional mapping. "
        "by_system ineligible entries are exclusions for that specific condition: not_met if the "
        "patient has it, unclear if they might, not_applicable if they plainly don't.\n\n"
        "OVERALL DECISION. Compare documents_present against the checklist for missing_documents. "
        "overall_decision is \"no\" only when a must rule is clearly not_met or an exclusion clearly "
        "applies, outside of a flagged case-by-case item. Otherwise \"maybe\" if any must/exclude/"
        "document/general rule is unclear, any document is not sent, any conditional rule is "
        "pending_arrangement (the arrangement must be confirmed before admission), any checklist "
        "document is missing, or anything is flagged for human review. Otherwise \"yes\". "
        "not_applicable verdicts and question_answers (answered or not) never move overall_decision "
        "in either direction — a rule that doesn't apply, or a question the packet leaves open, is "
        "not a reason for \"maybe\".\n\n"
        "Keep every rule_verdicts and question_answers entry brief (a short phrase for value_found/"
        "answer, one short sentence for reasoning; a few words is enough for not_applicable) — the full "
        "list must fit in the response. Call record_classification once with your full reasoning.\n\n"
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
    if message.stop_reason == 'max_tokens':
        raise RuntimeError(
            f'Claude\'s {tool_name} response was cut off at the max_tokens limit before it finished, so it '
            'cannot be used. Try again, or raise the relevant *_MAX_TOKENS constant in claude_client.py.'
        )
    for block in message.content:
        if block.type == 'tool_use' and block.name == tool_name:
            return block.input
    raise RuntimeError(f'Claude did not call {tool_name}; stop_reason={message.stop_reason}')
