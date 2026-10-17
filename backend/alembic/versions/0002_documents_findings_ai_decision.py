"""Add document uploads, extracted findings, and the referral's AI decision summary.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('referrals', sa.Column('ai_decision', sa.String(length=10), nullable=True))
    op.add_column('referrals', sa.Column('ai_decision_summary', sa.Text(), nullable=True))
    op.add_column('referrals', sa.Column('ai_processed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('referral_id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['referral_id'], ['referrals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_referral_id'), 'documents', ['referral_id'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    op.create_table(
        'findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('referral_id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('key', sa.String(length=160), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('rule_id', sa.String(length=20), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('verdict', sa.String(length=20), nullable=True),
        sa.Column('needs_verification', sa.Boolean(), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['referral_id'], ['referrals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_findings_document_id'), 'findings', ['document_id'], unique=False)
    op.create_index(op.f('ix_findings_referral_id'), 'findings', ['referral_id'], unique=False)
    op.create_index(op.f('ix_findings_category'), 'findings', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_findings_category'), table_name='findings')
    op.drop_index(op.f('ix_findings_referral_id'), table_name='findings')
    op.drop_index(op.f('ix_findings_document_id'), table_name='findings')
    op.drop_table('findings')

    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_referral_id'), table_name='documents')
    op.drop_table('documents')

    op.drop_column('referrals', 'ai_processed_at')
    op.drop_column('referrals', 'ai_decision_summary')
    op.drop_column('referrals', 'ai_decision')
