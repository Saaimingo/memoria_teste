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


class TestMetrics(unittest.TestCase):
    def test_precision(self) -> None:
        retrieved = ["f1", "f2", "f4"]
        expected = {"f1"}
        self.assertEqual(len(set(retrieved[:1]) & expected) / 1, 1.0)

    def test_hit(self) -> None:
        retrieved = ["f2", "f3", "f1"]
        expected = {"f1"}
        self.assertFalse(bool(set(retrieved[:1]) & expected))
        self.assertTrue(bool(set(retrieved[:3]) & expected))

    def test_mrr(self) -> None:
        retrieved = ["f2", "f1", "f3"]
        expected = {"f1"}
        mrr = 0.0
        for rank, rid in enumerate(retrieved, start=1):
            if rid in expected:
                mrr = 1.0 / rank
                break
        self.assertEqual(mrr, 0.5)

    def test_ndcg_perfect(self) -> None:
        retrieved = ["f1", "f2", "f3"]
        grades = {"f1": 3.0, "f2": 2.0, "f3": 1.0}
        ndcg = _compute_ndcg(retrieved, grades, k=3)
        self.assertAlmostEqual(ndcg, 1.0, places=2)

    def test_ndcg_zero(self) -> None:
        ndcg = _compute_ndcg(["f1"], {}, k=1)
        self.assertEqual(ndcg, 0.0)


class TestEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="Football calendar with FIFA dates",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f2", content="Financial alerts duplication after restart",
            project_id="proj-finance", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f3", content="Queue items duplicated after restart",
            project_id="proj-queue", status=EpistemicStatus.VERIFIED,
        ))
        self.dataset = EvalDataset(name="test", queries=[
            QueryCase(query_id="q1", query="football calendar", expected_ids=["f1"],
                      expected_project_id="proj-football", relevance_grades={"f1": 3.0}),
            QueryCase(query_id="q2", query="duplication restart", expected_ids=["f2", "f3"],
                      relevance_grades={"f2": 3.0, "f3": 3.0}),
            QueryCase(query_id="q3", query="nonexistent", expected_ids=[],
                      expected_missing=["absent"], relevance_grades={}),
        ])

    def test_evaluate(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(self.store, retriever)
        metrics = evaluator.evaluate(self.dataset)
        self.assertEqual(metrics.num_queries, 3)
        self.assertGreaterEqual(metrics.mrr, 0.0)
        self.assertLessEqual(metrics.mrr, 1.0)

    def test_per_query_results(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(self.store, retriever)
        metrics = evaluator.evaluate(self.dataset)
        self.assertEqual(len(metrics.per_query), 3)

    def test_capsule_metrics(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(self.store, retriever)
        metrics = evaluator.evaluate(self.dataset)
        self.assertGreaterEqual(metrics.capsule_avg_chars, 0)

    def test_fake_source_rate(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(self.store, retriever)
        metrics = evaluator.evaluate(self.dataset)
        # All retrieved should be real
        self.assertEqual(metrics.fake_source_count, 0)


class TestAblation(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="Football simulator with calendar",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))
        self.dataset = EvalDataset(name="test", queries=[
            QueryCase(query_id="q1", query="football calendar", expected_ids=["f1"],
                      expected_project_id="proj-football", relevance_grades={"f1": 3.0}),
        ])

    def test_variants_exist(self) -> None:
        self.assertGreaterEqual(len(ABLATION_VARIANTS), 6)

    def test_run_ablation(self) -> None:
        results = run_ablation(self.store, self.dataset, DeterministicSemanticAdapter())
        self.assertIn("full_mec", results)
        self.assertIn("no_semantic", results)


class TestEvalDataset(unittest.TestCase):
    def test_from_json(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".json")
        with open(fd, "w") as f:
            json.dump({
                "name": "test",
                "queries": [{"query_id": "q1", "query": "test", "expected_ids": ["id1"]}],
            }, f)
        try:
            dataset = EvalDataset.from_json(Path(path))
            self.assertEqual(dataset.name, "test")
            self.assertEqual(len(dataset.queries), 1)
        finally:
            Path(path).unlink(missing_ok=True)


class TestReport(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="Test", project_id="p1", status=EpistemicStatus.VERIFIED,
        ))
        self.dataset = EvalDataset(name="test", queries=[
            QueryCase(query_id="q1", query="test", expected_ids=["f1"],
                      expected_project_id="p1", relevance_grades={"f1": 3.0}),
        ])

    def test_generate_report(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(self.store, retriever)
        metrics = evaluator.evaluate(self.dataset)
        ablation = run_ablation(self.store, self.dataset, DeterministicSemanticAdapter())
        report = generate_report(metrics, ablation, "test", "0.1.0", "abc")
        self.assertIn("# MEC Lab", report)
        self.assertIn("Hit@1", report)
        self.assertIn("## Ablation Results", report)
        self.assertIn("## Limitations", report)
