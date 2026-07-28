"""MEC R4 — Deterministic identity for ingested memories.

Produces stable, content-addressed IDs so that re-ingestion of the same
source always maps to the same memory records.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

INGESTION_PIPELINE_VERSION = "1.1.0"


def content_fingerprint(content: str) -> str:
    """SHA-256 hex digest of the content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def stable_memory_id(
    project_id: str,
    source_path: str,
    entity_type: str,
    entity_qualifier: str = "",
) -> str:
    """Generate a deterministic, stable memory ID.

    Uses the first 16 hex chars of SHA-256 over the composite key so that
    the same logical entity always gets the same ID, regardless of ingestion
    order or timestamp.
    """
    key = f"{project_id}|{source_path}|{entity_type}|{entity_qualifier}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def stable_relation_id(
    source_memory_id: str,
    target_memory_id: str,
    relation_type: str,
) -> str:
    """Deterministic relation ID so re-ingestion does not create duplicates."""
    key = f"{source_memory_id}|{target_memory_id}|{relation_type}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def source_identity(rel_path: str) -> dict[str, Any]:
    """Return a dict with source identity fields for metadata."""
    return {
        "source_type": "git-tracked-file",
        "source_path": rel_path,
    }


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
