"""MEC Lab — SQLite storage backend.

Provides schema creation (versioned), CRUD repositories for all memory types,
relation persistence, project records, and import/export.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EvidenceType,
    FactStatus,
    HypothesisState,
    LearningState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    AnyMemory,
    Checkpoint,
    Decision,
    DocumentRecord,
    Episode,
    Evidence,
    Fact,
    Hypothesis,
    Learning,
    MemoryRelation,
    ProjectRecord,
    SourceRef,
    memory_class_for,
)

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _serialize(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _deserialize(raw: str) -> Any:
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


CREATE_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    project_id TEXT NOT NULL,
    source_refs TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    status TEXT NOT NULL DEFAULT 'registered',
    confidence TEXT NOT NULL DEFAULT 'medium',
    entities TEXT NOT NULL DEFAULT '[]',
    relations TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    supersedes TEXT,
    superseded_by TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    extra_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'medium',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (source_id) REFERENCES memories(id),
    FOREIGN KEY (target_id) REFERENCES memories(id)
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
"""


class Storage:
    """SQLite-backed storage for MEC Lab."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create or upgrade the schema to the latest version."""
        self.conn.executescript(CREATE_SCHEMA_SQL)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, _now_iso()),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def save_project(self, project: ProjectRecord) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO projects (id, name, description, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                project.id,
                project.name,
                project.description,
                project.created_at.isoformat(),
                _serialize(project.metadata),
            ),
        )
        self.conn.commit()

    def get_project(self, project_id: str) -> ProjectRecord | None:
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return None
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=_deserialize(row["metadata"]) or {},
        )

    def list_projects(self) -> list[ProjectRecord]:
        rows = self.conn.execute("SELECT * FROM projects").fetchall()
        return [
            ProjectRecord(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                created_at=datetime.fromisoformat(r["created_at"]),
                metadata=_deserialize(r["metadata"]) or {},
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Memories — unified persistence
    # ------------------------------------------------------------------

    def save_memory(self, memory: AnyMemory) -> None:
        """Persist any memory record. Serialises type-specific fields to extra_json."""
        extra = _serialize(_extract_extra(memory))
        self.conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, type, content, project_id, source_refs, created_at,
                valid_from, valid_to, status, confidence, entities, relations,
                version, supersedes, superseded_by, metadata, extra_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                memory.type,
                memory.content,
                memory.project_id,
                _serialize([s.model_dump() for s in memory.source_refs]),
                memory.created_at.isoformat(),
                memory.valid_from.isoformat() if memory.valid_from else None,
                memory.valid_to.isoformat() if memory.valid_to else None,
                memory.status,
                memory.confidence,
                _serialize([e.model_dump() for e in memory.entities]),
                _serialize(memory.relations),
                memory.version,
                memory.supersedes,
                memory.superseded_by,
                _serialize(memory.metadata),
                extra,
            ),
        )
        self.conn.commit()

    def get_memory(self, memory_id: str) -> AnyMemory | None:
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_memory(row)

    def get_memory_by_type(self, memory_id: str, mtype: MemoryType) -> AnyMemory | None:
        mem = self.get_memory(memory_id)
        if mem is not None and mem.type == mtype:
            return mem
        return None

    def list_memories(
        self,
        project_id: str | None = None,
        mtype: MemoryType | None = None,
        status: EpistemicStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnyMemory]:
        query = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        if mtype is not None:
            query += " AND type = ?"
            params.append(mtype)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [_row_to_memory(r) for r in rows]

    def count_memories(
        self,
        project_id: str | None = None,
        mtype: MemoryType | None = None,
    ) -> int:
        query = "SELECT COUNT(*) FROM memories WHERE 1=1"
        params: list[Any] = []
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        if mtype is not None:
            query += " AND type = ?"
            params.append(mtype)
        row = self.conn.execute(query, params).fetchone()
        return row[0] if row else 0

    def list_all_memories(self) -> list[AnyMemory]:
        rows = self.conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
        return [_row_to_memory(r) for r in rows]

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    def save_relation(self, rel: MemoryRelation) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO relations
               (id, source_id, target_id, relation_type, confidence, evidence_ids, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rel.id,
                rel.source_id,
                rel.target_id,
                rel.relation_type,
                rel.confidence,
                _serialize(rel.evidence_ids),
                rel.created_at.isoformat(),
                _serialize(rel.metadata),
            ),
        )
        self.conn.commit()

    def get_relations_for(
        self, memory_id: str, direction: str = "both"
    ) -> list[MemoryRelation]:
        """Return relations where memory_id is source, target, or both."""
        params: list[str] = []
        if direction == "source":
            rows = self.conn.execute(
                "SELECT * FROM relations WHERE source_id = ?", (memory_id,)
            ).fetchall()
        elif direction == "target":
            rows = self.conn.execute(
                "SELECT * FROM relations WHERE target_id = ?", (memory_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM relations WHERE source_id = ? OR target_id = ?",
                (memory_id, memory_id),
            ).fetchall()
        return [_row_to_relation(r) for r in rows]

    def list_all_relations(self) -> list[MemoryRelation]:
        rows = self.conn.execute("SELECT * FROM relations").fetchall()
        return [_row_to_relation(r) for r in rows]

    def search_relations(
        self, source_id: str | None = None, target_id: str | None = None,
        relation_type: RelationType | None = None,
    ) -> list[MemoryRelation]:
        query = "SELECT * FROM relations WHERE 1=1"
        params: list[Any] = []
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if relation_type:
            query += " AND relation_type = ?"
            params.append(relation_type)
        rows = self.conn.execute(query, params).fetchall()
        return [_row_to_relation(r) for r in rows]

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_all(self) -> dict[str, Any]:
        """Export entire database as a JSON-serialisable dict."""
        projects = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at.isoformat(),
                "metadata": p.metadata,
            }
            for p in self.list_projects()
        ]
        memories_rows = self.conn.execute("SELECT * FROM memories").fetchall()
        memories = []
        for r in memories_rows:
            mem = _row_to_memory(r)
            memories.append(mem.model_dump(mode="json"))
        relations = [r.model_dump(mode="json") for r in self.list_all_relations()]
        return {"projects": projects, "memories": memories, "relations": relations}

    def import_all(self, data: dict[str, Any]) -> None:
        """Import from a previously exported dict."""
        for proj in data.get("projects", []):
            self.save_project(ProjectRecord(**proj))
        for mem_data in data.get("memories", []):
            mtype = MemoryType(mem_data["type"])
            cls = memory_class_for(mtype)
            mem = cls(**mem_data)
            self.save_memory(mem)
        for rel_data in data.get("relations", []):
            self.save_relation(MemoryRelation(**rel_data))


# ---------------------------------------------------------------------------
# Row → model helpers
# ---------------------------------------------------------------------------


def _extract_extra(memory: AnyMemory) -> dict[str, Any]:
    """Extract type-specific fields not in the common envelope."""
    common = {
        "id", "type", "content", "project_id", "source_refs", "created_at",
        "valid_from", "valid_to", "status", "confidence", "entities",
        "relations", "version", "supersedes", "superseded_by", "metadata",
    }
    data = memory.model_dump(mode="json")
    return {k: v for k, v in data.items() if k not in common}


def _row_to_memory(row: sqlite3.Row) -> AnyMemory:
    """Reconstruct the correct domain model from a DB row."""
    mtype = MemoryType(row["type"])
    base: dict[str, Any] = {
        "id": row["id"],
        "type": mtype,
        "content": row["content"],
        "project_id": row["project_id"],
        "source_refs": _deserialize(row["source_refs"]) or [],
        "created_at": datetime.fromisoformat(row["created_at"]),
        "valid_from": datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
        "valid_to": datetime.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
        "status": EpistemicStatus(row["status"]),
        "confidence": Confidence(row["confidence"]),
        "entities": _deserialize(row["entities"]) or [],
        "relations": _deserialize(row["relations"]) or [],
        "version": row["version"],
        "supersedes": row["supersedes"],
        "superseded_by": row["superseded_by"],
        "metadata": _deserialize(row["metadata"]) or {},
    }
    extra = _deserialize(row["extra_json"]) or {}
    base.update(extra)
    cls = memory_class_for(mtype)
    return cls(**base)


def _row_to_relation(row: sqlite3.Row) -> MemoryRelation:
    return MemoryRelation(
        id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        relation_type=RelationType(row["relation_type"]),
        confidence=Confidence(row["confidence"]),
        evidence_ids=_deserialize(row["evidence_ids"]) or [],
        created_at=datetime.fromisoformat(row["created_at"]),
        metadata=_deserialize(row["metadata"]) or {},
    )
