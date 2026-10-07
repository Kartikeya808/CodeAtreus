"""SQLAlchemy ORM models.

Importing this package registers every model on ``Base.metadata`` so that
Alembic autogenerate and ``Base.metadata.create_all`` see the full schema.
"""
from app.models.base import Base
from app.models.chat import ChatMessage, ChatSession
from app.models.index_job import IndexJob, IndexStatus
from app.models.repo import Repo, RepoStatus
from app.models.roadmap import Roadmap
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Repo",
    "RepoStatus",
    "IndexJob",
    "IndexStatus",
    "ChatSession",
    "ChatMessage",
    "Roadmap",
]
