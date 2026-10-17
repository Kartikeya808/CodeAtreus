"""add llm_cache table + repo.indexed_commit_sha

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-17 12:10:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2c3d4e5f6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('repos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('indexed_commit_sha', sa.String(length=40), nullable=True))

    op.create_table(
        'llm_cache',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cache_key', sa.String(length=64), nullable=False),
        sa.Column('repo_id', sa.String(length=36), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('files', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_cache_cache_key', 'llm_cache', ['cache_key'], unique=True)
    op.create_index('ix_llm_cache_repo_id', 'llm_cache', ['repo_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_llm_cache_repo_id', table_name='llm_cache')
    op.drop_index('ix_llm_cache_cache_key', table_name='llm_cache')
    op.drop_table('llm_cache')
    with op.batch_alter_table('repos', schema=None) as batch_op:
        batch_op.drop_column('indexed_commit_sha')
