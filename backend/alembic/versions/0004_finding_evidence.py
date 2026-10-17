"""Add an evidence column to findings, separate from the match/mismatch reasoning in value.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('findings', sa.Column('evidence', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('findings', 'evidence')
