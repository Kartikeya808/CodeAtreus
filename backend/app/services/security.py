"""Security insights (Phase 4.2): secret scanning + dependency vulnerabilities.

Secret scan: regex rules + Shannon-entropy heuristic over the repo's source
files (reusing the indexing walk). Dependency vulns: parse package manifests and
query the free OSV.dev batch API. Every external call degrades gracefully to an
empty result so the endpoint never hard-fails (mirrors the LLM fallback style).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.core.logging import get_logger
from app.services.indexing.walk import walk_repo

logger = get_logger("security")

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns"

MAX_SECRETS = 100
MAX_VULN_DETAILS = 40

# ── Secret detection rules ────────────────────────────────────────────────────
# name -> (compiled regex, severity). The first capture group (if any) is the
# sensitive span used to build the masked preview.
_SECRET_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("AWS Access Key ID", re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "high"),
    ("AWS Secret Access Key",
     re.compile(r"""aws_secret_access_key\s*[=:]\s*['"]?([A-Za-z0-9/+=]{40})['"]?""", re.I), "high"),
    ("GitHub Token", re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,})\b"), "high"),
    ("Slack Token", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b"), "high"),
    ("Google API Key", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b"), "high"),
    ("OpenAI/OpenRouter Key", re.compile(r"\b(sk-(?:or-)?[A-Za-z0-9_\-]{20,})\b"), "high"),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "high"),
    ("Generic Secret Assignment",
     re.compile(r"""(?:password|passwd|secret|api_?key|token|access_?key)\s*[=:]\s*['"]([^'"\s]{8,})['"]""", re.I),
     "medium"),
]

# Suffixes we skip for secret scanning — docs/examples produce mostly noise.
_SKIP_SECRET_SUFFIXES = (".md", ".mdx", ".rst", ".txt", ".csv", ".json", ".lock")


@dataclass
class Package:
    name: str
    version: str
    ecosystem: str  # OSV ecosystem: PyPI, npm, Go, Maven


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _mask(value: str, visible: int = 4) -> str:
    if len(value) <= visible * 2:
        return value[:2] + "•" * 4
    return f"{value[:visible]}…{value[-visible:]}"


# ── Secret scanning ───────────────────────────────────────────────────────────
_HIGH_ENTROPY_RE = re.compile(r"""['"]([A-Za-z0-9+/=_\-]{24,64})['"]""")


def scan_secrets(root: Path) -> list[dict]:
    findings: list[dict] = []
    walk = walk_repo(root)
    for sf in walk.files:
        if sf.rel_path.lower().endswith(_SKIP_SECRET_SUFFIXES):
            continue
        try:
            text = sf.abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if len(line) > 500:  # minified / data lines — skip
                continue
            matched_rule = False
            for name, pattern, severity in _SECRET_RULES:
                m = pattern.search(line)
                if not m:
                    continue
                matched_rule = True
                secret = m.group(1) if m.groups() else m.group(0)
                findings.append({
                    "file": sf.rel_path,
                    "line": lineno,
                    "rule": name,
                    "severity": severity,
                    "preview": _mask(secret),
                })
                break
            # Entropy heuristic for anything the rules missed.
            if not matched_rule:
                for hm in _HIGH_ENTROPY_RE.finditer(line):
                    candidate = hm.group(1)
                    if _shannon_entropy(candidate) >= 4.0:
                        findings.append({
                            "file": sf.rel_path,
                            "line": lineno,
                            "rule": "High-entropy string",
                            "severity": "low",
                            "preview": _mask(candidate),
                        })
                        break
            if len(findings) >= MAX_SECRETS:
                return findings
    return findings


# ── Dependency manifest parsing ───────────────────────────────────────────────
_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([A-Za-z0-9_.\-]+)")
_GOMOD_RE = re.compile(r"^\s*([\w./\-]+)\s+v([0-9][\w.\-]*)")


def _parse_requirements(path: Path) -> list[Package]:
    out: list[Package] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("#"):
            continue
        m = _REQ_RE.match(line)
        if m:
            out.append(Package(m.group(1), m.group(2), "PyPI"))
    return out


