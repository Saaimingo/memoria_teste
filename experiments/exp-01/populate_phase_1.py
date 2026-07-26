"""Phase 1 — Initial decision: Projeto Atlas adopts batch processing.

Idempotent: skips memories that already exist in the DB.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EvidenceType,
    FactStatus,
    HypothesisState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    Evidence,
    Fact,
    Hypothesis,
    MemoryRelation,
    ProjectRecord,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    """Populate Phase 1 memories into *store*. Returns list of created IDs."""
    created: list[str] = []

    # --- Project ---
    proj = ProjectRecord(
        id=project_id,
        name="Projeto Atlas",
        description="Sistema de alertas operacionais com processamento confiável de eventos",
    )
    if store.get_project(project_id) is None:
        store.save_project(proj)

    # --- Fact: objective ---
    fid = "fact-atlas-obj"
    if store.get_memory(fid) is None:
        f = Fact(
            id=fid,
            project_id=project_id,
            content="O Projeto Atlas tem como objetivo construir um sistema de alertas "
            "operacionais que notifique automaticamente desvios de métricas em tempo real.",
            assertion="O Projeto Atlas tem como objetivo construir um sistema de alertas "
            "operacionais que notifique automaticamente desvios de métricas em tempo real.",
            fact_status=FactStatus.CURRENT,
            scope="alertas-operacionais",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "Projeto Atlas", "entity_type": "project"},
                {"name": "alerta", "entity_type": "concept"},
                {"name": "métrica", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="especificacao-inicial", source_type="spec", description="Especificação inicial do Projeto Atlas").model_dump()],
        )
        store.save_memory(f)
        created.append(fid)

    # --- Decision: batch processing ---
    did = "dec-atlas-batch"
    if store.get_memory(did) is None:
        d = Decision(
            id=did,
            project_id=project_id,
            content="Processar alertas em lote a cada 60 segundos, agrupando eventos por "
            "tipo de métrica antes do envio das notificações.",
            decision_status=DecisionStatus.ACTIVE,
            authority="Arquiteto do Projeto Atlas",
            alternatives=[
                "Processamento em lote a cada 60s",
                "Processamento por fluxo contínuo (streaming)",
                "Processamento sob demanda via API",
            ],
            justification="Processamento em lote é mais simples de implementar, não requer "
            "infraestrutura de fila persistente e atende ao requisito de latência máxima de "
            "2 minutos para notificações. A alternativa de streaming exigiria um broker de "
            "mensagens que o time ainda não domina.",
            expected_consequences="Sistema mais simples, com menor custo operacional inicial. "
            "Latência máxima de 60 segundos para notificações.",
            revocation_criteria="Se aparecerem alertas duplicados, perda de eventos ou se a "
            "latência de 60 segundos se mostrar insuficiente para ambientes de produção.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "Processamento em lote", "entity_type": "concept"},
                {"name": "alerta", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="reuniao-arquitetura-01", source_type="meeting", description="Reunião de arquitetura — decisão de batch").model_dump()],
        )
        store.save_memory(d)
        created.append(did)

    # --- Evidence: benchmark supporting batch ---
    eid = "evi-atlas-bench"
    if store.get_memory(eid) is None:
        e = Evidence(
            id=eid,
            project_id=project_id,
            content="Benchmark local: processamento em lote atinge 1000 alertas/segundo | "
            "Ambiente de homologação com 50 métricas ativas, sem perda de eventos.",
            evidence_type=EvidenceType.BENCHMARK,
            location="homologacao/benchmark-batch-2026-07.csv",
            producer="Equipe de QA do Projeto Atlas",
            environment="homologação, Python 3.11, SQLite, single-node",
            timestamp="2026-07-15T10:00:00Z",
            supported_claims=["dec-atlas-batch"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "benchmark", "entity_type": "artifact"},
                {"name": "Processamento em lote", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="benchmark-batch", source_type="test", description="Resultados de benchmark do processamento em lote").model_dump()],
        )
        store.save_memory(e)
        created.append(eid)

    # --- Hypothesis: capacity ---
    hid = "hyp-atlas-cap"
    if store.get_memory(hid) is None:
        h = Hypothesis(
            id=hid,
            project_id=project_id,
            content="O processamento em lote suportará até 500 métricas ativas sem degradação "
            "de latência superior a 2 minutos.",
            hypothesis_state=HypothesisState.PROPOSED,
            origin_observation="Benchmark mostrou 1000 alertas/segundo com 50 métricas; "
            "extrapolação linear sugere margem para 500 métricas.",
            prediction="Com 500 métricas ativas, a latência não excederá 120 segundos.",
            test_condition="Simular 500 métricas gerando eventos a cada 30 segundos e medir "
            "latência de ponta a ponta durante 1 hora.",
            confirmation_criterion="Latência p99 abaixo de 120 segundos por 1 hora contínua.",
            rejection_criterion="Latência p99 acima de 120 segundos ou perda de mais de 1% "
            "dos eventos.",
            risk="Extrapolação linear pode não se manter; filas internas podem saturar.",
            status=EpistemicStatus.PARTIALLY_SUPPORTED,
            confidence=Confidence.MEDIUM,
            entities=[
                {"name": "hipótese de capacidade", "entity_type": "concept"},
                {"name": "latência", "entity_type": "metric"},
            ],
            source_refs=[SourceRef(source_id="analise-capacidade", source_type="analysis", description="Análise de capacidade baseada em benchmark").model_dump()],
        )
        store.save_memory(h)
        created.append(hid)

    # --- Checkpoint 1 ---
    cid = "chk-atlas-01"
    if store.get_memory(cid) is None:
        c = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Fase 1 concluída: decisão por processamento em lote registrada, "
            "benchmark executado, hipótese de capacidade formulada.",
            current_state="Arquitetura definida: processamento em lote a cada 60 segundos. "
            "Benchmark executado com 50 métricas, 1000 alertas/s sem perda.",
            last_completed_action="Execução de benchmark em homologação e registro da decisão "
            "de arquitetura.",
            active_decisions=["dec-atlas-batch"],
            pending_items=["Implementar processador de lote", "Testar com 500 métricas"],
            blockers=[],
            next_allowed_action="Implementar o processador de lote conforme decisão vigente.",
            known_risks=["Hipótese de capacidade ainda não confirmada para 500 métricas"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "checkpoint", "entity_type": "milestone"},
                {"name": "Fase 1", "entity_type": "phase"},
            ],
        )
        store.save_memory(c)
        created.append(cid)

    # --- Relations ---
    relations = [
        # Evidence SUPPORTS Decision (using SUPPORTED_BY)
        ("rel-evi-bench-sup-dec", eid, did, RelationType.SUPPORTED_BY),
        # Hypothesis DERIVED_FROM Evidence
        ("rel-hyp-cap-der-evi", hid, eid, RelationType.DERIVED_FROM),
        # Checkpoint SUMMARIZES phase 1 state
        ("rel-chk-sum-dec", cid, did, RelationType.SUMMARIZES),
        # Hypothesis REFERENCES Checkpoint
        ("rel-hyp-ref-chk", hid, cid, RelationType.REFERENCES),
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
