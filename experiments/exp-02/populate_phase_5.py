"""Phase 5 — Estado Atual: implantacao parcial, risco de treinamento, bloqueios.

Idempotent. Enriched contents for lexical overlap.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    FactStatus,
    LearningState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    DocumentRecord,
    Episode,
    Fact,
    Learning,
    MemoryRelation,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    created: list[str] = []

    # --- Fact: deployment status ---
    fid_status = "fact-deployment-status"
    if store.get_memory(fid_status) is None:
        f = Fact(
            id=fid_status,
            project_id=project_id,
            content="A implantacao do sistema dual no Projeto Boreal esta parcial: "
            "os loggers IoT estao operacionais em 2 dos 3 centros de armazenamento "
            "(UBS Rio Verde e UBS Agua Fria). O centro UBS Belo Monte ainda utiliza "
            "o sistema antigo. Os 5000 indicadores VVM foram recebidos em 05/05/2026, "
            "mas ainda nao foram distribuidos para as rotas de transporte devido a "
            "pendencia de treinamento. A implantacao completa esta bloqueada ate que "
            "o treinamento das equipes seja concluido. O estado atual do projeto mostra "
            "progresso parcial com riscos significativos para o proximo ciclo.",
            assertion="Implantacao parcial: IoT em 2 de 3 centros, VVM recebidos mas nao distribuidos.",
            fact_status=FactStatus.CURRENT,
            scope="status-implantacao",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "UBS Rio Verde", "entity_type": "location"},
                {"name": "UBS Agua Fria", "entity_type": "location"},
                {"name": "UBS Belo Monte", "entity_type": "location"},
                {"name": "VVM", "entity_type": "equipment"},
            ],
            source_refs=[SourceRef(source_id="relatorio-status-20260515", source_type="report",
                                   description="Relatorio de status mensal").model_dump()],
        )
        store.save_memory(f)
        created.append(fid_status)

    # --- Learning: staff training gap ---
    lid_train = "lrn-staff-training-gap"
    if store.get_memory(lid_train) is None:
        ln = Learning(
            id=lid_train,
            project_id=project_id,
            content="A introducao de indicadores quimicos VVM exige treinamento "
            "presencial obrigatorio para todos os operadores de transporte. A tentativa "
            "de treinamento remoto por videoaula falhou: apenas 3 de 12 operadores "
            "conseguiram interpretar corretamente um VVM em teste pratico. Este "
            "aprendizado sobre a lacuna de treinamento e o principal bloqueio que "
            "impede a implantacao completa do sistema dual. Sem treinamento concluido, "
            "os VVM ja adquiridos nao podem ser distribuidos e as rotas de transporte "
            "para regioes frias permanecem suspensas, colocando em risco o proximo "
            "ciclo de vacinacao com 12.000 doses.",
            learning_state=LearningState.OBSERVED,
            origin_episode_ids=["epi-pilot-deploy"],
            evidence_ids=[],
            works_under_conditions="Treinamento presencial com pratica supervisionada",
            fails_under_conditions="Treinamento exclusivamente remoto ou apenas material impresso",
            generalization_degree="Especifico para tecnologias que exigem interpretacao visual",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "treinamento", "entity_type": "process"},
                {"name": "VVM", "entity_type": "equipment"},
            ],
        )
        store.save_memory(ln)
        created.append(lid_train)

    # --- Fact: training risk ---
    fid_risk = "fact-training-risk"
    if store.get_memory(fid_risk) is None:
        f = Fact(
            id=fid_risk,
            project_id=project_id,
            content="O principal risco que ainda pode atrasar a implantacao do Projeto "
            "Boreal e o atraso na aprovacao do material de treinamento para leitura "
            "de VVM. Este perigo pode melar a instalacao do sistema porque sem "
            "treinamento concluido, os VVM nao podem ser distribuidos. O proximo ciclo "
            "de vacinacao esta programado para 01/06/2026. Se o treinamento nao for "
            "concluido ate 25/05/2026, 12.000 doses poderao ser impactadas. A proxima "
            "acao prioritaria do projeto e concluir e aprovar o material didatico e "
            "agendar sessoes presenciais de capacitacao. A equipe deveria focar agora "
            "neste treinamento para avancar a implantacao.",
            assertion="Risco principal: atraso no treinamento pode impactar 12.000 doses.",
            fact_status=FactStatus.CURRENT,
            scope="riscos-projeto",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "treinamento", "entity_type": "process"},
                {"name": "VVM", "entity_type": "equipment"},
            ],
        )
        store.save_memory(f)
        created.append(fid_risk)

    # --- Checkpoint: Final ---
    cid_p5 = "chk-boreal-p5"
    if store.get_memory(cid_p5) is None:
        ck = Checkpoint(
            id=cid_p5,
            project_id=project_id,
            content="Checkpoint final do Projeto Boreal em 20/05/2026. O estado atual "
            "do projeto mostra implantacao parcial com 66% dos centros operacionais. "
            "VVM adquiridos mas bloqueados por falta de treinamento. Este checkpoint "
            "mostra tudo que mudou entre o primeiro checkpoint (apenas IoT) e o estado "
            "atual (sistema dual em implantacao). A proxima acao prioritaria e concluir "
            "o material de treinamento e agendar as capacitacoes presenciais. O principal "
            "bloqueio que impede a implantacao completa e a pendencia do material didatico. "
            "A equipe deve focar agora na aprovacao do treinamento para avancar.",
            current_state="Implantacao parcial. IoT em 2 de 3 centros. VVM em estoque. "
            "Equipes nao treinadas. Rotas frias suspensas.",
            last_completed_action="Recebimento dos 5000 VVM e tentativa de treinamento remoto",
            active_decisions=["dec-boreal-dual"],
            pending_items=["Aprovacao do material de treinamento",
                           "Treinamento presencial de 12 operadores",
                           "Distribuicao dos VVM para as rotas",
                           "Instalacao de IoT no terceiro centro"],
            blockers=["Material de treinamento pendente de aprovacao",
                      "Equipes sem capacitacao para uso de VVM"],
            artifacts_and_versions={"especificacao-sistema-dual": "v1.0",
                                    "material-treinamento-vvm": "rascunho v0.3"},
            next_allowed_action="Concluir e aprovar material de treinamento e agendar "
            "sessoes presenciais para todas as equipes",
            known_risks=["Impacto em 12.000 doses se treinamento atrasar",
                         "Resistencia a mudanca por operadores",
                         "Falha na interpretacao dos VVM"],
            deep_dive_refs=["doc-dual-spec", "lrn-staff-training-gap", "fact-training-risk"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
        )
        store.save_memory(ck)
        created.append(cid_p5)

    # --- Document: Training material ---
    docid_train = "doc-training-material"
    if store.get_memory(docid_train) is None:
        doc = DocumentRecord(
            id=docid_train,
            project_id=project_id,
            content="Material de Treinamento para Leitura de Indicadores VVM do Projeto "
            "Boreal. Rascunho em elaboracao (v0.3) incluindo guia visual dos estagios "
            "de cor do VVM, protocolo de decisao e exercicios praticos. Documento pendente "
            "de revisao pela coordenacao pedagogica e aprovacao final. Este material e "
            "essencial para viabilizar o treinamento presencial e destravar a implantacao.",
            document_type="training",
            sections=["Introducao ao VVM", "Estagios e Cores", "Protocolo de Decisao",
                      "Exercicios Praticos", "Registro Fotografico"],
            constituent_ids=[],
            is_normative=False,
            status=EpistemicStatus.PARTIALLY_SUPPORTED,
            confidence=Confidence.MEDIUM,
            entities=[
                {"name": "VVM", "entity_type": "equipment"},
                {"name": "treinamento", "entity_type": "process"},
            ],
            source_refs=[SourceRef(source_id="material-treinamento-vvm", source_type="training",
                                   description="Rascunho v0.3").model_dump()],
        )
        store.save_memory(doc)
        created.append(docid_train)

    # --- Episode: Pilot deployment ---
    epid_pilot = "epi-pilot-deploy"
    if store.get_memory(epid_pilot) is None:
        ep = Episode(
            id=epid_pilot,
            project_id=project_id,
            content="Tentativa de implantacao piloto do sistema dual na rota UBS Rio "
            "Verde para UBS Agua Fria em 08/05/2026. VVM foram afixados nas caixas "
            "termicas e operadores receberam videoaula de 20 minutos. Ao final, apenas "
            "3 de 12 operadores (25%) interpretaram corretamente os VVM. O treinamento "
            "remoto falhou porque a interpretacao visual requer pratica presencial "
            "supervisionada. Este episodio demonstrou que o treinamento presencial e "
            "obrigatorio e que o material didatico precisa de fotos reais em diferentes "
            "condicoes de iluminacao.",
            initial_state="VVM disponiveis, videoaula preparada, 12 operadores",
            goal="Validar fluxo operacional e verificar suficiencia do treinamento remoto",
            plan="Videoaula de 20 min + transporte real + avaliacao pratica com 5 VVM",
            actions=[
                "Producao e envio de videoaula",
                "Afixacao de VVM em 3 veiculos",
                "Rota UBS Rio Verde -> UBS Agua Fria (3h)",
                "Avaliacao pratica: cada operador classifica 5 VVM",
            ],
            observations=[
                "25% acertaram todos os 5 VVM",
                "50% acertaram 2 ou 3 VVM",
                "25% erraram todos, confundindo estagio 2 com 3",
                "Imagem na videoaula diferente da aparencia real",
            ],
            deviations=["Taxa de acerto de 25%, muito abaixo dos 80% minimos"],
            corrections=[
                "Suspensao do treinamento remoto",
                "Producao de material impresso com fotos reais",
                "Planejamento de sessoes presenciais",
            ],
            result="Falha do treinamento remoto. Treinamento presencial obrigatorio.",
            consequences="Atraso de 2 semanas. Risco de nao cumprir prazo do proximo ciclo.",
            learning_summary="Treinamento remoto insuficiente. Material presencial obrigatorio.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "VVM", "entity_type": "equipment"},
                {"name": "treinamento remoto", "entity_type": "process"},
            ],
            source_refs=[SourceRef(source_id="relatorio-piloto-20260508", source_type="report",
                                   description="Relatorio do teste piloto").model_dump()],
        )
        store.save_memory(ep)
        created.append(epid_pilot)

    # Relations
    relations: list[tuple[str, str, str, RelationType]] = [
        ("rel-27-factdep-der-decdual", fid_status, "dec-boreal-dual", RelationType.DERIVED_FROM),
        ("rel-28-lrntrain-der-epipilot", lid_train, epid_pilot, RelationType.DERIVED_FROM),
        ("rel-29-factrisk-cau-lrntrain", fid_risk, lid_train, RelationType.CAUSED_BY),
        ("rel-30-epipilot-occ-chkp4", epid_pilot, "chk-boreal-p4", RelationType.OCCURRED_DURING),
        ("rel-31-chkp5-sum-factdep", cid_p5, fid_status, RelationType.SUMMARIZES),
        ("rel-32-doctrain-ref-docspec", docid_train, "doc-dual-spec", RelationType.REFERENCES),
        ("rel-33-doctrain-sup-lrntrain", docid_train, lid_train, RelationType.SUPPORTED_BY),
        ("rel-34-chkp5-sum-factrisk", cid_p5, fid_risk, RelationType.SUMMARIZES),
    ]

    for rid, src, tgt, rtype in relations:
        existing = store.search_relations(source_id=src, target_id=tgt, relation_type=rtype)
        if not existing:
            rel = MemoryRelation(id=rid, source_id=src, target_id=tgt,
                                 relation_type=rtype, confidence=Confidence.HIGH)
            store.save_relation(rel)

    # Verify old decision state
    old_dec = store.get_memory("dec-boreal-iot")
    if old_dec and old_dec.superseded_by != "dec-boreal-dual":
        old_dec.superseded_by = "dec-boreal-dual"
        from mec_lab.domain.enums import DecisionStatus
        old_dec.decision_status = DecisionStatus.SUPERSEDED
        store.save_memory(old_dec)

    return created
