"""Tests — SQLite storage (unittest)."""

import json
import tempfile
import unittest
from pathlib import Path

from mec_lab.domain.enums import EpistemicStatus, MemoryType, RelationType
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    Episode,
    Fact,
    MemoryRelation,
    ProjectRecord,
)
from mec_lab.storage import Storage


class TestStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_init_creates_tables(self) -> None:
        tables = self.store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r[0] for r in tables}
        self.assertIn("projects", names)
        self.assertIn("memories", names)
        self.assertIn("relations", names)

    def test_schema_idempotent(self) -> None:
        self.store.init_schema()
        row = self.store.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()
        self.assertEqual(row[0], 1)

    def test_save_and_get_project(self) -> None:
        proj = ProjectRecord(name="Test")
        self.store.save_project(proj)
        loaded = self.store.get_project(proj.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Test")  # type: ignore[union-attr]

    def test_list_projects(self) -> None:
        self.store.save_project(ProjectRecord(name="A"))
        self.store.save_project(ProjectRecord(name="B"))
        self.assertEqual(len(self.store.list_projects()), 2)

    def test_save_and_get_fact(self) -> None:
        fact = Fact(content="Sky is blue", project_id="p1", assertion="Sky is blue")
        self.store.save_memory(fact)
        loaded = self.store.get_memory(fact.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.content, "Sky is blue")  # type: ignore[union-attr]

    def test_save_and_get_decision(self) -> None:
        d = Decision(content="Use SQLite", project_id="p1", authority="Saimon", justification="J")
        self.store.save_memory(d)
        loaded = self.store.get_memory(d.id)
        self.assertIsInstance(loaded, Decision)
        self.assertEqual(loaded.authority, "Saimon")  # type: ignore[union-attr]

    def test_save_and_get_checkpoint(self) -> None:
        cp = Checkpoint(content="Snap", project_id="p1", current_state="W", blockers=["B1"])
        self.store.save_memory(cp)
        loaded = self.store.get_memory(cp.id)
        self.assertIsInstance(loaded, Checkpoint)
        self.assertEqual(loaded.blockers, ["B1"])  # type: ignore[union-attr]

    def test_save_and_get_episode(self) -> None:
        ep = Episode(content="Bug fix", project_id="p1", initial_state="S", goal="G", result="R")
        self.store.save_memory(ep)
        loaded = self.store.get_memory(ep.id)
        self.assertIsInstance(loaded, Episode)

    def test_list_memories_by_project(self) -> None:
        self.store.save_memory(Fact(content="F1", project_id="p1"))
        self.store.save_memory(Fact(content="F2", project_id="p1"))
        self.store.save_memory(Fact(content="F3", project_id="p2"))
        self.assertEqual(len(self.store.list_memories(project_id="p1")), 2)

    def test_list_memories_by_type(self) -> None:
        self.store.save_memory(Fact(content="F", project_id="p1"))
        self.store.save_memory(Decision(content="D", project_id="p1", justification="J"))
        self.assertEqual(len(self.store.list_memories(mtype=MemoryType.FACT)), 1)

    def test_count_memories(self) -> None:
        self.assertEqual(self.store.count_memories(), 0)
        self.store.save_memory(Fact(content="F", project_id="p1"))
        self.assertEqual(self.store.count_memories(), 1)

    def test_supersedes_chain(self) -> None:
        old = Fact(content="Old", project_id="p1", fact_status="obsolete")
        self.store.save_memory(old)
        new = Fact(content="New", project_id="p1", fact_status="current", supersedes=old.id)
        old.superseded_by = new.id
        self.store.save_memory(new)
        self.store.save_memory(old)
        loaded = self.store.get_memory(new.id)
        self.assertEqual(loaded.supersedes, old.id)  # type: ignore[union-attr]

    def test_save_and_get_relation(self) -> None:
        f1 = Fact(content="F1", project_id="p1")
        f2 = Fact(content="F2", project_id="p1")
        self.store.save_memory(f1)
        self.store.save_memory(f2)
        rel = MemoryRelation(source_id=f1.id, target_id=f2.id, relation_type=RelationType.SUPPORTED_BY)
        self.store.save_relation(rel)
        rels = self.store.get_relations_for(f1.id)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0].relation_type, RelationType.SUPPORTED_BY)

    def test_export_import_roundtrip(self) -> None:
        self.store.save_project(ProjectRecord(name="T"))
        self.store.save_memory(Fact(content="F1", project_id="p1"))
        exported = self.store.export_all()
        s2 = Storage(":memory:")
        s2.init_schema()
        s2.import_all(exported)
        self.assertEqual(s2.count_memories(), 1)
        self.assertEqual(len(s2.list_projects()), 1)


class TestFilePersistence(unittest.TestCase):
    def test_persistence(self) -> None:
        import os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            s1 = Storage(path)
            s1.init_schema()
            f = Fact(content="Persist", project_id="p1")
            s1.save_memory(f)
            s1.conn.close()
            s2 = Storage(path)
            loaded = s2.get_memory(f.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.content, "Persist")  # type: ignore[union-attr]
            s2.conn.close()
        finally:
            Path(path).unlink(missing_ok=True)
