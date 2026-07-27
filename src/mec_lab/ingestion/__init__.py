"""MEC R4 — Ingestion layer.

Deterministic, idempotent pipeline for transforming project files into
structured MEC memory records.
"""

from mec_lab.ingestion.identity import (
    INGESTION_PIPELINE_VERSION,
    content_fingerprint,
    stable_memory_id,
    stable_relation_id,
)
from mec_lab.ingestion.manifest import IngestionManifest
from mec_lab.ingestion.pipeline import IngestionPipeline, IngestionReport
from mec_lab.ingestion.secret_check import check_file

__all__ = [
    "IngestionPipeline",
    "IngestionReport",
    "IngestionManifest",
    "INGESTION_PIPELINE_VERSION",
    "content_fingerprint",
    "stable_memory_id",
    "stable_relation_id",
    "check_file",
]
