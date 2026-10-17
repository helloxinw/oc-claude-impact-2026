from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReferralStatus = Literal['new', 'needs_info', 'ready_for_review', 'accepted', 'closed']


class ReferralCreate(BaseModel):
    patient_alias: str = Field(min_length=2, max_length=80)
    hospital_name: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=2, max_length=3000)


class ReferralStatusUpdate(BaseModel):
    status: ReferralStatus


class ReferralRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_alias: str
    hospital_name: str
    reason: str
    status: ReferralStatus
    notes: str
    created_at: datetime
    updated_at: datetime
