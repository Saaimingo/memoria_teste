"""Tests — Behavioral tests for Rework R3 (vigência, ausência, próxima ação, risco, conflitos).

Covers the 9 required behavioral tests from PROMPT_REWORK_R3.md:
1. decisão atual supera a superseded com maior overlap literal
2. consulta histórica recupera a superseded
3. consulta sem evidência retorna absent e zero resultados úteis
4. relações isoladas não geram relevância
5. próxima ação prioriza memória pendente adequada
6. risco pendente é recuperável
7. consulta neutra não recebe bônus de intenção
8. conflito lógico não é duplicado
9. todos os 116 testes anteriores permanecem passando
"""

import unittest

from mec_lab.domain.enums import (
    DecisionStatus,
    EpistemicStatus,
    FactStatus,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    Fact,
    MemoryRelation,
    ProjectRecord,
)
from mec_lab.retrieval import (
    HybridRetriever,
    RetrievalConfig,
    extract_clues,
)
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# R3-1: Vigência vs obsolescência
# ---------------------------------------------------------------------------


class TestVigenciaSuperaObsoleta(unittest.TestCase):
    """R3-1: Current decision outranks superseded one even with lexical disadvantage."""

    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_project(ProjectRecord(id="proj-test", name="Projeto Teste"))
        # Old decision — has high lexical overlap with query about "processar"
        self.store.save_memory(Decision(
            id="dec-old",
            content="Processar dados em lote a cada 60 segundos com agrupamento por tipo.",
            project_id="proj-test",
            decision_status=DecisionStatus.SUPERSEDED,
            status=EpistemicStatus.SUPERSEDED,
            superseded_by="dec-new",
        ))
        # New decision — uses different vocabulary (about replacement, not processing)
        self.store.save_memory(Decision(
            id="dec-new",
            content="Substituir processamento em lote por fila persistente com confirmação individual.",
            project_id="proj-test",
            decision_status=DecisionStatus.ACTIVE,
            status=EpistemicStatus.VERIFIED,
            supersedes="dec-old",
        ))
        self.store.save_relation(MemoryRelation(
            source_id="dec-new", target_id="dec-old",
            relation_type=RelationType.SUPERSEDES,
        ))

    def test_consulta_vigente_prioriza_decisao_atual(self) -> None:
        """R3-1a: Current decision outranks superseded when query asks for current approach."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "Qual abordagem está vigente para processar dados?",
            project_id="proj-test",
        )
        top_ids = [cs.memory_id for cs in result.candidate_scores[:3]]
        self.assertEqual(
            top_ids[0], "dec-new",
            f"Expected dec-new (ACTIVE) at #1, got {top_ids[:3]}. "
            f"Superseded decision should not outrank active one."
        )

    def test_consulta_historica_recupera_superseded(self) -> None:
        """R3-2: Historical query recovers superseded decision."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "Como o sistema fazia isso antes da mudança?",
            project_id="proj-test",
        )
        top_ids = [cs.memory_id for cs in result.candidate_scores[:3]]
        self.assertIn(
            "dec-old", top_ids,
            f"Expected dec-old (SUPERSEDED) in top-3 for historical query, got {top_ids[:3]}"
        )


# ---------------------------------------------------------------------------
# R3-2: Ausência real de evidência
# ---------------------------------------------------------------------------


