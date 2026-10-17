"""add repo.security

Revision ID: a1b2c3d4e5f6
Revises: 0c0231a8f34b
Create Date: 2026-10-17 11:40:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '0c0231a8f34b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('repos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('security', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('repos', schema=None) as batch_op:
        batch_op.drop_column('security')
