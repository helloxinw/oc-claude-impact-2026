"""Backend-shaped data models for the hybrid referral prototype.

These models intentionally mirror the naming and logic used in
backend/app/schemas.py and backend/app/models.py so the hybrid prototype can be
compared against the production app without drifting in structure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReferralStatus = Literal['new', 'needs_info', 'ready_for_review', 'accepted', 'closed']
AiDecision = Literal['yes', 'no', 'maybe']
DocumentStatus = Literal['uploaded', 'processing', 'processed', 'failed']
FindingCategory = Literal['extraction', 'eligibility_rule', 'missing_document', 'decision']
FindingVerdict = Literal['met', 'not_met', 'unclear', 'present', 'present_unclear', 'missing']


class ReferralDraft(BaseModel):
    patient_alias: str = Field(min_length=2, max_length=80)
    hospital_name: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=2, max_length=3000)


class ReferralSummary(BaseModel):
    id: str
    patient_alias: str
    hospital_name: str
    reason: str
    status: ReferralStatus = 'new'
    notes: str = ''
    ai_decision: AiDecision | None = None
    ai_decision_summary: str | None = None
    ai_processed_at: datetime | None = None
    coordinator_decision: AiDecision | None = None
    coordinator_decision_note: str | None = None
    coordinator_decision_at: datetime | None = None
    document_status: DocumentStatus | None = None
    document_filename: str | None = None
    document_page_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentRecord(BaseModel):
    id: str
    referral_id: str
    filename: str
    content_type: str = 'application/pdf'
    size_bytes: int = 0
    page_count: int | None = None
    status: DocumentStatus = 'uploaded'
    error_message: str | None = None
    uploaded_at: datetime | None = None


class FindingRecord(BaseModel):
    id: str
    document_id: str
    referral_id: str
    category: FindingCategory
    key: str
    value: str
    evidence: str | None = None
    rule_id: str | None = None
    source_page: int | None = None
    verdict: FindingVerdict | None = None
    needs_verification: bool = True
    verified: bool = False
    override_verdict: FindingVerdict | None = None
    coordinator_note: str | None = None
    bbox_x0: float | None = None
    bbox_y0: float | None = None
    bbox_x1: float | None = None
    bbox_y1: float | None = None
    created_at: datetime | None = None


class DecisionPayload(BaseModel):
    overall_decision: AiDecision
    overall_reasoning: str
    flags_for_human_review: list[dict[str, str]] = []
    missing_documents: list[dict[str, str]] = []
    rule_verdicts: list[dict[str, object]] = []
    confidence: Literal['low', 'medium', 'high'] = 'medium'
    disclaimer: str = 'Recommendation only. Human staff make the final admission decision.'
