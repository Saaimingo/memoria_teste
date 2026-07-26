"""Tests — Context capsule and evaluation (unittest)."""

import json
import tempfile
import unittest
from pathlib import Path

from mec_lab.context import CapsuleBuilder, build_resumption_prompt
from mec_lab.domain.enums import EpistemicStatus
from mec_lab.domain.models import Checkpoint, Decision, Fact, Episode
from mec_lab.evaluation import (
    ABLATION_VARIANTS,
    EvalDataset,
    Evaluator,
    QueryCase,
    _compute_ndcg,
    generate_report,
    run_ablation,
)
from mec_lab.retrieval import DeterministicSemanticAdapter, HybridRetriever
from mec_lab.storage import Storage


class TestCapsuleBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Checkpoint(
            id="cp-1", content="Snapshot", project_id="proj-football",
            current_state="Working", last_completed_action="Fix bug",
            next_allowed_action="Test", blockers=["No $"],
            pending_items=["UI"],
        ))
        self.store.save_memory(Decision(
            id="d-1", content="Use Python", project_id="proj-football",
            authority="Saimon", decision_status="active",
        ))
        self.store.save_memory(Fact(
            id="f-1", content="20 clubes com acesso e rebaixamento.",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))

    def test_build_capsule(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        builder = CapsuleBuilder(self.store, retriever)
        capsule = builder.build("futebol", project_id="proj-football")
        self.assertEqual(capsule.project_id, "proj-football")
        self.assertGreater(capsule.total_characters, 0)

    def test_capsule_summary(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        builder = CapsuleBuilder(self.store, retriever)
        capsule = builder.build("futebol")
        s = capsule.summary()
        self.assertIn("total_characters", s)

    def test_resumption_prompt(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        builder = CapsuleBuilder(self.store, retriever)
        capsule = builder.build("futebol", project_id="proj-football")
        prompt = build_resumption_prompt(capsule)
        self.assertIn("MEC CONTEXT CAPSULE", prompt)
        self.assertIn("Capsule stats:", prompt)

    def test_empty_capsule(self) -> None:
        s = Storage(":memory:")
        s.init_schema()
        retriever = HybridRetriever(s, semantic=DeterministicSemanticAdapter())
        builder = CapsuleBuilder(s, retriever)
        capsule = builder.build("nothing")
        self.assertEqual(capsule.total_characters, 0)
