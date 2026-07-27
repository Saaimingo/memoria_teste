"""MEC R4 — Ingestion manifest.

Records every file considered for ingestion, its disposition, and
the planned segmentation — before any memory is written.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class FileEntry:
    """One file considered for ingestion."""
    relative_path: str
    file_type: str  # "markdown", "python", "toml", "yaml", "json", "other"
    size_bytes: int
    sha256: str
    commit_sha: str
    inclusion_reason: str = ""
    segmentation_rule: str = ""
    expected_segments: int = 0
    status: str = "pending"  # "included" | "excluded"
    exclusion_reason: str = ""


@dataclass
class IngestionManifest:
    """Complete pre-ingestion plan."""
    pipeline_version: str = "1.0.0"
    project_id: str = ""
    source_root: str = ""
    commit_sha: str = ""
    generated_at: str = ""
    total_files: int = 0
    included_files: int = 0
    excluded_files: int = 0
    total_expected_memories: int = 0
    files: list[FileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.pipeline_version,
            "project_id": self.project_id,
            "source_root": self.source_root,
            "commit_sha": self.commit_sha,
            "generated_at": self.generated_at,
            "total_files": self.total_files,
            "included_files": self.included_files,
            "excluded_files": self.excluded_files,
            "total_expected_memories": self.total_expected_memories,
            "files": [asdict(f) for f in self.files],
        }

    def save(self, path: str) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str) -> IngestionManifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        m = cls(
            pipeline_version=data.get("pipeline_version", ""),
            project_id=data.get("project_id", ""),
            source_root=data.get("source_root", ""),
            commit_sha=data.get("commit_sha", ""),
            generated_at=data.get("generated_at", ""),
            total_files=data.get("total_files", 0),
            included_files=data.get("included_files", 0),
            excluded_files=data.get("excluded_files", 0),
            total_expected_memories=data.get("total_expected_memories", 0),
        )
        m.files = [FileEntry(**f) for f in data.get("files", [])]
        return m


def sha256_file(path: str) -> str:
    """SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_file(rel_path: str) -> str:
    """Return the file type based on extension."""
    ext = Path(rel_path).suffix.lower()
    mapping = {
        ".md": "markdown",
        ".py": "python",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
    }
    return mapping.get(ext, "other")
