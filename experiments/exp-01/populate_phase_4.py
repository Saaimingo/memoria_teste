"""Phase 4 — Current state: partial implementation, risks, next actions.

Idempotent: skips memories that already exist in the DB.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    EpistemicStatus,
    FactStatus,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    DocumentRecord,
    Fact,
    MemoryRelation,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    """Populate Phase 4 memories. Returns list of created IDs."""
    created: list[str] = []

    # --- Fact: partial implementation ---
    fid_impl = "fact-atlas-impl"
    if store.get_memory(fid_impl) is None:
        f = Fact(
            id=fid_impl,
            project_id=project_id,
            content="O consumidor de fila persistente está parcialmente implementado: "
            "consome eventos do Redis Streams, mas a confirmação de processamento "
            "(ack) ainda não é atômica — em caso de falha entre o envio da notificação "
            "e a gravação do ack, o evento pode ser reprocessado.",
            assertion="O consumidor de fila persistente está parcialmente implementado: "
            "ack ainda não é atômico.",
            fact_status=FactStatus.CURRENT,
            scope="implementacao",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "consumidor de fila", "entity_type": "component"},
                {"name": "ack não atômico", "entity_type": "limitation"},
            ],
            source_refs=[SourceRef(source_id="codigo-consumidor", source_type="code", description="Código atual do consumidor de fila").model_dump()],
        )
        store.save_memory(f)
        created.append(fid_impl)

    # --- Fact: risk still pending ---
    fid_risk = "fact-atlas-risk"
    if store.get_memory(fid_risk) is None:
        f = Fact(
            id=fid_risk,
            project_id=project_id,
            content="Risco pendente: a atomicidade do ack não está garantida. Se o processo "
            "morrer entre o envio da notificação e a confirmação de processamento, o evento "
            "será reentregue pela fila e poderá gerar notificação duplicada — o mesmo modo "
            "de falha que motivou a migração.",
            assertion="Risco pendente: ack não atômico pode reintroduzir duplicação de alertas.",
            fact_status=FactStatus.CURRENT,
            scope="riscos",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "risco de duplicação", "entity_type": "risk"},
                {"name": "atomicidade", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="analise-risco-ack", source_type="analysis", description="Análise de risco da não-atomicidade do ack").model_dump()],
        )
        store.save_memory(f)
        created.append(fid_risk)

    # --- Fact: next priority ---
    fid_next = "fact-atlas-next"
    if store.get_memory(fid_next) is None:
        f = Fact(
            id=fid_next,
            project_id=project_id,
            content="Próximo trabalho prioritário: implementar confirmação atômica usando "
            "transação Redis (MULTI/EXEC) ou padrão outbox para garantir que notificação "
            "e ack sejam uma operação indivisível.",
            assertion="Próximo trabalho: implementar ack atômico com transação Redis ou "
            "padrão outbox.",
            fact_status=FactStatus.CURRENT,
            scope="proximos-passos",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "ack atômico", "entity_type": "task"},
                {"name": "Redis", "entity_type": "technology"},
            ],
            source_refs=[SourceRef(source_id="planejamento-sprint", source_type="plan", description="Planejamento do próximo sprint").model_dump()],
        )
        store.save_memory(f)
        created.append(fid_next)

    # --- Document: architecture reference ---
    docid = "doc-atlas-arch"
    if store.get_memory(docid) is None:
        d = DocumentRecord(
            id=docid,
            project_id=project_id,
            content="Documento de Arquitetura do Projeto Atlas v2.0 — descreve a arquitetura "
            "atual baseada em fila persistente (Redis Streams), o modelo de processamento "
            "com confirmação, os componentes do sistema e os modos de falha conhecidos.",
            document_type="specification",
            sections=[
                "Visão Geral",
                "Arquitetura de Fila Persistente",
                "Modelo de Confirmação",
                "Componentes do Sistema",
                "Modos de Falha Conhecidos",
                "Plano de Migração",
            ],
            constituent_ids=[
                "dec-atlas-queue",
                "fact-atlas-impl",
                "fact-atlas-risk",
                "lrn-atlas-idem",
            ],
            is_normative=True,
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "documento de arquitetura", "entity_type": "document"},
                {"name": "Projeto Atlas", "entity_type": "project"},
            ],
            source_refs=[SourceRef(source_id="doc-arquitetura-v2", source_type="spec", description="Documento de arquitetura versão 2.0").model_dump()],
        )
        store.save_memory(d)
        created.append(docid)

    # --- Checkpoint 4 (final) ---
    cid = "chk-atlas-04"
    if store.get_memory(cid) is None:
        c = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Fase 4 — estado atual: implementação parcial da fila persistente. "
            "Consumidor funcional mas ack não atômico. Risco de duplicação ainda presente. "
            "Próximo passo: transação atômica para ack.",
            current_state="Fila persistente parcialmente implementada. Consumidor consome "
            "do Redis Streams e envia notificações. Ack não é atômico — risco remanescente "
            "de duplicação.",
            last_completed_action="Implementação do consumidor básico de Redis Streams e "
            "integração com o sistema de notificação.",
            active_decisions=["dec-atlas-queue"],
            pending_items=[
                "Implementar ack atômico (transação Redis ou outbox)",
                "Testar 100 ciclos de reinicialização para confirmar ausência de duplicação",
                "Configurar Redis em produção com persistência RDB+AOF",
            ],
            blockers=[
                "Ack não atômico impede garantia de entrega exatamente uma vez",
            ],
            next_allowed_action="Implementar confirmação atômica usando transação Redis "
            "(MULTI/EXEC) ou padrão outbox.",
            known_risks=[
                "Duplicação de alertas se processo morrer entre notificação e ack",
                "Complexidade operacional do Redis em produção",
                "Custo de infraestrutura adicional",
            ],
            artifacts_and_versions={
                "consumidor-fila": "v0.2.0-parcial",
                "doc-arquitetura": "v2.0",
            },
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "checkpoint", "entity_type": "milestone"},
                {"name": "Fase 4", "entity_type": "phase"},
            ],
        )
        store.save_memory(c)
        created.append(cid)

    # --- Relations ---
    relations = [
        # Document REFERENCES decisions
        ("rel-doc-ref-dec", docid, "dec-atlas-queue", RelationType.REFERENCES),
        # Checkpoint SUMMARIZES document
        ("rel-chk4-sum-doc", cid, docid, RelationType.SUMMARIZES),
        # Risk fact CAUSED_BY partial implementation
        ("rel-risk-caused-impl", fid_risk, fid_impl, RelationType.CAUSED_BY),
        # Next action fact REFERENCES the risk
        ("rel-next-ref-risk", fid_next, fid_risk, RelationType.REFERENCES),
        # Checkpoint REFERENCES next action fact
        ("rel-chk4-ref-next", cid, fid_next, RelationType.REFERENCES),
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
