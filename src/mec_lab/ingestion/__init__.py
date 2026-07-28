"""MEC R4 — Ingestion layer.

Deterministic, idempotent pipeline for transforming project files into
structured MEC memory records.

R4.1: Symbolic normalization and git history ingestion.
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
from mec_lab.ingestion.symbol_normalize import (
    SymbolIndexEntry,
    build_symbol_index_entry,
    cli_options_match,
    commit_prefix_matches,
    extract_commit_prefix,
    normalize_cli_option,
    normalize_symbol,
    normalize_path_symbol,
    paths_symbol_match,
    symbols_match,
)

__all__ = [
    "IngestionPipeline",
    "IngestionReport",
    "IngestionManifest",
    "INGESTION_PIPELINE_VERSION",
    "content_fingerprint",
    "stable_memory_id",
    "stable_relation_id",
    "check_file",
    "SymbolIndexEntry",
    "build_symbol_index_entry",
    "cli_options_match",
    "commit_prefix_matches",
    "extract_commit_prefix",
    "normalize_cli_option",
    "normalize_symbol",
    "normalize_path_symbol",
    "paths_symbol_match",
    "symbols_match",
]
