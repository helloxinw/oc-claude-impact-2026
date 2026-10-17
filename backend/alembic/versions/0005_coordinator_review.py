"""Add coordinator review fields: per-rule override/note, and the referral's own final decision.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('referrals', sa.Column('coordinator_decision', sa.String(length=10), nullable=True))
    op.add_column('referrals', sa.Column('coordinator_decision_note', sa.Text(), nullable=True))
    op.add_column('referrals', sa.Column('coordinator_decision_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('findings', sa.Column('override_verdict', sa.String(length=20), nullable=True))
    op.add_column('findings', sa.Column('coordinator_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('findings', 'coordinator_note')
    op.drop_column('findings', 'override_verdict')

    op.drop_column('referrals', 'coordinator_decision_at')
    op.drop_column('referrals', 'coordinator_decision_note')
    op.drop_column('referrals', 'coordinator_decision')
