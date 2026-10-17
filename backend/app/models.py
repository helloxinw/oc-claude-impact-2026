from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Referral(Base):
    __tablename__ = 'referrals'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_alias: Mapped[str] = mapped_column(String(80), nullable=False)
    hospital_name: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='new', index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    # Advisory AI read of the IHH admission criteria. Never a final decision: the workflow status
    # above always requires a human coordinator to accept/close a case.
    ai_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ai_decision_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The coordinator's own final call, recorded separately from the AI draft above. Never set
    # automatically; the workflow `status` field still drives the operational queue.
    coordinator_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    coordinator_decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    coordinator_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Denormalized snapshot of the most recently uploaded document, so the queue list can show
    # packet status without an N+1 query per row. Mirrors Document.status/page_count/filename.
    document_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    document_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    documents: Mapped[list['Document']] = relationship(back_populates='referral', cascade='all, delete-orphan')
    findings: Mapped[list['Finding']] = relationship(back_populates='referral', cascade='all, delete-orphan')


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    referral_id: Mapped[str] = mapped_column(String(36), ForeignKey('referrals.id'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Processing lifecycle for the upload -> extract -> classify pipeline.
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='uploaded', index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    referral: Mapped['Referral'] = relationship(back_populates='documents')
    findings: Mapped[list['Finding']] = relationship(back_populates='document', cascade='all, delete-orphan')


class Finding(Base):
    __tablename__ = 'findings'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey('documents.id'), nullable=False, index=True)
    referral_id: Mapped[str] = mapped_column(String(36), ForeignKey('referrals.id'), nullable=False, index=True)
    # 'extraction' (a fact read off the packet), 'eligibility_rule' (a verdict against one IHH
    # admission-criteria rule), 'missing_document' (a checklist item not found in the packet), or
    # 'decision' (the single overall yes/no/maybe finding plus its reasoning).
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    # For category='eligibility_rule': the specific fact read from the packet that the verdict is
    # based on (null when nothing relevant was found). `value` holds the match/mismatch reasoning.
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Admission-criteria rule id this finding is about, e.g. 'MOB-3' (see backend/app/data/admission_criteria.json).
    rule_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'met' | 'not_met' | 'unclear' | 'present' | 'present_unclear' | 'missing', depending on category.
    # 'present_unclear': the checklist document is in the packet but its key content is redacted/illegible
    # (different from 'missing', where the document was never sent). Null for free-text findings.
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    needs_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # The coordinator's own verdict for this rule, when it differs from (or confirms past) the AI's
    # `verdict` above. `verdict` is never overwritten, so the AI's original read stays auditable.
    override_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    coordinator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Where on source_page this was found, as a fraction (0-1) of the page image, so the frontend can
    # draw a highlight box over the exact text rather than just scrolling to the page. Null when no
    # verbatim OCR quote could be matched back to a line on the page.
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    document: Mapped['Document'] = relationship(back_populates='findings')
    referral: Mapped['Referral'] = relationship(back_populates='findings')
