from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReferralStatus = Literal['new', 'needs_info', 'ready_for_review', 'accepted', 'closed']
AiDecision = Literal['yes', 'no', 'maybe']
DocumentStatus = Literal['uploaded', 'processing', 'processed', 'failed']
FindingCategory = Literal['extraction', 'eligibility_rule', 'missing_document', 'decision']
FindingVerdict = Literal['met', 'not_met', 'unclear', 'present', 'missing']


class ReferralCreate(BaseModel):
    patient_alias: str = Field(min_length=2, max_length=80)
    hospital_name: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=2, max_length=3000)


class ReferralStatusUpdate(BaseModel):
    status: ReferralStatus


class ReferralDecisionUpdate(BaseModel):
    decision: AiDecision
    note: str = Field(default='', max_length=3000)


class ReferralRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_alias: str
    hospital_name: str
    reason: str
    status: ReferralStatus
    notes: str
    ai_decision: AiDecision | None
    ai_decision_summary: str | None
    ai_processed_at: datetime | None
    coordinator_decision: AiDecision | None
    coordinator_decision_note: str | None
    coordinator_decision_at: datetime | None
    document_status: DocumentStatus | None
    document_filename: str | None
    document_page_count: int | None
    created_at: datetime
    updated_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    referral_id: str
    filename: str
    content_type: str
    size_bytes: int
    page_count: int | None
    status: DocumentStatus
    error_message: str | None
    uploaded_at: datetime


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    referral_id: str
    category: FindingCategory
    key: str
    value: str
    evidence: str | None
    rule_id: str | None
    source_page: int | None
    verdict: FindingVerdict | None
    needs_verification: bool
    verified: bool
    override_verdict: FindingVerdict | None
    coordinator_note: str | None
    bbox_x0: float | None
    bbox_y0: float | None
    bbox_x1: float | None
    bbox_y1: float | None
    created_at: datetime


class FindingReviewUpdate(BaseModel):
    verified: bool
    override_verdict: FindingVerdict | None = None
    coordinator_note: str = Field(default='', max_length=3000)