class TestAusenciaRealDeEvidencia(unittest.TestCase):
    """R3-2: Absence detection — no fabrication of relevance from isolated relations."""

    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_project(ProjectRecord(id="proj-test", name="Test"))
        # A few connected memories about a different topic
        self.store.save_memory(Fact(
            id="f-sports",
            content="O time de futebol venceu o campeonato nacional.",
            project_id="proj-test",
            status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_memory(Fact(
            id="f-calendar",
            content="Calendário esportivo inclui 38 rodadas.",
            project_id="proj-test",
            status=EpistemicStatus.VERIFIED,
        ))
        self.store.save_relation(MemoryRelation(
            source_id="f-sports", target_id="f-calendar",
            relation_type=RelationType.REFERENCES,
        ))
        self.store.save_relation(MemoryRelation(
            source_id="f-calendar", target_id="f-sports",
            relation_type=RelationType.SUPPORTED_BY,
        ))

    def test_consulta_sem_evidencia_retorna_absent(self) -> None:
        """R3-3: Query on absent topic returns 'absent' quality and no useful results."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "Existe decisão registrada sobre criptografia ponta a ponta?",
            project_id="proj-test",
        )
        self.assertEqual(
            result.quality, "absent",
            f"Expected 'absent' for query on non-existent topic, got '{result.quality}'"
        )

    def test_relacoes_isoladas_nao_geram_relevancia(self) -> None:
        """R3-4: Isolated relations don't fabricate relevance for unrelated queries."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "criptografia segurança dados",
            project_id="proj-test",
        )
        # Even though f-sports and f-calendar are connected by relations,
        # a query about cryptography should not make them relevant
        self.assertEqual(
            result.quality, "absent",
            f"Expected 'absent' — isolated relations should not fabricate relevance. "
            f"Got quality='{result.quality}', top scores: "
            f"{[(cs.memory_id, cs.total_score) for cs in result.candidate_scores[:3]]}"
        )


# ---------------------------------------------------------------------------
# R3-3: Próxima ação e risco pendente
# ---------------------------------------------------------------------------


class TestNextActionRisk(unittest.TestCase):
    """R3-3: Next action and pending risk retrieval."""

    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_project(ProjectRecord(id="proj-test", name="Test"))
        # Fact about next work
        self.store.save_memory(Fact(
            id="fact-next",
            content="O próximo trabalho prioritário é implementar confirmação atômica "
            "usando transação ou padrão outbox.",
            project_id="proj-test",
            fact_status=FactStatus.CURRENT,
            status=EpistemicStatus.VERIFIED,
        ))
        # Fact about risk
        self.store.save_memory(Fact(
            id="fact-risk",
            content="Risco: a atomicidade do ack não está garantida. Se o processo "
            "morrer entre notificação e confirmação, o evento será reentregue.",
            project_id="proj-test",
            fact_status=FactStatus.CURRENT,
            status=EpistemicStatus.VERIFIED,
        ))
        # Checkpoint with next/pending info
        self.store.save_memory(Checkpoint(
            id="chk-1",
            content="Checkpoint do projeto: fila implementada, falta ack atômico.",
            project_id="proj-test",
            current_state="Em desenvolvimento",
            pending_items=["Implementar ack atômico"],
            blockers=["Risco de reentrega de eventos"],
            next_allowed_action="Implementar confirmação atômica",
            known_risks=["Atomicidade do ack não garantida"],
        ))
        # Unrelated memories for noise
        self.store.save_memory(Fact(
            id="fact-other",
            content="O sistema usa Redis como armazenamento principal.",
            project_id="proj-test",
            status=EpistemicStatus.VERIFIED,
        ))

    def test_proxima_acao_prioriza_memoria_pendente(self) -> None:
        """R3-5: Next action query prioritizes pending-action memory."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "Em que devo trabalhar agora?",
            project_id="proj-test",
        )
        top_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
        self.assertIn(
            "fact-next", top_ids[:3],
            f"Expected fact-next in top-3 for next action query, got top-5: {top_ids}"
        )

    def test_risco_pendente_e_recuperavel(self) -> None:
        """R3-6: Pending risk is retrievable."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "Qual risco ainda impede a conclusão do projeto?",
            project_id="proj-test",
        )
        top_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
        self.assertIn(
            "fact-risk", top_ids[:3],
            f"Expected fact-risk in top-3 for risk query, got top-5: {top_ids}"
        )

    def test_consulta_neutra_nao_recebe_bonus_intencao(self) -> None:
        """R3-7: Neutral query doesn't receive intent bonuses."""
        # First, verify a neutral query doesn't trigger hints
        clues = extract_clues("descreva o sistema de armazenamento", self.store)
        self.assertFalse(clues.wants_current)
        self.assertFalse(clues.wants_historical)
        self.assertFalse(clues.wants_next_action)
        self.assertFalse(clues.wants_risk)
        self.assertFalse(clues.wants_blocker)

        # Now verify ranking: fact-other should rank well on its own lexical merit
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "descreva o sistema de armazenamento",
            project_id="proj-test",
        )
        top_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
        # fact-other ("O sistema usa Redis...") should rank well lexically
        self.assertIn("fact-other", top_ids[:3],
                      f"Neutral query should rank fact-other by lexical merit, got: {top_ids[:5]}")


