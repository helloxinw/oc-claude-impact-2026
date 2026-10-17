"""Create the synthetic referral queue.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'referrals',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_alias', sa.String(length=80), nullable=False),
        sa.Column('hospital_name', sa.String(length=120), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_referrals_status'), 'referrals', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_referrals_status'), table_name='referrals')
    op.drop_table('referrals')
