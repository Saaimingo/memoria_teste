"""MEC R4 — Deterministic identifier normalization.

Provides stable, canonical representations for technical identifiers so that
semantically equivalent inputs always collide on the same normalized key:

* MAC addresses with ``:`` / ``-`` separators or bare hex digits.
* Serial numbers with different casing or whitespace.
* Protocol numbers with spaces, dots or hyphens.
* File paths Windows <-> Unix (forward slashes, drive letters).
* Commit SHAs (full or prefix, lowercased hex).
* File names with casing differences.
* Ticket numbers with varying prefixed forms (``#123`` ``TICKET-123`` etc).

None of these functions alter the *original stored value*. They only produce a
normalized representation used by the assisted retrieval pipeline for matching.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Field names we know how to normalize. Kept here so callers have a single
# source of truth for the identifier dimensions.
# ---------------------------------------------------------------------------

IDENTIFIER_FIELDS: tuple[str, ...] = (
    "serial_number",
    "mac_address",
    "protocol_number",
    "commit_sha",
    "file_path",
    "folder_path",
    "file_name",
    "ticket_number",
    "issue_id",
)


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------


def normalize_mac(value: str) -> str:
    """Canonical MAC form: 12 lowercase hex digits, no separators.

    ``"AA:BB:CC:dd:ee:ff"`` -> ``"aabbccddeeff"``
    ``"AA-BB-CC-DD-EE-FF"`` -> ``"aabbccddeeff"``
    ``"aabbccddeeff"``       -> ``"aabbccddeeff"``
    """
    if not value:
        return ""
    hex_only = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return hex_only


def normalize_serial(value: str) -> str:
    """Canonical serial form: uppercase, only alphanumerics.

    ``" sn-abc-123  "`` -> ``"SNABC123"``.
    """
    if not value:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


def normalize_protocol(value: str) -> str:
    """Canonical protocol form: uppercase alphanumerics, separators stripped.

    ``"PROTO-1.2 / 3"``  -> ``"PROTO123"``.
    """
    if not value:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


def normalize_path(value: str) -> str:
    """Canonical path form: forward slashes, no trailing slash, lowercase drive.

    ``"D:\\Foo\\bar.py"``  -> ``"/d/foo/bar.py"``
    ``"D:/Foo/bar.py/"``   -> ``"/d/foo/bar.py"``
    ``"/foo/bar.py"``      -> ``"/foo/bar.py"``
    """
    if not value:
        return ""
    v = value.strip()
    # Convert Windows driveletter form to MSYS-style /driveletter path.
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", v)
    if m:
        drive = m.group(1).lower()
        rest = re.sub(r"[\\/]+", "/", m.group(2)).strip("/")
        return f"/{drive}/{rest}" if rest else f"/{drive}"
    # Already unix-like
    v = re.sub(r"[\\/]+", "/", v)
    if not v.startswith("/"):
        v = "/" + v
    if v != "/" and v.endswith("/"):
        v = v[:-1]
    return v


def normalize_commit(value: str) -> str:
    """Canonical commit SHA form: lowercase hex (prefix kept as-is)."""
    if not value:
        return ""
    return re.sub(r"[^0-9a-fA-F]", "", value).lower()


def normalize_filename(value: str) -> str:
    """Canonical filename form: lowercase, basename only, separators stripped.

    ``"D:\\Foo\\Bar.py"``  -> ``"bar.py"``
    ``"/foo/bar.py"``      -> ``"bar.py"``
    """
    if not value:
        return ""
    base = value.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return base if base else value.lower()


def normalize_ticket(value: str) -> str:
    """Canonical ticket/issue form: digits-only core, no prefix.

    ``"#123"``, ``"TICKET-123"``, ``"JIRA-123"``, ``"123"`` -> ``"123"``.
    """
    if not value:
        return ""
    # Grab the trailing numeric run.
    digits = re.search(r"(\d+)$", value.strip())
    return digits.group(1) if digits else re.sub(r"[^0-9A-Za-z]", "", value)


def normalize_identifier(field: str, value: str) -> str:
    """Dispatch normalization by structured-field name."""
    if not value:
        return ""
    dispatch = {
        "mac_address": normalize_mac,
        "serial_number": normalize_serial,
        "protocol_number": normalize_protocol,
        "commit_sha": normalize_commit,
        "file_path": normalize_path,
        "folder_path": normalize_path,
        "file_name": normalize_filename,
        "ticket_number": normalize_ticket,
        "issue_id": normalize_ticket,
    }
    return dispatch.get(field, _generic_normalize)(value)


def _generic_normalize(value: str) -> str:
    """Fall-through normalizer: lowercase, collapse whitespace, keep punctuation."""
    return re.sub(r"\s+", " ", value.strip()).lower()


# ---------------------------------------------------------------------------
# Extraction: pull candidate identifiers out of free-text queries.
# ---------------------------------------------------------------------------

# Regex patterns used to recognize identifiers inside a query. The named
# groups must match IDENTIFIER_FIELDS for uniform downstream handling.
_IDENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # MAC: six groups of hex separated by ':' or '-' (any case).
    ("mac_address", re.compile(r"\b([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})\b")),
    # Commit SHA: 7..40 lowercase/uppercase hex chars.
    ("commit_sha", re.compile(r"\b([0-9a-fA-F]{8,40})\b")),
]

# A few lowercase keywords to not hijack as commit SHA (false positives).
_NOT_A_SHA = {"ffffff", "0000000", "aaaaaaa", "abcd123", "1234567", "deadbeef"}


def extract_identifier_hints(text: str) -> dict[str, list[str]]:
    """Return a map of identifier field -> list of raw candidate values.

    Multiple candidate values for the same field are allowed; the matcher picks
    whichever produces an exact normalized match against a stored value first.
    """
    hints: dict[str, list[str]] = {}
    if not text:
        return hints
    for field, pattern in _IDENT_PATTERNS:
        for raw in pattern.findall(text):
            if field == "commit_sha" and normalize_commit(raw) in _NOT_A_SHA:
                continue
            hints.setdefault(field, []).append(raw)
    # Serial: tokens that look like ``SN-XXX`` or ``SN:XXX`` or serial prefix.
    sn_re = re.compile(r"\b(serial|sn|serie)\s*[:\-]?\s*([A-Za-z0-9\-]{3,})\b", re.IGNORECASE)
    for m in sn_re.finditer(text):
        hints.setdefault("serial_number", []).append(m.group(2))
    # Protocol: protocolo/patente etc. Followed by digits/separators.
    proto_re = re.compile(r"\b(protocolo|protocol|patente)\s*[:\-]?\s*([0-9A-Za-z\-.\/]{3,})", re.IGNORECASE)
    for m in proto_re.finditer(text):
        hints.setdefault("protocol_number", []).append(m.group(2))
    # MAC loose: 12 contiguous hex digits, not already captured by mac regex above.
    mac_loose = re.compile(r"\b([0-9a-fA-F]{12})\b")
    for raw in mac_loose.findall(text):
        hints.setdefault("mac_address", []).append(raw)
    # Ticket: #NNN or TICKET-NNN or similar prefixed number.
    ticket_re = re.compile(r"\b(?:#|ticket-|chamado-|issue-)?(\d{3,8})\b", re.IGNORECASE)
    # Only treat as a ticket number when a hint word appears, avoid random ints.
    if any(w in text.lower() for w in ("ticket", "chamado", "issue", "protocolo")):
        # Try to grab tickets with explicit prefix first
        explicit = re.compile(r"\b(?:ticket|chamado|issue)\s*[:\-]?\s*#?(\d+)\b", re.IGNORECASE)
        for raw in explicit.findall(text):
            hints.setdefault("ticket_number", []).append(raw)
    # File path / file name: anything that looks like a path with a dot extension.
    path_re = re.compile(r"([A-Za-z]:[\\/][^ \t]+|/[A-Za-z][^ \t]+|\b[\w\-./]+\.[a-z]{1,6}\b)")
    for raw in path_re.findall(text):
        hints.setdefault("file_path", []).append(raw)
    # Deduplicate while preserving order
    for k in list(hints.keys()):
        seen: list[str] = []
        for v in hints[k]:
            if v not in seen:
                seen.append(v)
        hints[k] = seen
    return hints


# Local variables:
# python-indent-offset: 4
# end: