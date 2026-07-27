"""MEC R4 — Ingestion pipeline.

Deterministic, idempotent pipeline that transforms project files into
MEC memory records with full provenance metadata.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mec_lab.domain.enums import DecisionStatus, EpistemicStatus, MemoryType, RelationType
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    DocumentRecord,
    Evidence,
    Fact,
    Hypothesis,
    Learning,
    MemoryRelation,
    ProjectRecord,
    memory_class_for,
)
from mec_lab.ingestion.identity import (
    INGESTION_PIPELINE_VERSION,
    content_fingerprint,
    now_iso,
    stable_memory_id,
    stable_relation_id,
)
from mec_lab.ingestion.manifest import (
    FileEntry,
    IngestionManifest,
    classify_file,
    sha256_file,
)
from mec_lab.ingestion.secret_check import check_file
from mec_lab.ingestion.segmenters import (
    ConfigSegment,
    MarkdownSegment,
    PythonEntity,
    segment_config,
    segment_markdown,
    segment_python,
)
from mec_lab.storage import Storage

# Directories / files always excluded
_ALWAYS_EXCLUDE_PATTERNS: list[str] = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "pilot_data",
    "cache",
]

# File extensions to exclude
_EXCLUDE_EXTENSIONS: set[str] = {
    ".db", ".sqlite", ".sqlite3",
    ".pyc", ".pyo",
    ".so", ".dll", ".pyd",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".exe", ".bin", ".dmg",
    ".pdf",
    ".lock",
}

# Specific filenames to exclude
_EXCLUDE_FILENAMES: set[str] = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
}

# Paths within the project that should be excluded
_EXCLUDE_PATH_PREFIXES: list[str] = [
    "experiments/exp-02/",
    "experiments/exp-02-clean/",
    "audit/",
    "evidence/",
]

# File types we can ingest
_SUPPORTED_TYPES: set[str] = {"markdown", "python", "toml", "yaml", "json"}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestionReport:
    """Accumulated statistics from an ingestion run."""

    def __init__(self) -> None:
        self.files_analyzed: int = 0
        self.files_included: int = 0
        self.files_excluded: int = 0
        self.memories_created: int = 0
        self.memories_skipped: int = 0  # duplicates
        self.relations_created: int = 0
        self.relations_skipped: int = 0
        self.secrets_blocked: int = 0
        self.errors: int = 0
        self.error_details: list[str] = []
        self.secret_details: list[dict[str, str]] = []  # path + reason only
        self.start_time: str = ""
        self.end_time: str = ""
        self.elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_analyzed": self.files_analyzed,
            "files_included": self.files_included,
            "files_excluded": self.files_excluded,
            "memories_created": self.memories_created,
            "memories_skipped": self.memories_skipped,
            "relations_created": self.relations_created,
            "relations_skipped": self.relations_skipped,
            "secrets_blocked": self.secrets_blocked,
            "errors": self.errors,
            "error_details": self.error_details[:50],
            "secret_details": self.secret_details,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": self.elapsed_seconds,
        }

    def save(self, path: str) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class IngestionPipeline:
    """Deterministic, idempotent project-to-memory ingestion pipeline."""

    def __init__(
        self,
        source_root: str,
        project_id: str,
        storage: Storage,
        dry_run: bool = False,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        force_reindex: bool = False,
    ) -> None:
        self.source_root = Path(source_root).resolve()
        self.project_id = project_id
        self.storage = storage
        self.dry_run = dry_run
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.force_reindex = force_reindex
        self.report = IngestionReport()
        self._commit_sha = ""

        # Ensure project exists
        existing = self.storage.get_project(project_id)
        if existing is None:
            self.storage.save_project(ProjectRecord(
                id=project_id, name=project_id,
                description=f"Ingested project: {self.source_root.name}",
            ))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> IngestionReport:
        """Execute the full ingestion pipeline."""
        self.report.start_time = now_iso()
        t0 = time.monotonic()

        self._commit_sha = self._get_git_commit()

        # Phase 1: Build manifest
        manifest = self._build_manifest()

        # Phase 2: Ingest each included file
        if not self.dry_run:
            for entry in manifest.files:
                if entry.status == "included":
                    self._ingest_file(entry)

        self.report.end_time = now_iso()
        self.report.elapsed_seconds = round(time.monotonic() - t0, 2)
        return self.report

    # ------------------------------------------------------------------
    # Manifest building
    # ------------------------------------------------------------------

    def _build_manifest(self) -> IngestionManifest:
        manifest = IngestionManifest(
            pipeline_version=INGESTION_PIPELINE_VERSION,
            project_id=self.project_id,
            source_root=str(self.source_root),
            commit_sha=self._commit_sha,
            generated_at=now_iso(),
        )

        tracked_files = self._git_ls_files()

        for rel_path in sorted(tracked_files):
            self.report.files_analyzed += 1
            full_path = self.source_root / rel_path

            entry = FileEntry(
                relative_path=rel_path,
                file_type=classify_file(rel_path),
                size_bytes=full_path.stat().st_size if full_path.exists() else 0,
                sha256=sha256_file(str(full_path)) if full_path.exists() else "",
                commit_sha=self._commit_sha,
            )

            # Exclusion checks
            excluded, reason = self._should_exclude(rel_path, str(full_path))
            if excluded:
                entry.status = "excluded"
                entry.exclusion_reason = reason
                self.report.files_excluded += 1
                manifest.files.append(entry)
                continue

            # Secret check
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                secret_result = check_file(rel_path, content)
                if secret_result.blocked:
                    entry.status = "excluded"
                    entry.exclusion_reason = f"secret: {'; '.join(secret_result.reasons)}"
                    self.report.files_excluded += 1
                    self.report.secrets_blocked += 1
                    self.report.secret_details.append({
                        "path": rel_path,
                        "reasons": secret_result.reasons,
                    })
                    manifest.files.append(entry)
                    continue
            except Exception:
                pass  # binary/unreadable — already excluded by extension

            # Inclusion
            entry.status = "included"
            entry.inclusion_reason = f"tracked {entry.file_type} file"
            entry.segmentation_rule = self._segmentation_rule(entry.file_type)
            entry.expected_segments = self._estimate_segments(
                entry.file_type, str(full_path), content if 'content' in dir() else ""
            )
            self.report.files_included += 1
            manifest.files.append(entry)

        manifest.total_files = len(manifest.files)
        manifest.total_expected_memories = sum(
            f.expected_segments for f in manifest.files if f.status == "included"
        )
        return manifest

    def _should_exclude(self, rel_path: str, full_path: str) -> tuple[bool, str]:
        """Return (excluded, reason)."""
        path = Path(rel_path)
        parts = path.parts

        # Always-exclude patterns
        for pat in _ALWAYS_EXCLUDE_PATTERNS:
            if pat in parts:
                return True, f"matches exclude pattern: {pat}"

        # Extension-based
        suffix = path.suffix.lower()
        if suffix in _EXCLUDE_EXTENSIONS:
            return True, f"excluded extension: {suffix}"

        # Filename
        if path.name in _EXCLUDE_FILENAMES:
            return True, f"excluded filename: {path.name}"

        # Path prefixes (project-specific)
        for prefix in _EXCLUDE_PATH_PREFIXES:
            if rel_path.startswith(prefix) or rel_path.replace("\\", "/").startswith(prefix):
                return True, f"excluded path prefix: {prefix}"

        # Only ingest supported types
        if classify_file(rel_path) not in _SUPPORTED_TYPES:
            return True, f"unsupported type: {classify_file(rel_path)}"

        # Must exist
        if not os.path.isfile(full_path):
            return True, "file not found on disk"

        return False, ""

    def _segmentation_rule(self, file_type: str) -> str:
        rules = {
            "markdown": "heading-based segmentation",
            "python": "AST-based module/class/function extraction",
            "toml": "top-level table/key extraction",
            "yaml": "top-level key extraction",
            "json": "top-level key extraction",
        }
        return rules.get(file_type, "single-segment")

    def _estimate_segments(self, file_type: str, full_path: str, content: str) -> int:
        """Rough estimate for manifest. Not binding."""
        if not content.strip():
            return 0
        if file_type == "markdown":
            return max(1, content.count("\n#") + 1)
        elif file_type == "python":
            return max(1, content.count("\ndef ") + content.count("\nclass ") + content.count("\nasync def ") + 1)
        elif file_type in ("toml", "yaml", "json"):
            try:
                if file_type == "toml":
                    data = __import__("json").loads("{}")
                    try:
                        import tomllib
                        data = tomllib.loads(content)
                    except Exception:
                        return 1
                elif file_type == "yaml":
                    data = {"_": 0}
                    try:
                        import yaml
                        data = yaml.safe_load(content) or {}
                    except Exception:
                        return 1
                elif file_type == "json":
                    data = __import__("json").loads(content)
                if isinstance(data, dict):
                    return max(1, len(data))
                return 1
            except Exception:
                return 1
        return 1

    # ------------------------------------------------------------------
    # File ingestion
    # ------------------------------------------------------------------

    def _ingest_file(self, entry: FileEntry) -> None:
        """Ingest one file, creating memory records and relations."""
        full_path = self.source_root / entry.relative_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            self.report.errors += 1
            self.report.error_details.append(f"read error: {entry.relative_path}")
            return

        ftype = entry.file_type
        file_mem_id: str | None = None

        if ftype == "markdown":
            file_mem_id = self._ingest_markdown(content, entry)
        elif ftype == "python":
            file_mem_id = self._ingest_python(content, entry)
        elif ftype in ("toml", "yaml", "json"):
            file_mem_id = self._ingest_config(content, entry, ftype)
        else:
            return

        # Relations are between memory records only.
        # The project association is via project_id in the memory metadata.
        # File-level memories get linked to their segments/members internally.

    def _create_memory(
        self,
        memory_id: str,
        mem_type: MemoryType,
        content: str,
        entry: FileEntry,
        extra: dict[str, Any] | None = None,
    ) -> str | None:
        """Create a memory record if it does not already exist.

        Returns the memory_id if created or already present, None on error.
        """
        existing = self.storage.get_memory(memory_id)
        if existing is not None:
            if not self.force_reindex:
                self.report.memories_skipped += 1
                return memory_id

        fp = content_fingerprint(content)
        now = datetime.now(UTC)
        base = {
            "id": memory_id,
            "type": mem_type,
            "content": content,
            "project_id": self.project_id,
            "status": EpistemicStatus.VERIFIED,
            "created_at": now,
            "metadata": {
                "source_type": "git-tracked-file",
                "source_path": entry.relative_path,
                "source_sha256": entry.sha256,
                "source_commit_sha": self._commit_sha,
                "language": entry.file_type,
                "ingestion_pipeline_version": INGESTION_PIPELINE_VERSION,
                "ingested_at": now.isoformat(),
                "content_fingerprint": fp,
                "operational_status": "active",
                **(extra or {}),
            },
        }

        try:
            cls = memory_class_for(mem_type)
            mem = cls(**base)
            self.storage.save_memory(mem)
            self.report.memories_created += 1
            return memory_id
        except Exception as e:
            self.report.errors += 1
            self.report.error_details.append(
                f"create_memory({memory_id}): {e}"
            )
            return None

    def _create_relation(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
    ) -> None:
        """Create a relation if it does not already exist."""
        rid = stable_relation_id(source_id, target_id, rel_type.value)
        existing_rels = self.storage.get_relations_for(source_id)
        for er in existing_rels:
            if er.target_id == target_id and er.relation_type == rel_type:
                self.report.relations_skipped += 1
                return

        rel = MemoryRelation(
            id=rid,
            source_id=source_id,
            target_id=target_id,
            relation_type=rel_type,
            created_at=datetime.now(UTC),
            metadata={"ingestion_pipeline_version": INGESTION_PIPELINE_VERSION},
        )
        self.storage.save_relation(rel)
        self.report.relations_created += 1

    # ------------------------------------------------------------------
    # Segment-type specific ingestion
    # ------------------------------------------------------------------

    def _ingest_markdown(self, content: str, entry: FileEntry) -> str | None:
        segments = segment_markdown(content, entry.relative_path)
        if not segments:
            return None

        # Create a document-level memory
        doc_title = entry.relative_path
        doc_id = stable_memory_id(self.project_id, entry.relative_path, "document", "")
        self._create_memory(
            doc_id, MemoryType.DOCUMENT,
            content=content[:5000],
            entry=entry,
            extra={
                "source_heading": doc_title,
                "qualified_name": entry.relative_path,
                "source_line_start": 1,
                "source_line_end": content.count("\n") + 1,
                "segment_count": len(segments),
            },
        )

        last_child_id: str | None = None
        for seg in segments:
            heading = seg.heading_chain[-1] if seg.heading_chain else entry.relative_path
            seg_id = stable_memory_id(
                self.project_id, entry.relative_path, "section",
                heading,
            )
            self._create_memory(
                seg_id, MemoryType.DOCUMENT,
                content=seg.content[:5000],
                entry=entry,
                extra={
                    "source_heading": " > ".join(seg.heading_chain),
                    "qualified_name": heading,
                    "source_line_start": seg.line_start,
                    "source_line_end": seg.line_end,
                    "heading_level": seg.heading_level,
                },
            )
            # Link section to document
            self._create_relation(seg_id, doc_id, RelationType.PART_OF)
            last_child_id = seg_id

        return doc_id

    def _ingest_python(self, content: str, entry: FileEntry) -> str | None:
        entities = segment_python(content, entry.relative_path)
        if not entities:
            return None

        # Module entity (first one)
        module_entity = entities[0]
        module_id = stable_memory_id(
            self.project_id, entry.relative_path, "module",
            module_entity.qualified_name,
        )

        # Determine memory type based on content
        mem_type = MemoryType.FACT

        self._create_memory(
            module_id, mem_type,
            content=module_entity.content[:5000],
            entry=entry,
            extra={
                "source_heading": module_entity.qualified_name,
                "qualified_name": module_entity.qualified_name,
                "source_line_start": module_entity.line_start,
                "source_line_end": module_entity.line_end,
                "entity_type": "module",
                "docstring": module_entity.docstring[:1000],
                "imports": module_entity.imports[:20],
            },
        )

        module_id_map: dict[str, str] = {"": module_id}
        last_parent: str | None = None

        for entity in entities[1:]:  # skip module
            ent_id = stable_memory_id(
                self.project_id, entry.relative_path,
                entity.entity_type, entity.qualified_name,
            )

            self._create_memory(
                ent_id, mem_type,
                content=entity.content[:5000],
                entry=entry,
                extra={
                    "source_heading": entity.qualified_name,
                    "qualified_name": entity.qualified_name,
                    "signature": entity.signature,
                    "docstring": entity.docstring[:1000],
                    "source_line_start": entity.line_start,
                    "source_line_end": entity.line_end,
                    "entity_type": entity.entity_type,
                },
            )

            # Determine parent: for methods, find the class; for classes/functions, use module
            if entity.entity_type == "method":
                parent_name = entity.qualified_name.rsplit(".", 2)[0] if entity.qualified_name.count(".") >= 2 else ""
            else:
                parent_name = entity.qualified_name.rsplit(".", 1)[0] if "." in entity.qualified_name else ""

            parent_id = module_id_map.get(parent_name, module_id)
            self._create_relation(ent_id, parent_id, RelationType.PART_OF)

            module_id_map[entity.qualified_name] = ent_id
            last_parent = ent_id

        return module_id

    def _ingest_config(
        self, content: str, entry: FileEntry, file_type: str,
    ) -> str | None:
        segments = segment_config(content, entry.relative_path, file_type)
        if not segments:
            return None

        # Create a file-level memory
        file_id = stable_memory_id(self.project_id, entry.relative_path, "config", "")
        self._create_memory(
            file_id, MemoryType.FACT,
            content=content[:5000],
            entry=entry,
            extra={
                "source_heading": entry.relative_path,
                "qualified_name": entry.relative_path,
                "source_line_start": 1,
                "source_line_end": content.count("\n") + 1,
                "config_format": file_type,
                "segment_count": len(segments),
            },
        )

        for seg in segments:
            seg_id = stable_memory_id(
                self.project_id, entry.relative_path, "config_key",
                seg.key_path,
            )
            self._create_memory(
                seg_id, MemoryType.FACT,
                content=seg.content[:5000],
                entry=entry,
                extra={
                    "source_heading": seg.key_path,
                    "qualified_name": seg.key_path,
                    "config_section": seg.key_path,
                    "config_value": seg.value_text[:2000],
                    "config_format": file_type,
                },
            )
            self._create_relation(seg_id, file_id, RelationType.PART_OF)

        return file_id

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _get_git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.source_root),
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _git_ls_files(self) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=str(self.source_root),
                capture_output=True, text=True, timeout=30,
            )
            return [l.strip() for l in result.stdout.split("\n") if l.strip()]
        except Exception:
            # Fallback: walk the directory manually with exclusions
            files: list[str] = []
            for root, dirs, filenames in os.walk(str(self.source_root)):
                # Skip excluded dirs
                dirs[:] = [d for d in dirs if d not in _ALWAYS_EXCLUDE_PATTERNS]
                for f in filenames:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, str(self.source_root)).replace("\\", "/")
                    if not rel.startswith(".git"):
                        files.append(rel)
            return files
