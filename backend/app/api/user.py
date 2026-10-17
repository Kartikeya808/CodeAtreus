"""User settings endpoints (Phase 4.5): profile, API keys, usage, danger zone."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.repos import teardown_repo_artifacts
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    ApiKeysOut,
    ApiKeysUpdate,
    MonthlyUsage,
    ProfileOut,
    ProfileUpdate,
    UsageOut,
)
from app.services import crypto, usage

router = APIRouter()


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)) -> ProfileOut:
    return ProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        avatar_url=user.avatar_url,
        github_login=user.github_login,
        github_connected=bool(user.github_access_token),
        plan=user.plan,
    )


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_profile(user)


@router.get("/api-keys", response_model=ApiKeysOut)
def get_api_keys(user: User = Depends(get_current_user)) -> ApiKeysOut:
    """Return masked previews only — raw keys are never exposed."""
    openrouter = crypto.decrypt(user.openrouter_api_key)
    github = crypto.decrypt(user.github_access_token)
    return ApiKeysOut(
        openrouter_key=crypto.mask(openrouter, visible=6),
        github_token=crypto.mask(github),
        openrouter_set=bool(openrouter),
        github_set=bool(github),
    )


@router.put("/api-keys", response_model=ApiKeysOut)
def update_api_keys(
    body: ApiKeysUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeysOut:
    # None = unchanged; "" = clear; otherwise set (encrypted at rest).
    if body.openrouter_key is not None:
        user.openrouter_api_key = (
            crypto.encrypt(body.openrouter_key) if body.openrouter_key else None
        )
    if body.github_token is not None:
        user.github_access_token = (
            crypto.encrypt(body.github_token) if body.github_token else None
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_api_keys(user)


@router.get("/usage", response_model=UsageOut)
def get_usage(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UsageOut:
    return UsageOut(
        repos_indexed=usage.repos_indexed(db, user.id),
        questions_asked=usage.questions_asked(db, user.id),
        tokens_used=usage.tokens_used(db, user.id),
        plan=user.plan,
        token_budget=usage.token_budget(user.plan),
        monthly=[MonthlyUsage(**m) for m in usage.monthly_series(db, user.id)],
    )


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def reset_data(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """Delete all of the user's repos (and their artifacts), keep the account."""
    for repo in list(user.repos):
        teardown_repo_artifacts(repo)
        db.delete(repo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_account(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """Permanently delete the account and all associated data."""
    for repo in list(user.repos):
        teardown_repo_artifacts(repo)
    db.delete(user)  # cascades to repos / sessions / messages / roadmaps
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
