"""Tests — Retrieval layer (unittest, rework R1)."""

import unittest

from mec_lab.domain.enums import MemoryType, RelationType, EpistemicStatus
from mec_lab.domain.models import Fact, Decision, MemoryRelation, ProjectRecord
from mec_lab.retrieval import (
    HybridRetriever,
    LexicalRetriever,
    RetrievalConfig,
    TfidfAdapter,
    extract_clues,
)
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Clue extraction
# ---------------------------------------------------------------------------


class TestClueExtraction(unittest.TestCase):
    def test_basic_terms(self) -> None:
        clues = extract_clues("simulador de futebol com calendário")
        # R3: terms are stemmed — "simulador" → "simul"
        self.assertIn("simul", clues.terms)
        self.assertNotIn("de", clues.terms)  # stopword removed

    def test_memory_type_hint_decision(self) -> None:
        clues = extract_clues("qual foi a decisão sobre o banco")
        self.assertEqual(clues.memory_type_hint, MemoryType.DECISION)

    def test_memory_type_hint_fact(self) -> None:
        clues = extract_clues("isso é um fato importante")
        self.assertEqual(clues.memory_type_hint, MemoryType.FACT)

    def test_project_hint_with_storage(self) -> None:
        s = Storage(":memory:")
        s.init_schema()
        s.save_project(ProjectRecord(name="Simulador de Futebol"))
        clues = extract_clues("projeto simulador de futebol", s)
        self.assertIsNotNone(clues.probable_project)

    def test_no_results_for_unrelated(self) -> None:
        clues = extract_clues("xyzabc123")
        self.assertIsNone(clues.memory_type_hint)

    def test_stopwords_filtered(self) -> None:
        """R1: verify stopwords are removed from terms."""
        clues = extract_clues("o que foi feito no projeto de futebol")
        for sw in ["o", "que", "foi", "no", "de"]:
            self.assertNotIn(sw, clues.terms)
        self.assertIn("futebol", clues.terms)

    # R2: behavioral tests for temporal / action hint triggers
    def test_historical_hint_antes(self) -> None:
        """R2: 'antes' triggers wants_historical even though it's a stopword."""
        clues = extract_clues("como era o calendario antes da mudanca")
        self.assertTrue(clues.wants_historical,
                        f"Expected wants_historical=True, got {clues.wants_historical}")

    def test_historical_hint_era(self) -> None:
        """R2: 'era' triggers wants_historical even though it's a stopword."""
        clues = extract_clues("o que era aquilo")
        self.assertTrue(clues.wants_historical)

    def test_current_hint_agora(self) -> None:
        """R2: 'agora' triggers wants_current even though it's a stopword."""
        clues = extract_clues("o que fazer agora")
        self.assertTrue(clues.wants_current)

    def test_current_hint_atual(self) -> None:
        """R2: 'atual' triggers wants_current."""
        clues = extract_clues("qual a regra atual")
        self.assertTrue(clues.wants_current)

    def test_action_hint_fazer(self) -> None:
        """R2: 'fazer' triggers wants_next_action even though it's a stopword."""
        clues = extract_clues("o que devo fazer")
        self.assertTrue(clues.wants_next_action)

    def test_action_hint_pendente(self) -> None:
        """R2: 'pendente' triggers wants_next_action."""
        clues = extract_clues("o que esta pendente")
        self.assertTrue(clues.wants_next_action)

    def test_no_hint_on_neutral_query(self) -> None:
        """R2: neutral query triggers no temporal/action hints."""
        clues = extract_clues("futebol calendario simulador")
        self.assertFalse(clues.wants_historical)
        self.assertFalse(clues.wants_current)
        self.assertFalse(clues.wants_next_action)

    def test_multiple_hints_together(self) -> None:
        """R2: a query may trigger multiple hint types simultaneously."""
        clues = extract_clues("antes de fazer o trabalho atual")
        self.assertTrue(clues.wants_historical)
        self.assertTrue(clues.wants_current)
        self.assertTrue(clues.wants_next_action)

    def test_terms_still_clean_with_hints(self) -> None:
        """R2: hint detection must not leak stopwords into clues.terms."""
        clues = extract_clues("como era o calendario antes da mudanca atual")
        for sw in ["como", "era", "o", "antes", "da"]:
            self.assertNotIn(sw, clues.terms,
                            f"Stopword '{sw}' leaked into terms: {clues.terms}")
        # R3: terms are stemmed — "calendario" → "calendari", "mudanca" → "mudanc", "atual" → "atu"
        self.assertIn("calendari", clues.terms)
        self.assertIn("mudanc", clues.terms)
        self.assertIn("atu", clues.terms)  # 'atual' stemmed to 'atu' via 'al' suffix


