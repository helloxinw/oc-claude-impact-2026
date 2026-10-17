"""Add a denormalized packet-status summary to referrals for the queue list.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('referrals', sa.Column('document_status', sa.String(length=32), nullable=True))
    op.add_column('referrals', sa.Column('document_filename', sa.String(length=255), nullable=True))
    op.add_column('referrals', sa.Column('document_page_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('referrals', 'document_page_count')
    op.drop_column('referrals', 'document_filename')
    op.drop_column('referrals', 'document_status')
