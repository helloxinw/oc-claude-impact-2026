"""Add a bounding box to findings, so the packet viewer can highlight exactly where a fact or
rule verdict was read from instead of just scrolling to the page.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('findings', sa.Column('bbox_x0', sa.Float(), nullable=True))
    op.add_column('findings', sa.Column('bbox_y0', sa.Float(), nullable=True))
    op.add_column('findings', sa.Column('bbox_x1', sa.Float(), nullable=True))
    op.add_column('findings', sa.Column('bbox_y1', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('findings', 'bbox_y1')
    op.drop_column('findings', 'bbox_x1')
    op.drop_column('findings', 'bbox_y0')
    op.drop_column('findings', 'bbox_x0')
