"""Tests — Retrieval layer (unittest)."""

import unittest

from mec_lab.domain.enums import MemoryType, RelationType, EpistemicStatus
from mec_lab.domain.models import Fact, Decision, MemoryRelation
from mec_lab.retrieval import (
    DeterministicSemanticAdapter,
    HybridRetriever,
    LexicalRetriever,
    NullSemanticAdapter,
    RetrievalConfig,
    extract_clues,
)
from mec_lab.storage import Storage


class TestClueExtraction(unittest.TestCase):
    def test_basic_terms(self) -> None:
        clues = extract_clues("simulador de futebol com calendário")
        self.assertIn("simulador", clues.terms)

    def test_memory_type_hint_decision(self) -> None:
        clues = extract_clues("qual foi a decisão sobre o banco")
        self.assertEqual(clues.memory_type_hint, MemoryType.DECISION)

    def test_memory_type_hint_fact(self) -> None:
        clues = extract_clues("isso é um fato importante")
        self.assertEqual(clues.memory_type_hint, MemoryType.FACT)

    def test_project_hint_with_storage(self) -> None:
        s = Storage(":memory:")
        s.init_schema()
        from mec_lab.domain.models import ProjectRecord
        s.save_project(ProjectRecord(name="Simulador de Futebol"))
        clues = extract_clues("projeto simulador de futebol", s)
        self.assertIsNotNone(clues.probable_project)

    def test_no_results_for_unrelated(self) -> None:
        clues = extract_clues("xyzabc123")
        # The term matches regex, but there should be no meaningful entities or type hints
        self.assertIsNone(clues.memory_type_hint)
        self.assertIsNone(clues.probable_project)


class TestLexicalRetriever(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="O simulador de futebol usa calendário com data FIFA.",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f2", content="Sistema financeiro processa alertas em tempo real.",
            project_id="proj-finance", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Decision(
            id="d1", content="Usar Python com Pygame para o protótipo.",
            project_id="proj-football", authority="Saimon", justification="J",
        ))

    def test_basic_search(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("futebol calendário")
        self.assertGreater(len(results), 0)

    def test_project_filter(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("alertas", project_id="proj-finance")
        for mem, _ in results:
            self.assertEqual(mem.project_id, "proj-finance")

    def test_no_results(self) -> None:
        retriever = LexicalRetriever(self.store)
        results = retriever.search("xyzabc123")
        self.assertEqual(len(results), 0)


class TestHybridRetriever(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="O simulador de futebol usa calendário com 38 rodadas e data FIFA.",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f2", content="Jogadores se aposentam após 15 temporadas.",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f3", content="Alertas duplicados após reinicialização do sistema financeiro.",
            project_id="proj-finance", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Decision(
            id="d1", content="Usar Python com Pygame para o protótipo.",
            project_id="proj-football", authority="Saimon", justification="J",
        ))
        self.store.save_relation(MemoryRelation(
            source_id="f3", target_id="f1", relation_type=RelationType.SIMILAR_TO,
        ))

    def test_basic_search(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("futebol calendário")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_result_structure(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("futebol")
        self.assertTrue(hasattr(result, "retrieved_facts"))
        self.assertTrue(hasattr(result, "explanation"))
        self.assertTrue(hasattr(result, "conflicts"))
        self.assertTrue(hasattr(result, "inferences"))

    def test_score_decomposition(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("futebol")
        for cs in result.candidate_scores:
            self.assertIn("lexical", cs.explanation_decomposition)

    def test_explanation_non_empty(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("futebol")
        self.assertGreater(len(result.explanation), 0)

    def test_ablation_no_semantic(self) -> None:
        cfg = RetrievalConfig(enable_semantic=False, semantic_weight=0.0)
        retriever = HybridRetriever(self.store, config=cfg, semantic=NullSemanticAdapter())
        result = retriever.search("futebol")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_ablation_no_typing(self) -> None:
        cfg = RetrievalConfig(enable_typing=False, type_weight=0.0, entity_weight=0.0)
        retriever = HybridRetriever(self.store, config=cfg, semantic=DeterministicSemanticAdapter())
        result = retriever.search("futebol")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_type_filtering_decision(self) -> None:
        retriever = HybridRetriever(self.store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("decisão sobre pygame")
        ids = [cs.memory_id for cs in result.candidate_scores]
        self.assertIn("d1", ids)


class TestSemanticAdapters(unittest.TestCase):
    def test_null_adapter(self) -> None:
        a = NullSemanticAdapter(dimension=4)
        vecs = a.embed(["test"])
        self.assertEqual(len(vecs[0]), 4)
        self.assertFalse(a.is_available())

    def test_deterministic_available(self) -> None:
        a = DeterministicSemanticAdapter()
        self.assertTrue(a.is_available())

    def test_deterministic_consistent(self) -> None:
        a = DeterministicSemanticAdapter(dimension=32)
        v1 = a.embed(["hello world"])[0]
        v2 = a.embed(["hello world"])[0]
        self.assertEqual(v1, v2)
