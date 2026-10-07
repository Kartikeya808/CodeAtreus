"""GitHub repository URL validation (SSRF guard) + metadata lookup."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

# Only HTTPS github.com URLs of the form github.com/<owner>/<repo>[.git].
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)"
    r"(?:\.git)?/?$"
)


class InvalidRepoURL(ValueError):
    """Raised when a URL is not an acceptable public github.com repo URL."""


@dataclass
class RepoRef:
    owner: str
    repo: str
    full_name: str
    clone_url: str


def validate_github_url(url: str) -> RepoRef:
    """Validate + normalise a GitHub repo URL, guarding against SSRF.

    Rejects non-github hosts, IP literals, userinfo, ports and anything that
    isn't a plain ``https://github.com/owner/repo`` reference.
    """
    url = url.strip()
    m = _GITHUB_URL_RE.match(url)
    if not m:
        raise InvalidRepoURL(
            "Only public https://github.com/<owner>/<repo> URLs are accepted"
        )
    owner, repo = m.group("owner"), m.group("repo")
    repo = repo[:-4] if repo.endswith(".git") else repo
    full_name = f"{owner}/{repo}"
    return RepoRef(
        owner=owner,
        repo=repo,
        full_name=full_name,
        clone_url=f"https://github.com/{full_name}.git",
    )


@dataclass
class RepoMeta:
    default_branch: str
    description: str | None
    stars: int
    size_kb: int
    private: bool


async def fetch_repo_meta(ref: RepoRef, token: str | None = None) -> RepoMeta:
    """Look up repo metadata (default branch, stars, size) via the GitHub API.

    Falls back to sensible defaults if the API is unavailable or unauthenticated
    rate limits are hit — import must not hard-fail on a metadata miss.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    api_url = f"https://api.github.com/repos/{ref.full_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(api_url, headers=headers)
        if resp.status_code == 404:
            raise InvalidRepoURL(f"Repository {ref.full_name} not found or is private")
        resp.raise_for_status()
        data = resp.json()
        return RepoMeta(
            default_branch=data.get("default_branch", "main"),
            description=data.get("description"),
            stars=data.get("stargazers_count", 0),
            size_kb=data.get("size", 0),
            private=data.get("private", False),
        )
    except httpx.HTTPError:
        return RepoMeta(default_branch="main", description=None, stars=0, size_kb=0, private=False)
