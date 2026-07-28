"""MEC R4.1 — Symbolic normalization.

Deterministic normalization for software identifiers: class names, function
names, module paths, CLI options, qualified names, and commit SHAs.

All transformations are reversible and preserve the original string.
No LLM involved — pure string transforms.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Symbol normalization: PascalCase, camelCase, snake_case, kebab-case, etc.
# ---------------------------------------------------------------------------


def normalize_symbol(text: str) -> list[str]:
    """Return all normalized forms of a software symbol.

    Given e.g. ``ClarificationCycle``, returns:
    - ``ClarificationCycle`` (original)
    - ``clarification cycle`` (word split)
    - ``clarification_cycle`` (snake)
    - ``clarification-cycle`` (kebab)
    - ``clarificationcycle`` (flat)

    Given ``mec_lab.retrieval.assisted``, returns:
    - ``mec_lab.retrieval.assisted`` (original)
    - ``mec lab retrieval assisted`` (words)
    - ``mec_lab_retrieval_assisted`` (uniform separator)

    This list is used for matching — a query token normalizes to one of these
    forms, and a stored entity's qualified_name normalizes to the same set.
    """
    if not text:
        return []

    forms: set[str] = {text}

    # Split PascalCase / camelCase boundaries
    # "ClarificationCycle" -> "Clarification Cycle"
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", words)
    # Replace separators with spaces
    words = re.sub(r"[._\-/\\]+", " ", words).strip().lower()
    if words:
        forms.add(words)
        # snake_case form of the words
        snake = words.replace(" ", "_")
        forms.add(snake)
        # kebab-case form
        kebab = words.replace(" ", "-")
        forms.add(kebab)
        # flat (no separators)
        flat = words.replace(" ", "")
        forms.add(flat)

    # Also add the lowercased original
    forms.add(text.lower())

    # Replace dots with underscores for dotted module paths
    if "." in text:
        forms.add(text.lower().replace(".", "_"))
        forms.add(text.lower().replace(".", " "))
        forms.add(text.lower().replace(".", "/"))

    # Replace slashes with dots for file paths
    if "/" in text or "\\" in text:
        norm_slash = text.replace("\\", "/")
        forms.add(norm_slash)
        forms.add(norm_slash.lower())
        forms.add(norm_slash.lower().replace("/", "."))

    return sorted(forms)


def symbols_match(query_token: str, stored_token: str) -> bool:
    """Check if a query token and a stored token match under normalization."""
    q_forms = set(normalize_symbol(query_token))
    s_forms = set(normalize_symbol(stored_token))
    return bool(q_forms & s_forms)


# ---------------------------------------------------------------------------
# CLI option normalization
# ---------------------------------------------------------------------------


def normalize_cli_option(text: str) -> str:
    """Normalize a CLI option: strip leading --, lowercase, replace - with _.

    --retrieval-mode -> retrieval_mode
    --retrieval_mode -> retrieval_mode
    retrieval-mode   -> retrieval_mode
    """
    t = text.strip()
    # Strip leading dashes
    t = re.sub(r"^-+", "", t)
    # Replace hyphens with underscores
    t = t.replace("-", "_")
    return t.lower()


def cli_options_match(query_option: str, stored_option: str) -> bool:
    """Match CLI options under normalization."""
    return normalize_cli_option(query_option) == normalize_cli_option(stored_option)


# ---------------------------------------------------------------------------
# Path normalization (extends identifiers.py with symbol awareness)
# ---------------------------------------------------------------------------


def normalize_path_symbol(path: str) -> str:
    """Normalize a file path for symbolic matching.

    Uses existing normalize_path for the canonical form, then lowercases.
    """
    from mec_lab.retrieval.identifiers import normalize_path
    n = normalize_path(path)
    return n.lower()


def paths_symbol_match(query_path: str, stored_path: str) -> bool:
    """Match paths under both structural and symbolic normalization."""
    q = normalize_path_symbol(query_path)
    s = normalize_path_symbol(stored_path)
    if q == s:
        return True
    # Also try matching basename
    from pathlib import PurePath
    q_base = PurePath(query_path.replace("\\", "/")).name.lower()
    s_base = PurePath(stored_path.replace("\\", "/")).name.lower()
    if q_base and s_base and q_base == s_base:
        return True
    # Containment: query is a suffix of stored path
    if s.endswith(q) or q.endswith(s):
        return True
    return False


# ---------------------------------------------------------------------------
# Commit SHA normalization
# ---------------------------------------------------------------------------


def extract_commit_prefix(text: str) -> str | None:
    """Extract a commit SHA or prefix from text.

    Looks for 7-40 hex chars, optionally preceded by 'commit', 'sha', 'SHA'.
    Returns the hex string (lowercased) or None.
    """
    if not text:
        return None
    # Try "commit <hex>" or "SHA <hex>" patterns
    m = re.search(r"\b(?:commit|sha|SHA)\s+([0-9a-fA-F]{7,40})\b", text, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # Try standalone hex of 7-40 chars (but not trivial like "1234567")
    m = re.search(r"\b([0-9a-fA-F]{7,40})\b", text)
    if m:
        val = m.group(1).lower()
        # Avoid matching all-zero or trivially false hex
        if val != "0" * len(val) and not all(c in "0123456789" for c in val):
            return val
    return None


def commit_prefix_matches(prefix: str, full_sha: str) -> bool:
    """Check if a prefix matches a full SHA (case-insensitive)."""
    return full_sha.lower().startswith(prefix.lower())


# ---------------------------------------------------------------------------
# Symbol index entry: describes a structured entity for matching
# ---------------------------------------------------------------------------


from dataclasses import dataclass, field
from typing import Any


@dataclass
class SymbolIndexEntry:
    """An entry in the symbol index, derived from ingested memory metadata."""
    memory_id: str
    entity_type: str = ""  # "module", "class", "function", "method", "command", "option", "config_key", "section", "document", "file"
    qualified_name: str = ""
    source_path: str = ""
    source_heading: str = ""
    language: str = ""
    module_name: str = ""
    class_name: str = ""
    function_name: str = ""
    method_name: str = ""
    symbol_kind: str = ""
    symbol_normalized: list[str] = field(default_factory=list)
    cli_command: str = ""
    cli_option: str = ""
    cli_option_normalized: str = ""
    file_role: str = ""  # "module-file", "document", "test", "config"
    group_id: str = ""  # entity group for candidate grouping

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "entity_type": self.entity_type,
            "qualified_name": self.qualified_name,
            "source_path": self.source_path,
            "source_heading": self.source_heading,
            "language": self.language,
            "module_name": self.module_name,
            "class_name": self.class_name,
            "function_name": self.function_name,
            "method_name": self.method_name,
            "symbol_kind": self.symbol_kind,
            "symbol_normalized": self.symbol_normalized,
            "cli_command": self.cli_command,
            "cli_option": self.cli_option,
            "cli_option_normalized": self.cli_option_normalized,
            "file_role": self.file_role,
            "group_id": self.group_id,
        }


def build_symbol_index_entry(
    memory_id: str,
    metadata: dict[str, Any],
) -> SymbolIndexEntry | None:
    """Build a SymbolIndexEntry from ingested memory metadata.

    Returns None if the memory has no relevant structured metadata.
    """
    if not metadata:
        return None

    entry = SymbolIndexEntry(
        memory_id=memory_id,
        entity_type=metadata.get("entity_type", ""),
        qualified_name=metadata.get("qualified_name", ""),
        source_path=metadata.get("source_path", ""),
        source_heading=metadata.get("source_heading", ""),
        language=metadata.get("language", ""),
        module_name=metadata.get("module_name", ""),
        class_name=metadata.get("class_name", ""),
        function_name=metadata.get("function_name", ""),
        method_name=metadata.get("method_name", ""),
        symbol_kind=metadata.get("symbol_kind", ""),
        cli_command=metadata.get("cli_command", ""),
        cli_option=metadata.get("cli_option", ""),
        file_role=metadata.get("file_role", ""),
    )

    # Build normalized symbol forms from qualified_name or source_heading
    symbol_source = entry.qualified_name or entry.source_heading or ""
    if symbol_source:
        entry.symbol_normalized = normalize_symbol(symbol_source)

    # Normalize CLI option
    if entry.cli_option:
        entry.cli_option_normalized = normalize_cli_option(entry.cli_option)

    # Determine group_id: group by source_path for file-level grouping
    if entry.source_path:
        # For files, group = the file-level memory (module/document/config)
        # For segments, group = parent file path
        if entry.entity_type in ("module", "file", "config"):
            entry.group_id = entry.source_path
        elif entry.entity_type == "document":
            entry.group_id = entry.source_path
        else:
            entry.group_id = entry.source_path

    return entry