def _parse_package_lock(path: Path) -> list[Package]:
    out: list[Package] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return out
    # npm lockfile v2/v3: "packages" keyed by "node_modules/<name>".
    for key, meta in (data.get("packages") or {}).items():
        if not key.startswith("node_modules/"):
            continue
        name = key.split("node_modules/")[-1]
        version = (meta or {}).get("version")
        if name and version:
            out.append(Package(name, version, "npm"))
    # v1 fallback: flat "dependencies".
    if not out:
        for name, meta in (data.get("dependencies") or {}).items():
            version = (meta or {}).get("version")
            if version:
                out.append(Package(name, version, "npm"))
    return out


def _parse_go_mod(path: Path) -> list[Package]:
    out: list[Package] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith(("module ", "go ", "//")) or line in ("require (", ")"):
            continue
        m = _GOMOD_RE.match(line.replace("require ", ""))
        if m:
            out.append(Package(m.group(1), m.group(2), "Go"))
    return out


def parse_dependencies(root: Path) -> list[Package]:
    """Best-effort dependency extraction from common manifests."""
    packages: list[Package] = []
    parsers = [
        ("requirements.txt", _parse_requirements),
        ("package-lock.json", _parse_package_lock),
        ("go.mod", _parse_go_mod),
    ]
    for filename, parser in parsers:
        path = root / filename
        if path.exists():
            try:
                packages.extend(parser(path))
            except Exception as exc:  # noqa: BLE001 - never let one manifest break the scan
                logger.info("dependency parse failed for %s: %s", filename, exc)
    # De-dupe on (name, version, ecosystem).
    seen: set[tuple[str, str, str]] = set()
    unique: list[Package] = []
    for p in packages:
        key = (p.name, p.version, p.ecosystem)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


async def query_vulnerabilities(packages: list[Package]) -> list[dict]:
    """Query OSV.dev for vulns affecting the given packages. [] on any failure."""
    if not packages:
        return []
    queries = [
        {"package": {"name": p.name, "ecosystem": p.ecosystem}, "version": p.version}
        for p in packages
    ]
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.post(OSV_BATCH_URL, json={"queries": queries})
            resp.raise_for_status()
            results = resp.json().get("results", [])

            # Collect (package, vuln_id) pairs, capped.
            pairs: list[tuple[Package, str]] = []
            for pkg, result in zip(packages, results, strict=False):
                for vuln in (result.get("vulns") or []):
                    pairs.append((pkg, vuln["id"]))
            pairs = pairs[:MAX_VULN_DETAILS]

            out: list[dict] = []
            for pkg, vuln_id in pairs:
                detail = await _fetch_vuln_detail(http, vuln_id)
                out.append({
                    "package": pkg.name,
                    "version": pkg.version,
                    "ecosystem": pkg.ecosystem,
                    "id": vuln_id,
                    "severity": detail.get("severity", "unknown"),
                    "summary": detail.get("summary", vuln_id),
                    "fixed_in": detail.get("fixed_in"),
                })
            return out
    except Exception as exc:  # noqa: BLE001 - offline / rate-limited → no vulns
        logger.info("OSV query failed: %s", exc)
        return []


async def _fetch_vuln_detail(http: httpx.AsyncClient, vuln_id: str) -> dict:
    try:
        resp = await http.get(f"{OSV_VULN_URL}/{vuln_id}")
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001
        return {}
    # OSV severity lives under database_specific or severity[].
    severity = "unknown"
    db = data.get("database_specific") or {}
    if isinstance(db.get("severity"), str):
        severity = db["severity"].lower()
    elif data.get("severity"):
        severity = "scored"
    fixed_in = None
    for affected in data.get("affected", []):
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    fixed_in = event["fixed"]
    return {
        "summary": data.get("summary") or (data.get("details") or "")[:200] or vuln_id,
        "severity": severity,
        "fixed_in": fixed_in,
    }


async def run_security_scan(root: Path) -> dict:
    """Run both scanners and return the combined, cacheable result."""
    secrets = scan_secrets(root)
    packages = parse_dependencies(root)
    vulnerabilities = await query_vulnerabilities(packages)
    return {
        "secrets": secrets,
        "vulnerabilities": vulnerabilities,
        "dependencies_scanned": len(packages),
        "scanned_at": datetime.now(UTC).isoformat(),
    }
