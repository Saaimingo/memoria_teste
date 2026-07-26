"""Tests — Negative, edge cases, and behavioral tests (rework R1).

Covers:
- empty database
- invalid input
- malformed JSON
- duplicate IDs
- circular relations
- supersedes chains
- missing responses
- ranking behavior
- all 8 memory type field integrity
"""

import json
import tempfile
import unittest
from pathlib import Path

from mec_lab.domain.enums import (
    EpistemicStatus,
    MemoryType,
    RelationType,
    HypothesisState,
    LearningState,
    EvidenceType,
    DecisionStatus,
    FactStatus,
)
from mec_lab.domain.models import (
    Fact,
    Decision,
    Hypothesis,
    Evidence,
    Learning,
    Episode,
    Checkpoint,
    DocumentRecord,
    MemoryRelation,
    ProjectRecord,
)
from mec_lab.retrieval import HybridRetriever, LexicalRetriever, TfidfAdapter
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------


class TestEmptyDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_count_zero(self) -> None:
        self.assertEqual(self.store.count_memories(), 0)

    def test_list_empty(self) -> None:
        self.assertEqual(len(self.store.list_all_memories()), 0)

    def test_get_nonexistent_returns_none(self) -> None:
        self.assertIsNone(self.store.get_memory("nonexistent"))

    def test_search_empty_returns_empty(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("anything")
        self.assertEqual(len(results), 0)

    def test_hybrid_search_empty_quality_none(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("anything")
        self.assertEqual(result.quality, "none")
        self.assertEqual(len(result.source_ids), 0)

    def test_relations_empty(self) -> None:
        self.assertEqual(len(self.store.list_all_relations()), 0)

    def test_export_empty_is_valid(self) -> None:
        data = self.store.export_all()
        self.assertEqual(len(data["memories"]), 0)
        self.assertEqual(len(data["relations"]), 0)


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------


class TestInvalidInput(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_save_memory_without_project_fails_gracefully(self) -> None:
        """Fact with empty project_id should still save (no FK constraint)."""
        f = Fact(content="Test", project_id="")
        self.store.save_memory(f)
        loaded = self.store.get_memory(f.id)
        self.assertIsNotNone(loaded)

    def test_duplicate_id_overwrites(self) -> None:
        """Saving memory with same ID should overwrite."""
        f1 = Fact(id="dup1", content="First", project_id="p1")
        self.store.save_memory(f1)
        f2 = Fact(id="dup1", content="Second", project_id="p1")
        self.store.save_memory(f2)
        loaded = self.store.get_memory("dup1")
        self.assertEqual(loaded.content, "Second")  # type: ignore[union-attr]

    def test_invalid_memory_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MemoryType("invalid_type")

    def test_invalid_relation_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RelationType("invalid_relation")

    def test_invalid_status_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EpistemicStatus("invalid_status")

    def test_empty_query_lexical(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("")
        self.assertEqual(len(results), 0)

    def test_empty_query_hybrid(self) -> None:
        self.store.save_memory(Fact(content="test", project_id="p1"))
        retriever = HybridRetriever(self.store)
        result = retriever.search("")
        # Should not crash; quality may be none if no tokens
        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# Malformed JSON (EvalDataset)
# ---------------------------------------------------------------------------


class TestMalformedJson(unittest.TestCase):
    def test_missing_queries_key(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".json")
        with open(fd, "w") as f:
            json.dump({"name": "test"}, f)
        try:
            from mec_lab.evaluation import EvalDataset
            with self.assertRaises(KeyError):
                EvalDataset.from_json(Path(path))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_not_json_file(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".json")
        with open(fd, "w") as f:
            f.write("not json at all")
        try:
            from mec_lab.evaluation import EvalDataset
            with self.assertRaises((json.JSONDecodeError, UnicodeDecodeError)):
                EvalDataset.from_json(Path(path))
        finally:
            Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Circular relations
# ---------------------------------------------------------------------------


class TestCircularRelations(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_self_relation_saves(self) -> None:
        """Self-referencing relation should not crash."""
        f = Fact(id="f1", content="Self-ref", project_id="p1")
        self.store.save_memory(f)
        rel = MemoryRelation(
            source_id="f1", target_id="f1",
            relation_type=RelationType.REFERENCES,
        )
        self.store.save_relation(rel)
        rels = self.store.get_relations_for("f1")
        self.assertEqual(len(rels), 1)

    def test_mutual_relations(self) -> None:
        """A -> B and B -> A should both exist."""
        f1 = Fact(id="a", content="A", project_id="p1")
        f2 = Fact(id="b", content="B", project_id="p1")
        self.store.save_memory(f1)
        self.store.save_memory(f2)
        self.store.save_relation(MemoryRelation(
            source_id="a", target_id="b", relation_type=RelationType.SUPPORTED_BY,
        ))
        self.store.save_relation(MemoryRelation(
            source_id="b", target_id="a", relation_type=RelationType.DERIVED_FROM,
        ))
        rels_a = self.store.get_relations_for("a")
        rels_b = self.store.get_relations_for("b")
        self.assertEqual(len(rels_a), 2)
        self.assertEqual(len(rels_b), 2)


# ---------------------------------------------------------------------------
# Supersedes chain and versioning
# ---------------------------------------------------------------------------


class TestSupersedesChain(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_three_version_chain(self) -> None:
        v1 = Fact(id="f-v1", content="Version 1", project_id="p1",
                  fact_status=FactStatus.OBSOLETE, version=1)
        self.store.save_memory(v1)
        v2 = Fact(id="f-v2", content="Version 2", project_id="p1",
                  fact_status=FactStatus.OBSOLETE, supersedes="f-v1", version=2)
        v1.superseded_by = "f-v2"
        self.store.save_memory(v2)
        self.store.save_memory(v1)
        v3 = Fact(id="f-v3", content="Version 3", project_id="p1",
                  fact_status=FactStatus.CURRENT, supersedes="f-v2", version=3)
        v2.superseded_by = "f-v3"
        self.store.save_memory(v3)
        self.store.save_memory(v2)

        loaded = self.store.get_memory("f-v3")
        self.assertEqual(loaded.supersedes, "f-v2")  # type: ignore[union-attr]

    def test_supersedes_conflict_detected(self) -> None:
        """R1: supersedes should trigger conflict detection."""
        old = Fact(id="old", content="Old rule", project_id="p1",
                   status=EpistemicStatus.OBSOLETE)
        new = Fact(id="new", content="New rule", project_id="p1",
                   status=EpistemicStatus.VERIFIED, supersedes="old")
        old.superseded_by = "new"
        self.store.save_memory(old)
        self.store.save_memory(new)
        self.store.save_relation(MemoryRelation(
            source_id="new", target_id="old", relation_type=RelationType.SUPERSEDES,
        ))

        retriever = HybridRetriever(self.store)
        result = retriever.search("rule", project_id="p1")
        self.assertGreater(len(result.conflicts), 0,
                          f"Expected conflicts for supersedes, got: {result.conflicts}")


# ---------------------------------------------------------------------------
# All 8 memory types — field integrity
# ---------------------------------------------------------------------------


class TestAllMemoryTypesFieldIntegrity(unittest.TestCase):
    """R1: Test specialized fields for each of the 8 memory types."""

    def test_fact_fields(self) -> None:
        f = Fact(content="F", project_id="p1", assertion="Assertion",
                 fact_status=FactStatus.CURRENT, scope="test-scope",
                 evidence_ids=["e1"], contradiction_ids=["c1"])
        self.assertEqual(f.assertion, "Assertion")
        self.assertEqual(f.scope, "test-scope")
        self.assertEqual(f.fact_status, FactStatus.CURRENT)

    def test_decision_fields(self) -> None:
        d = Decision(content="D", project_id="p1", authority="Saimon",
                     justification="Because", decision_status=DecisionStatus.ACTIVE,
                     alternatives=["A", "B"], revocation_criteria="If X")
        self.assertEqual(d.authority, "Saimon")
        self.assertEqual(len(d.alternatives), 2)
        self.assertEqual(d.revocation_criteria, "If X")

    def test_hypothesis_fields(self) -> None:
        h = Hypothesis(content="H", project_id="p1",
                       hypothesis_state=HypothesisState.UNDER_TEST,
                       prediction="X causes Y", test_condition="Set X=1",
                       confirmation_criterion="p<0.05", rejection_criterion="p>=0.05")
        self.assertEqual(h.hypothesis_state, HypothesisState.UNDER_TEST)
        self.assertEqual(h.prediction, "X causes Y")

    def test_evidence_fields(self) -> None:
        e = Evidence(content="E", project_id="p1",
                     evidence_type=EvidenceType.TEST_RESULT,
                     location="/tmp/test.log", producer="pytest",
                     integrity_hash="abc123", limitations="Staging only")
        self.assertEqual(e.evidence_type, EvidenceType.TEST_RESULT)
        self.assertEqual(e.integrity_hash, "abc123")
        self.assertEqual(e.limitations, "Staging only")

    def test_learning_fields(self) -> None:
        lr = Learning(content="L", project_id="p1",
                      learning_state=LearningState.PROMOTED,
                      origin_episode_ids=["ep1", "ep2"],
                      works_under_conditions="Volume<100",
                      fails_under_conditions="Volume>1000")
        self.assertEqual(lr.learning_state, LearningState.PROMOTED)
        self.assertEqual(len(lr.origin_episode_ids), 2)

    def test_episode_fields(self) -> None:
        ep = Episode(content="E", project_id="p1",
                     initial_state="Start", goal="Goal", plan="Plan",
                     actions=["Act1", "Act2"], observations=["Obs1"],
                     deviations=["Dev1"], corrections=["Corr1"],
                     result="Done", consequences="Better",
                     learning_summary="Learned")
        self.assertEqual(ep.initial_state, "Start")
        self.assertEqual(len(ep.actions), 2)
        self.assertEqual(len(ep.deviations), 1)
        self.assertEqual(ep.result, "Done")

    def test_checkpoint_fields(self) -> None:
        cp = Checkpoint(content="C", project_id="p1",
                        current_state="Working", last_completed_action="Deploy",
                        active_decisions=["d1"], pending_items=["p1"],
                        blockers=["b1"], next_allowed_action="Test",
                        known_risks=["r1"], deep_dive_refs=["ep1"])
        self.assertEqual(cp.current_state, "Working")
        self.assertEqual(len(cp.blockers), 1)
        self.assertEqual(len(cp.active_decisions), 1)

    def test_document_fields(self) -> None:
        doc = DocumentRecord(content="D", project_id="p1",
                             document_type="specification", is_normative=True,
                             constituent_ids=["f1", "d1"], sections=["Intro", "Body"])
        self.assertTrue(doc.is_normative)
        self.assertEqual(len(doc.constituent_ids), 2)
        self.assertEqual(len(doc.sections), 2)


# ---------------------------------------------------------------------------
# Project scope isolation
# ---------------------------------------------------------------------------


class TestProjectScopeIsolation(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(id="f1", content="Football data", project_id="p-football",
                                     status=EpistemicStatus.VERIFIED))
        self.store.save_memory(Fact(id="f2", content="Finance data", project_id="p-finance",
                                     status=EpistemicStatus.VERIFIED))
        self.store.save_memory(Fact(id="f3", content="Queue data", project_id="p-queue",
                                     status=EpistemicStatus.VERIFIED))

    def test_project_filter_excludes_others(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("data", project_id="p-football")
        ids = [r[0].id for r in results]
        self.assertIn("f1", ids)
        self.assertNotIn("f2", ids)
        self.assertNotIn("f3", ids)

    def test_no_project_filter_returns_all(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("data")
        self.assertEqual(len(results), 3)
