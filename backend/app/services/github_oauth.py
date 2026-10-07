"""GitHub OAuth: exchange the authorization code for a token + fetch the user."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class GithubOAuthError(RuntimeError):
    """Raised when the OAuth exchange with GitHub fails."""


@dataclass
class GithubProfile:
    github_id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str | None
    access_token: str


async def exchange_code_for_profile(code: str, redirect_uri: str | None = None) -> GithubProfile:
    """Exchange an OAuth `code` for an access token, then load the user profile."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise GithubOAuthError("GitHub OAuth is not configured (missing client id/secret)")

    async with httpx.AsyncClient(timeout=15.0) as http:
        token_resp = await http.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri or settings.github_oauth_redirect_uri,
            },
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise GithubOAuthError(
                f"GitHub token exchange failed: {token_data.get('error_description') or token_data}"
            )

        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        user_resp = await http.get(GITHUB_USER_URL, headers=auth_headers)
        user_resp.raise_for_status()
        user = user_resp.json()

        email = user.get("email")
        if not email:
            # Primary email may be private; fetch from the emails endpoint.
            emails_resp = await http.get(GITHUB_EMAILS_URL, headers=auth_headers)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                email = primary or (emails[0]["email"] if emails else None)

    return GithubProfile(
        github_id=user["id"],
        login=user["login"],
        name=user.get("name"),
        email=email,
        avatar_url=user.get("avatar_url"),
        access_token=access_token,
    )