# ---------------------------------------------------------------------------
# R3-4: Conflitos (deduplication)
# ---------------------------------------------------------------------------


class TestConflictDedup(unittest.TestCase):
    """R3-4: Conflict detection should not duplicate the same logical conflict."""

    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()
        self.store.save_project(ProjectRecord(id="proj-test", name="Test"))
        # Old decision (superseded)
        self.store.save_memory(Decision(
            id="dec-old",
            content="Processar em lote.",
            project_id="proj-test",
            decision_status=DecisionStatus.SUPERSEDED,
            status=EpistemicStatus.SUPERSEDED,
            superseded_by="dec-new",
        ))
        # New decision (active)
        self.store.save_memory(Decision(
            id="dec-new",
            content="Processar em fila.",
            project_id="proj-test",
            decision_status=DecisionStatus.ACTIVE,
            status=EpistemicStatus.VERIFIED,
            supersedes="dec-old",
        ))
        self.store.save_relation(MemoryRelation(
            source_id="dec-new", target_id="dec-old",
            relation_type=RelationType.SUPERSEDES,
        ))

    def test_conflito_logico_nao_duplicado(self) -> None:
        """R3-8: The same logical conflict is not reported multiple times."""
        retriever = HybridRetriever(self.store)
        result = retriever.search(
            "processamento de dados",
            project_id="proj-test",
        )

        # Count STATE_CONFLICT entries — should be at most 1 (for dec-old)
        state_conflicts = [c for c in result.conflicts if c.startswith("STATE_CONFLICT")]
        self.assertLessEqual(
            len(state_conflicts), 1,
            f"Expected at most 1 STATE_CONFLICT, got {len(state_conflicts)}: {state_conflicts}"
        )

        # Count CONFLICT entries referencing SUPERSEDES — should be at most 1
        supersedes_conflicts = [c for c in result.conflicts if "SUPERSEDES" in c]
        self.assertLessEqual(
            len(supersedes_conflicts), 1,
            f"Expected at most 1 SUPERSEDES conflict, got {len(supersedes_conflicts)}: {supersedes_conflicts}"
        )

        # The old approach fired 2 separate entries (STATE_CONFLICT + superseded_by line)
        # R3 merges them into 1 entry
        for c in result.conflicts:
            if c.startswith("STATE_CONFLICT"):
                # The STATE_CONFLICT line should include superseded_by inline
                self.assertIn("superseded_by", c,
                              f"STATE_CONFLICT should inline superseded_by info. Got: {c}")


# ---------------------------------------------------------------------------
# Additional R3 clue detection tests
# ---------------------------------------------------------------------------


class TestR3ClueExtraction(unittest.TestCase):
    """R3: Verify new clue extraction triggers."""

    def test_risk_words_detected(self) -> None:
        clues = extract_clues("qual risco impede a conclusao")
        self.assertTrue(clues.wants_risk, f"Expected wants_risk=True, got {clues.wants_risk}")

    def test_blocker_words_detected(self) -> None:
        clues = extract_clues("o que esta bloqueando a finalizacao")
        self.assertTrue(clues.wants_blocker, f"Expected wants_blocker=True, got {clues.wants_blocker}")

    def test_absence_words_detected(self) -> None:
        clues = extract_clues("existe decisao registrada sobre isso")
        self.assertTrue(clues.needs_absence, f"Expected needs_absence=True, got {clues.needs_absence}")

    def test_multiple_r3_hints(self) -> None:
        clues = extract_clues("existe risco pendente que bloqueia a conclusao")
        self.assertTrue(clues.wants_risk)
        self.assertTrue(clues.needs_absence)
