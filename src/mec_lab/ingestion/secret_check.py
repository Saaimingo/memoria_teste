"""MEC R4 — Secret and credential detection for ingestion pipeline.

Blocks files containing secrets before they become memories.
Never reproduces the secret value in logs or reports.
"""

from __future__ import annotations

import re
from pathlib import Path

# Patterns that indicate a file likely contains secrets.
# These are conservative — we only match clear patterns, not heuristics.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key_pattern", re.compile(
        r'(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?key)\s*[:=]\s*["\']?[\w\-]{20,}["\']?',
        re.IGNORECASE,
    )),
    ("private_key_header", re.compile(
        r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
    )),
    ("jwt_token", re.compile(
        r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    )),
    ("github_token", re.compile(
        r'(?:gh[pous]_[A-Za-z0-9]{36,}|github[_-]?token\s*[:=])',
        re.IGNORECASE,
    )),
    ("password_assignment", re.compile(
        r'(?:password|passwd|pwd|senha)\s*[:=]\s*["\'][^"\']{4,}["\']',
        re.IGNORECASE,
    )),
    ("connection_string", re.compile(
        r'(?:mysql|postgres|mongodb|redis|sqlite)://[^\s"\']+@',
        re.IGNORECASE,
    )),
]

_BLOCKED_FILENAMES: set[str] = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.json", "secrets.yaml", "secrets.yml",
    "service-account.json", "service_account.json",
    "id_rsa", "id_ed25519", "id_ecdsa",
    ".pem", ".key", ".pfx", ".p12",
    ".npmrc", ".pypirc",
}

_BLOCKED_EXTENSIONS: set[str] = {
    ".pem", ".key", ".pfx", ".p12", ".jks", ".keystore",
}


class SecretCheckResult:
    """Result of scanning a single file for secrets."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.blocked = False
        self.reasons: list[str] = []

    def add_reason(self, reason: str) -> None:
        self.blocked = True
        self.reasons.append(reason)


def check_file(file_path: str, content: str | None = None) -> SecretCheckResult:
    """Scan a file for secrets.

    If content is provided it is scanned; otherwise only the filename
    is checked against blocked-name lists.

    Returns a SecretCheckResult — never the secret value itself.
    """
    result = SecretCheckResult(file_path)
    path = Path(file_path)
    name = path.name.lower()

    # Filename blocks
    if name in _BLOCKED_FILENAMES:
        result.add_reason(f"blocked filename: {name}")

    suffix = path.suffix.lower()
    if suffix in _BLOCKED_EXTENSIONS:
        result.add_reason(f"blocked extension: {suffix}")

    # Content scan (if provided)
    if content is not None and not result.blocked:
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                result.add_reason(f"content matches {label}")
                break  # one match is enough to block

    return result


def is_safe_file(file_path: str, content: str | None = None) -> tuple[bool, list[str]]:
    """Convenience: return (safe, reasons)."""
    r = check_file(file_path, content)
    return (not r.blocked, r.reasons)
