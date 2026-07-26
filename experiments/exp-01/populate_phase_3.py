"""Phase 3 — Decision change: replace batch with persistent queue.

Idempotent: skips memories that already exist in the DB.
IMPORTANT: Mutates dec-atlas-batch status to SUPERSEDED.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EvidenceType,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    Evidence,
    MemoryRelation,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    """Populate Phase 3 memories. Returns list of created IDs."""
    created: list[str] = []

    # --- Mutate old decision: mark as SUPERSEDED ---
    old_dec = store.get_memory_by_type("dec-atlas-batch", MemoryType.DECISION)
    if old_dec is not None and getattr(old_dec, "decision_status", None) != "superseded":
        old_dec.decision_status = DecisionStatus.SUPERSEDED  # type: ignore[attr-defined]
        old_dec.status = EpistemicStatus.SUPERSEDED
        old_dec.superseded_by = "dec-atlas-queue"
        store.save_memory(old_dec)

    # --- New Decision: persistent queue ---
    did = "dec-atlas-queue"
    if store.get_memory(did) is None:
        d = Decision(
            id=did,
            project_id=project_id,
            content="Substituir processamento em lote por fila persistente com "
            "confirmação de processamento. Cada evento será consumido individualmente "
            "da fila e marcado como processado antes do envio da notificação.",
            decision_status=DecisionStatus.ACTIVE,
            authority="Arquiteto do Projeto Atlas, após postmortem do incidente de duplicação",
            alternatives=[
                "Fila persistente com confirmação (escolhida)",
                "Processamento em lote com checkpoint de offset",
                "Streaming com Apache Kafka",
            ],
            justification="O processamento em lote falhou em produção ao gerar alertas "
            "duplicados após reinicialização. A fila persistente garante que cada evento "
            "seja processado exatamente uma vez, eliminando a causa raiz do incidente. "
            "A alternativa de adicionar checkpoint ao lote foi considerada, mas a fila "
            "oferece garantias mais fortes e é padrão da indústria para este cenário.",
            expected_consequences="Eliminação de alertas duplicados. Maior confiabilidade. "
            "Latência reduzida para near-real-time. Aumento de complexidade operacional "
            "pela introdução do broker de filas.",
            revocation_criteria="Se a fila introduzir latência superior a 10 segundos no "
            "percentil 99 ou se o custo operacional do broker se mostrar proibitivo.",
            supersedes="dec-atlas-batch",
            superseded_decision_id="dec-atlas-batch",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "fila persistente", "entity_type": "concept"},
                {"name": "processamento individual", "entity_type": "concept"},
                {"name": "confirmação de processamento", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="postmortem-dup", source_type="postmortem", description="Postmortem do incidente de duplicação — motivou a mudança").model_dump()],
        )
        store.save_memory(d)
        created.append(did)

    # --- Evidence: queue benchmark ---
    eid = "evi-atlas-queue-bench"
    if store.get_memory(eid) is None:
        e = Evidence(
            id=eid,
            project_id=project_id,
            content="Benchmark de fila persistente (Redis Streams): 5000 eventos/segundo "
            "com latência p99 de 3 segundos, zero duplicações em 100 ciclos de "
            "reinicialização. | Ambiente de homologação, 200 métricas ativas.",
            evidence_type=EvidenceType.BENCHMARK,
            location="homologacao/benchmark-queue-2026-07.csv",
            producer="Equipe de QA do Projeto Atlas",
            environment="homologação, Python 3.11, Redis 7.2, single-node",
            timestamp="2026-07-22T15:00:00Z",
            supported_claims=["dec-atlas-queue"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "Redis Streams", "entity_type": "technology"},
                {"name": "benchmark de fila", "entity_type": "artifact"},
            ],
            source_refs=[SourceRef(source_id="benchmark-queue", source_type="test", description="Benchmark da fila persistente com Redis Streams").model_dump()],
        )
        store.save_memory(e)
        created.append(eid)

    # --- Checkpoint 3 ---
    cid = "chk-atlas-03"
    if store.get_memory(cid) is None:
        c = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Fase 3 concluída: decisão de migrar para fila persistente registrada. "
            "Processamento em lote marcado como obsoleto. Benchmark da fila executado.",
            current_state="Arquitetura redefinida: fila persistente com confirmação. "
            "Processamento em lote descontinuado. Decisão antiga formalmente substituída "
            "(SUPERSEDES).",
            last_completed_action="Registro da nova decisão de arquitetura, benchmark da "
            "fila persistente, marcação da decisão antiga como SUPERSEDED.",
            active_decisions=["dec-atlas-queue"],
            pending_items=[
                "Implementar consumidor de fila persistente",
                "Migrar processador de lote para consumidor de fila",
                "Configurar broker Redis em produção",
            ],
            blockers=[],
            next_allowed_action="Implementar o consumidor de fila persistente e migrar o "
            "código do processador.",
            known_risks=[
                "Complexidade operacional adicional com Redis",
                "Custo de infraestrutura do broker",
            ],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "checkpoint", "entity_type": "milestone"},
                {"name": "Fase 3", "entity_type": "phase"},
            ],
        )
        store.save_memory(c)
        created.append(cid)

    # --- Relations ---
    relations = [
        # New decision SUPERSEDES old decision
        ("rel-queue-sup-batch", did, "dec-atlas-batch", RelationType.SUPERSEDES),
        # Evidence SUPPORTED_BY decision
        ("rel-qbench-sup-dec", eid, did, RelationType.SUPPORTED_BY),
        # Checkpoint SUMMARIZES new state
        ("rel-chk3-sum-dec", cid, did, RelationType.SUMMARIZES),
        # New decision REFERENCES the learning from phase 2
        ("rel-dec-ref-lrn", did, "lrn-atlas-idem", RelationType.REFERENCES),
        # Evidence REFERENCES old evidence (comparison)
        ("rel-qbench-ref-bbench", eid, "evi-atlas-bench", RelationType.REFERENCES),
    ]

    for rid, src, tgt, rtype in relations:
        if not store.search_relations(source_id=src, target_id=tgt, relation_type=rtype):
            rel = MemoryRelation(
                id=rid,
                source_id=src,
                target_id=tgt,
                relation_type=rtype,
                confidence=Confidence.HIGH,
            )
            store.save_relation(rel)

    return created
