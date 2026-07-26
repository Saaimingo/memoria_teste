"""Tests — Domain model validation (unittest)."""

import unittest

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    FactStatus,
    HypothesisState,
    LearningState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
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
    memory_class_for,
)


class TestFact(unittest.TestCase):
    def test_create_minimal_fact(self) -> None:
        f = Fact(content="Test fact", project_id="proj-1", assertion="Test fact")
        self.assertEqual(f.type, MemoryType.FACT)
        self.assertTrue(f.id)
        self.assertEqual(f.fact_status, FactStatus.CURRENT)

    def test_fact_with_evidence(self) -> None:
        f = Fact(project_id="p1", content="Claim", evidence_ids=["ev-1", "ev-2"])
        self.assertEqual(len(f.evidence_ids), 2)

    def test_fact_obsolete(self) -> None:
        f = Fact(project_id="p1", content="Old", fact_status=FactStatus.OBSOLETE, superseded_by="v2")
        self.assertEqual(f.fact_status, FactStatus.OBSOLETE)


class TestDecision(unittest.TestCase):
    def test_create_decision(self) -> None:
        d = Decision(content="Use SQLite", project_id="p1", authority="Saimon", justification="Simple")
        self.assertEqual(d.type, MemoryType.DECISION)
        self.assertEqual(d.authority, "Saimon")

    def test_decision_alternatives(self) -> None:
        d = Decision(project_id="p1", content="A", alternatives=["B", "C"], justification="J")
        self.assertEqual(len(d.alternatives), 2)


class TestHypothesis(unittest.TestCase):
    def test_create(self) -> None:
        h = Hypothesis(content="H", project_id="p1", prediction="P", test_condition="T")
        self.assertEqual(h.type, MemoryType.HYPOTHESIS)
        self.assertEqual(h.hypothesis_state, HypothesisState.PROPOSED)


class TestEvidence(unittest.TestCase):
    def test_create(self) -> None:
        e = Evidence(content="E", project_id="p1", evidence_type="test_result", integrity_hash="abc")
        self.assertEqual(e.type, MemoryType.EVIDENCE)


class TestLearning(unittest.TestCase):
    def test_create(self) -> None:
        lr = Learning(content="L", project_id="p1", learning_state=LearningState.PROMOTED)
        self.assertEqual(lr.type, MemoryType.LEARNING)


class TestEpisode(unittest.TestCase):
    def test_create(self) -> None:
        ep = Episode(content="E", project_id="p1", initial_state="S", goal="G", result="R")
        self.assertEqual(ep.type, MemoryType.EPISODE)

    def test_causal_chain(self) -> None:
        ep = Episode(project_id="p1", content="E", initial_state="S", goal="G", result="R")
        chain = ep.causal_chain()
        self.assertEqual(len(chain), 3)


class TestCheckpoint(unittest.TestCase):
    def test_create(self) -> None:
        cp = Checkpoint(content="C", project_id="p1", current_state="W", blockers=["B"])
        self.assertEqual(cp.type, MemoryType.CHECKPOINT)
        self.assertEqual(len(cp.blockers), 1)


class TestDocumentRecord(unittest.TestCase):
    def test_create(self) -> None:
        doc = DocumentRecord(content="D", project_id="p1", is_normative=True)
        self.assertEqual(doc.type, MemoryType.DOCUMENT)
        self.assertTrue(doc.is_normative)


class TestMemoryRelation(unittest.TestCase):
    def test_create(self) -> None:
        rel = MemoryRelation(source_id="a", target_id="b", relation_type=RelationType.SUPPORTED_BY)
        self.assertEqual(rel.relation_type, RelationType.SUPPORTED_BY)


class TestProjectRecord(unittest.TestCase):
    def test_create(self) -> None:
        p = ProjectRecord(name="Test")
        self.assertTrue(p.id)


class TestMemoryClassFor(unittest.TestCase):
    def test_mapping(self) -> None:
        self.assertIs(memory_class_for(MemoryType.FACT), Fact)
        self.assertIs(memory_class_for(MemoryType.DECISION), Decision)
        self.assertIs(memory_class_for(MemoryType.CHECKPOINT), Checkpoint)
        self.assertIs(memory_class_for(MemoryType.EPISODE), Episode)
        self.assertIs(memory_class_for(MemoryType.DOCUMENT), DocumentRecord)


class TestEpistemicStates(unittest.TestCase):
    def test_all_values(self) -> None:
        statuses = list(EpistemicStatus)
        self.assertIn(EpistemicStatus.REGISTERED, statuses)
        self.assertIn(EpistemicStatus.VERIFIED, statuses)
        self.assertIn(EpistemicStatus.SUPERSEDED, statuses)
