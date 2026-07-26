"""Phase 2 — Problem observed: duplicate alerts after restart.

Idempotent: skips memories that already exist in the DB.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    EpistemicStatus,
    EvidenceType,
    HypothesisState,
    LearningState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Episode,
    Evidence,
    Hypothesis,
    Learning,
    MemoryRelation,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    """Populate Phase 2 memories into *store*. Returns list of created IDs."""
    created: list[str] = []

    # --- Episode: duplicate alerts after restart ---
    epid = "epi-atlas-dup"
    if store.get_memory(epid) is None:
        ep = Episode(
            id=epid,
            project_id=project_id,
            content="Episódio de duplicação: ao reiniciar o processador de lote após "
            "manutenção programada, todos os alertas das últimas 2 horas foram reenviados, "
            "gerando notificações duplicadas para os operadores.",
            initial_state="Processador em lote operando normalmente, alertas sendo enviados "
            "a cada 60 segundos.",
            goal="Reiniciar o serviço após manutenção sem gerar duplicação de alertas.",
            plan="Parar o serviço, aplicar patch de manutenção, religar o processador.",
            actions=["Parar processador de lote", "Aplicar manutenção", "Reiniciar processador"],
            observations=[
                "Após reinicialização, operadores reportaram receber os mesmos alertas duas vezes",
                "Logs mostram que eventos das últimas 2 horas foram reprocessados",
                "Volume de notificações dobrou no intervalo pós-reinicialização",
            ],
            deviations=["Serviço reprocessou eventos antigos em vez de retomar do ponto de parada"],
            corrections=["Limpeza manual da fila de notificações", "Notificação aos operadores sobre o incidente"],
            result="Operadores receberam alertas duplicados por aproximadamente 15 minutos até "
            "a limpeza manual. Nenhum alerta crítico foi perdido.",
            consequences="Confiança no sistema abalada. Time reconhece que o processamento em "
            "lote não possui mecanismo de idempotência nem checkpoint de retomada.",
            learning_summary="Processamento em lote sem idempotência causa duplicação de alertas "
            "quando o serviço é reiniciado, pois a posição de leitura não é preservada.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "duplicação", "entity_type": "failure_mode"},
                {"name": "reinicialização", "entity_type": "event"},
                {"name": "processador de lote", "entity_type": "component"},
            ],
            source_refs=[SourceRef(source_id="incidente-dup-2026-07-20", source_type="incident", description="Relatório de incidente de duplicação de alertas").model_dump()],
        )
        store.save_memory(ep)
        created.append(epid)

    # --- Evidence: log proving duplication ---
    eid_log = "evi-atlas-log"
    if store.get_memory(eid_log) is None:
        e = Evidence(
            id=eid_log,
            project_id=project_id,
            content="Trecho de log mostrando alerta #4821 enviado às 14:32 (pré-reinício) e "
            "reenviado às 14:47 (pós-reinício) com mesmo conteúdo e destinatário | "
            "Arquivo: /var/log/atlas/processor.log, linhas 2047-2053",
            evidence_type=EvidenceType.LOG,
            location="/var/log/atlas/processor.log",
            producer="Processador de lote do Projeto Atlas",
            environment="produção, Linux, Python 3.11",
            timestamp="2026-07-20T14:47:00Z",
            artifact_version="v0.1.0",
            integrity_hash="a3f2b1c9d8e7f6a5b4c3d2e1",
            supported_claims=["hyp-atlas-replay"],
            limitations="Log cobre apenas 1 instância do problema; pode haver outros modos de "
            "falha não capturados.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "log", "entity_type": "artifact"},
                {"name": "alerta #4821", "entity_type": "event"},
            ],
            source_refs=[SourceRef(source_id="processor-log", source_type="log", description="Log do processador durante incidente de duplicação").model_dump()],
        )
        store.save_memory(e)
        created.append(eid_log)

    # --- Hypothesis: replay cause ---
    hid_rep = "hyp-atlas-replay"
    if store.get_memory(hid_rep) is None:
        h = Hypothesis(
            id=hid_rep,
            project_id=project_id,
            content="A duplicação de alertas é causada pela ausência de checkpoint de posição "
            "de leitura: ao reiniciar, o processador relê todo o intervalo de eventos em vez "
            "de retomar do último ponto processado.",
            hypothesis_state=HypothesisState.SUSTAINED,
            origin_observation="Logs mostram que eventos com timestamp anterior à reinicialização "
            "foram reprocessados integralmente.",
            prediction="Se adicionarmos um marcador de posição (offset ou cursor) ao processador, "
            "a duplicação não ocorrerá em reinicializações futuras.",
            test_condition="Simular reinicialização com marcador de posição implementado e "
            "verificar se alertas não são duplicados.",
            confirmation_criterion="Zero alertas duplicados em 10 ciclos de parada e reinício.",
            rejection_criterion="Qualquer alerta duplicado durante os 10 ciclos de teste.",
            risk="O marcador de posição pode corromper se a gravação não for atômica.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "replay de eventos", "entity_type": "failure_mode"},
                {"name": "checkpoint de posição", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="analise-replay", source_type="analysis", description="Análise de causa raiz da duplicação").model_dump()],
        )
        store.save_memory(h)
        created.append(hid_rep)

    # --- Learning: idempotency ---
    lid = "lrn-atlas-idem"
    if store.get_memory(lid) is None:
        l = Learning(
            id=lid,
            project_id=project_id,
            content="Processadores baseados em lote precisam de mecanismo de idempotência "
            "ou checkpoint de posição para evitar reprocessamento de eventos já notificados "
            "após reinicialização.",
            learning_state=LearningState.PROMOTED,
            origin_episode_ids=[epid],
            evidence_ids=[eid_log],
            works_under_conditions="Idempotência garantida quando: (1) cada evento possui "
            "identificador único; (2) o processador consulta registro de eventos já enviados "
            "antes de notificar; (3) o registro é persistente.",
            fails_under_conditions="Sem identificador único por evento OU sem persistência "
            "do estado de processamento OU em cenários de reinicialização que perdem o "
            "registro de eventos já enviados.",
            generalization_degree="Aplica-se a qualquer sistema de notificação baseado em "
            "polling ou janela temporal que não mantenha estado de processamento.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "idempotência", "entity_type": "concept"},
                {"name": "checkpoint de posição", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="postmortem-dup", source_type="postmortem", description="Postmortem do incidente de duplicação").model_dump()],
        )
        store.save_memory(l)
        created.append(lid)

    # --- Checkpoint 2 ---
    cid = "chk-atlas-02"
    if store.get_memory(cid) is None:
        c = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Fase 2: incidente de duplicação após reinicialização documentado. "
            "Hipótese de replay confirmada. Aprendizado sobre idempotência registrado.",
            current_state="Incidente de duplicação ocorreu e foi analisado. Causa raiz "
            "identificada: ausência de checkpoint de posição no processamento em lote.",
            last_completed_action="Análise de causa raiz do incidente de duplicação, "
            "documentação do episódio e registro do aprendizado.",
            active_decisions=["dec-atlas-batch"],
            pending_items=[
                "Decidir se corrige o processamento em lote ou migra para fila persistente",
                "Implementar mecanismo de idempotência temporário",
            ],
            blockers=["Processamento em lote não possui checkpoint de posição"],
            next_allowed_action="Avaliar alternativas: corrigir lote com checkpoint ou "
            "migrar para fila persistente.",
            known_risks=[
                "Duplicação pode ocorrer novamente em qualquer reinicialização",
                "Operadores perderam confiança no sistema",
            ],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "checkpoint", "entity_type": "milestone"},
                {"name": "Fase 2", "entity_type": "phase"},
            ],
        )
        store.save_memory(c)
        created.append(cid)

    # --- Relations ---
    relations = [
        # Episode CAUSED_BY lack of idempotency → point to the learning
        ("rel-epi-caused-lrn", epid, lid, RelationType.CAUSED_BY),
        # Evidence SUPPORTED_BY hypothesis
        ("rel-log-sup-hyp", eid_log, hid_rep, RelationType.SUPPORTED_BY),
        # Hypothesis DERIVED_FROM episode
        ("rel-hyp-der-epi", hid_rep, epid, RelationType.DERIVED_FROM),
        # Learning DERIVED_FROM evidence
        ("rel-lrn-der-evi", lid, eid_log, RelationType.DERIVED_FROM),
        # Checkpoint SUMMARIZES episode
        ("rel-chk2-sum-epi", cid, epid, RelationType.SUMMARIZES),
        # Checkpoint REFERENCES learning
        ("rel-chk2-ref-lrn", cid, lid, RelationType.REFERENCES),
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
