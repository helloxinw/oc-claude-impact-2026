from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Finding, Referral
from app.pipeline import process_document
from app.schemas import DocumentRead, FindingRead, FindingReviewUpdate

router = APIRouter(prefix='/api/referrals', tags=['documents'])
findings_router = APIRouter(prefix='/api/findings', tags=['findings'])
DbSession = Annotated[Session, Depends(get_db)]

STORAGE_DIR = Path(__file__).resolve().parents[2] / 'storage'
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post('/{referral_id}/documents', response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(referral_id: str, db: DbSession, file: Annotated[UploadFile, File()]):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')

    if file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail='Only PDF files are accepted.')

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail='The uploaded file is empty.')
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f'File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.')

    document_id = str(uuid4())
    referral_dir = STORAGE_DIR / referral_id
    referral_dir.mkdir(parents=True, exist_ok=True)
    file_path = referral_dir / f'{document_id}.pdf'
    file_path.write_bytes(contents)

    document = Document(
        id=document_id, referral_id=referral_id, filename=file.filename or 'referral.pdf',
        file_path=str(file_path), content_type=file.content_type, size_bytes=len(contents),
        status='uploaded',
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    process_document(db, document, contents)
    db.refresh(document)
    return document


@router.get('/{referral_id}/documents', response_model=list[DocumentRead])
def list_documents(referral_id: str, db: DbSession):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')
    return db.scalars(
        select(Document).where(Document.referral_id == referral_id).order_by(Document.uploaded_at.desc())
    ).all()


@router.get('/{referral_id}/documents/{document_id}/file')
def get_document_file(referral_id: str, document_id: str, db: DbSession):
    document = db.get(Document, document_id)
    if document is None or document.referral_id != referral_id:
        raise HTTPException(status_code=404, detail='Document not found')
    path = Path(document.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail='Stored file is missing')
    return FileResponse(path, media_type='application/pdf', filename=document.filename, content_disposition_type='inline')


@router.get('/{referral_id}/findings', response_model=list[FindingRead])
def list_findings(referral_id: str, db: DbSession):
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail='Referral not found')
    return db.scalars(select(Finding).where(Finding.referral_id == referral_id).order_by(Finding.created_at)).all()


@findings_router.patch('/{finding_id}', response_model=FindingRead)
def review_finding(finding_id: str, payload: FindingReviewUpdate, db: DbSession):
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail='Finding not found')
    finding.verified = payload.verified
    finding.override_verdict = payload.override_verdict
    finding.coordinator_note = payload.coordinator_note
    db.commit()
    db.refresh(finding)
    return finding
