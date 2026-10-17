from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Referral
from app.schemas import ReferralCreate, ReferralDecisionUpdate, ReferralRead, ReferralStatusUpdate

router = APIRouter(prefix='/api/referrals', tags=['referrals'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('', response_model=list[ReferralRead])
def list_referrals(db: DbSession):
    return db.scalars(select(Referral).order_by(Referral.created_at.desc())).all()


@router.post('', response_model=ReferralRead, status_code=status.HTTP_201_CREATED)
def create_referral(payload: ReferralCreate, db: DbSession):
    referral = Referral(**payload.model_dump())
    db.add(referral)
    db.commit()
    db.refresh(referral)
    return referral


@router.get('/{referral_id}', response_model=ReferralRead)
def get_referral(referral_id: str, db: DbSession):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')
    return referral


@router.patch('/{referral_id}', response_model=ReferralRead)
def update_status(referral_id: str, payload: ReferralStatusUpdate, db: DbSession):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')
    referral.status = payload.status
    db.commit()
    db.refresh(referral)
    return referral


@router.patch('/{referral_id}/decision', response_model=ReferralRead)
def update_coordinator_decision(referral_id: str, payload: ReferralDecisionUpdate, db: DbSession):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')
    referral.coordinator_decision = payload.decision
    referral.coordinator_decision_note = payload.note
    referral.coordinator_decision_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(referral)
    return referral
