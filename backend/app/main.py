import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.database import SessionLocal, engine
from app.models import Referral
from app.routers.referrals import router as referrals_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema migrations run explicitly via `alembic upgrade head` before startup.
    if os.environ.get('DEMO_SEED', 'true').lower() == 'true':
        with SessionLocal() as db:
            if db.scalar(select(Referral.id).limit(1)) is None:
                db.add_all([
                    Referral(patient_alias='Demo patient A', hospital_name='Example General Hospital',
                             reason='Recovery after wound treatment; mobility documentation needs clarification.',
                             status='needs_info', notes='Synthetic data only. Awaiting recent vitals and PT notes.'),
                    Referral(patient_alias='Demo patient B', hospital_name='Example Community Hospital',
                             reason='Medication management during recovery; packet ready for human review.',
                             status='ready_for_review', notes='Synthetic data only. No eligibility decision made.'),
                    Referral(patient_alias='Demo patient C', hospital_name='Example Medical Center',
                             reason='Post-discharge care and housing support; intake newly submitted.',
                             status='new', notes='Synthetic data only.'),
                ])
                db.commit()
    yield


app = FastAPI(title='ReferralFlow API', version='0.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['GET', 'POST', 'PATCH'],
    allow_headers=['Content-Type'],
)
app.include_router(referrals_router)


@app.get('/api/health', tags=['health'])
def health():
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'connected'}