# ---------------------------------------------------------------------------
# Lexical retriever
# ---------------------------------------------------------------------------


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

    def test_stopwords_ignored(self) -> None:
        """R1: query with only stopwords should return no results."""
        retriever = LexicalRetriever(self.store)
        results = retriever.search("o que foi feito")
        self.assertEqual(len(results), 0)


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------


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
        # R1: add supersedes relation to test conflict detection
        self.store.save_memory(Fact(
            id="f4-old", content="Regra antiga: calendário fixo de 38 rodadas.",
            project_id="proj-football", status=EpistemicStatus.OBSOLETE,
            superseded_by="f4-new",
        ))
        self.store.save_memory(Fact(
            id="f4-new", content="Regra nova: calendário com pausas FIFA.",
            project_id="proj-football", status=EpistemicStatus.VERIFIED,
            supersedes="f4-old",
        ))
        self.store.save_relation(MemoryRelation(
            source_id="f4-new", target_id="f4-old", relation_type=RelationType.SUPERSEDES,
        ))
        self.store.save_relation(MemoryRelation(
            source_id="f3", target_id="f1", relation_type=RelationType.SIMILAR_TO,
        ))

    def test_basic_search(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("futebol calendário")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_result_structure(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("futebol")
        self.assertTrue(hasattr(result, "retrieved_facts"))
        self.assertTrue(hasattr(result, "explanation"))
        self.assertTrue(hasattr(result, "quality"))  # R1

    def test_score_decomposition(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("futebol")
        for cs in result.candidate_scores:
            self.assertIn("lexical", cs.explanation_decomposition)

    def test_explanation_non_empty(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("futebol")
        self.assertGreater(len(result.explanation), 0)

    def test_ablation_no_semantic(self) -> None:
        cfg = RetrievalConfig(enable_semantic=False, semantic_weight=0.0)
        retriever = HybridRetriever(self.store, config=cfg)
        result = retriever.search("futebol")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_ablation_no_typing(self) -> None:
        cfg = RetrievalConfig(enable_typing=False, type_weight=0.0, entity_weight=0.0)
        retriever = HybridRetriever(self.store, config=cfg)
        result = retriever.search("futebol")
        self.assertGreater(len(result.candidate_scores), 0)

    def test_type_filtering_decision(self) -> None:
        retriever = HybridRetriever(self.store)
        result = retriever.search("decisão sobre pygame")
        ids = [cs.memory_id for cs in result.candidate_scores]
        self.assertIn("d1", ids)

    # R1: new tests
    def test_conflict_detection_supersedes(self) -> None:
        """R1: supersedes relations should be detected as conflicts."""
        retriever = HybridRetriever(self.store)
        result = retriever.search("calendário regra", project_id="proj-football")
        self.assertGreater(len(result.conflicts), 0,
                          f"Expected conflicts for supersedes, got: {result.conflicts}")

    def test_quality_relevant(self) -> None:
        """R1: strong match should be 'relevant'."""
        retriever = HybridRetriever(self.store)
        result = retriever.search("futebol calendário FIFA")
        self.assertEqual(result.quality, "relevant")

    def test_quality_none_for_stopword_query(self) -> None:
        """R1: stopword-only query may still get weak graph signals."""
        retriever = HybridRetriever(self.store)
        result = retriever.search("o que foi isso")
        # With stopwords removed, no lexical signal; graph may give weak score
        self.assertIn(result.quality, ("absent", "weak"))


# ---------------------------------------------------------------------------
# TF-IDF Adapter (R1 replacement)
# ---------------------------------------------------------------------------


class TestTfidfAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_memory(Fact(
            id="f1", content="Football simulator with calendar and FIFA dates.",
            project_id="p1", status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f2", content="Financial alerts duplication after restart.",
            project_id="p2", status=EpistemicStatus.VERIFIED,
        ))

    def test_build_and_available(self) -> None:
        adapter = TfidfAdapter()
        self.assertFalse(adapter.is_available())
        adapter.build(self.store)
        self.assertTrue(adapter.is_available())

    def test_embed_returns_valid_vectors(self) -> None:
        adapter = TfidfAdapter(self.store)
        vecs = adapter.embed(["football calendar"])
        self.assertGreater(len(vecs), 0)
        self.assertGreater(len(vecs[0]), 0)

    def test_consistent_output(self) -> None:
        adapter = TfidfAdapter(self.store)
        v1 = adapter.embed(["football calendar"])[0]
        v2 = adapter.embed(["football calendar"])[0]
        self.assertEqual(v1, v2)

    def test_different_inputs_different_vectors(self) -> None:
        adapter = TfidfAdapter(self.store)
        v1 = adapter.embed(["football"])[0]
        v2 = adapter.embed(["finance"])[0]
        # Should be different vectors (not identical)
        if len(v1) > 0:
            self.assertNotEqual(v1, v2)

    def test_normalized_vectors(self) -> None:
        adapter = TfidfAdapter(self.store)
        v = adapter.embed(["football calendar"])[0]
        import math
        norm = math.sqrt(sum(x * x for x in v))
        self.assertAlmostEqual(norm, 1.0, places=2)
