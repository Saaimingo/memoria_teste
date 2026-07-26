"""Phase 2 — Problema Observado: excursao de temperatura e lacuna de dados.

Idempotent. Enriched contents for lexical overlap with queries.
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
    created: list[str] = []

    # --- Episode: temperature excursion ---
    epid = "epi-transport-excursion"
    if store.get_memory(epid) is None:
        ep = Episode(
            id=epid,
            project_id=project_id,
            content="Episodio critico de excursao de temperatura durante o transporte de "
            "vacinas para a UBS Belo Monte em 15/03/2026. O logger IoT registrou aquecimento "
            "acima de 8C por 2 horas, seguido de um apagao de dados de 4 horas sem nenhum "
            "registro — uma falha de monitoramento que resultou no descarte de 200 doses. "
            "Este episodio foi a causa principal do abandono da abordagem inicial com apenas "
            "loggers IoT. A falha de dados ocorreu exatamente no trecho mais frio da rota "
            "onde a temperatura externa estava entre -12C e -18C. O palpite inicial foi que "
            "as baterias falharam no frio extremo, parando os registros temporariamente. "
            "A decisao de usar apenas loggers IoT foi questionada apos este incidente.",
            initial_state="Rota de 8h entre armazem central e UBS Belo Monte, temp externa -15C",
            goal="Entregar 200 doses de vacina com integridade termica comprovada",
            plan="Transporte em caixa termica passiva monitorada por logger TL-2000",
            actions=[
                "Carregamento da caixa termica as 06:00",
                "Verificacao inicial do logger: bateria 95%",
                "Inicio do transporte as 06:30",
            ],
            observations=[
                "09:15: temperatura 9.1C (acima do limite de 8C)",
                "09:30: temperatura 11.4C",
                "09:45: ultimo registro valido 8.2C",
                "09:45 as 13:45: lacuna de dados de 4 horas",
                "13:50: logger voltou com temperatura 3.5C",
                "Temp externa na rota: -12C a -18C",
            ],
            deviations=[
                "Excurso de temperatura acima de 8C por 2 horas",
                "Lacuna de dados de 4 horas sem registro",
            ],
            corrections=[
                "Descarte de 200 doses por seguranca",
                "Abertura de relatorio de incidente",
            ],
            result="200 doses descartadas. Causa-raiz nao identificada. Logger enviado para analise.",
            consequences="Confianca nos loggers IoT abalada. Necessidade de investigacao urgente.",
            learning_summary="Loggers IoT podem falhar em temperaturas negativas extremas, "
            "causando perda de dados e comprometendo a rastreabilidade.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "UBS Belo Monte", "entity_type": "location"},
                {"name": "vacina", "entity_type": "product"},
            ],
            source_refs=[SourceRef(source_id="relatorio-incidente-001", source_type="report",
                                   description="Relatorio de incidente Belo Monte").model_dump()],
        )
        store.save_memory(ep)
        created.append(epid)

    # --- Evidence: Logger data gap ---
    evid = "evi-logger-gap"
    if store.get_memory(evid) is None:
        ev = Evidence(
            id=evid,
            project_id=project_id,
            content="Arquivo de log do data logger TL-2000 (SN: TL-4521) extraido apos "
            "o incidente da UBS Belo Monte. Esta evidencia mostra registros normais das "
            "06:00 as 09:30, seguidos de ausencia total de dados entre 09:45 e 13:45 — "
            "um apagao de 4 horas. Apos 13:50 os registros retornam com valores normais. "
            "O contador interno indica 16 amostragens perdidas. Esta falha de registro "
            "ocorreu durante transporte em temperatura externa entre -12C e -18C. "
            "O arquivo sugere que as baterias falham no frio extremo, mas nao registra "
            "a causa exata da interrupcao.",
            evidence_type=EvidenceType.LOG,
            location="Arquivo TL4521_20260315.csv, hash SHA256: a3f8b2c...",
            producer="Data logger TL-2000 SN: TL-4521",
            environment="transporte rodoviario, temp externa -12C a -18C",
            artifact_version="firmware v3.1.2",
            supported_claims=["hyp-battery-failure"],
            limitations="O arquivo nao registra a causa da interrupcao nem o estado da bateria.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "TL-2000", "entity_type": "equipment"},
                {"name": "lacuna de dados", "entity_type": "anomaly"},
            ],
        )
        store.save_memory(ev)
        created.append(evid)

    # --- Hypothesis: battery failure ---
    hid = "hyp-battery-failure"
    if store.get_memory(hid) is None:
        h = Hypothesis(
            id=hid,
            project_id=project_id,
            content="A hipotese inicial do Projeto Boreal sobre o apagao de dados na rota "
            "de entrega para UBS Belo Monte: a bateria de litio do logger TL-2000 sofre "
            "queda abrupta de tensao quando exposta a temperaturas inferiores a -10C por "
            "periodo prolongado. Esta hipotese propoe que o frio extremo faz o circuito de "
            "protecao desligar temporariamente o dispositivo, interrompendo os registros. "
            "Ao aquecer, a bateria recupera tensao e o logger religa automaticamente. "
            "Este palpite inicial foi posteriormente confirmado por teste de laboratorio. "
            "A hipotese explicou as falhas nos dados durante o transporte.",
            hypothesis_state=HypothesisState.PROPOSED,
            origin_observation="Logger parou de registrar no trecho mais frio da rota (-18C) "
            "e voltou quando a temperatura subiu para -5C.",
            prediction="Se submetido a -15C em laboratorio, o logger desligara em menos de 60 min.",
            test_condition="Camara fria com 3 unidades TL-2000 a -15C, -20C e -25C",
            confirmation_criterion="Desligamento em 2 de 3 unidades a -15C ou inferior",
            rejection_criterion="Nenhuma unidade desligar em 4h a -25C",
            risk="Se confirmada, 50 loggers precisarao ser substituidos.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.MEDIUM,
            entities=[
                {"name": "bateria de litio", "entity_type": "component"},
                {"name": "temperatura negativa", "entity_type": "condition"},
            ],
        )
        store.save_memory(h)
        created.append(hid)

    # --- Learning: single logger insufficient ---
    lid = "lrn-single-logger-insufficient"
    if store.get_memory(lid) is None:
        ln = Learning(
            id=lid,
            project_id=project_id,
            content="Um unico ponto de monitoramento com logger IoT nao oferece redundancia "
            "para garantir a integridade dos dados em rotas longas com variacao termica "
            "extrema. A falha de um unico componente eletronico compromete toda a "
            "rastreabilidade da cadeia fria. Este aprendizado contribuiu para o motivo "
            "do abandono da abordagem inicial baseada exclusivamente em loggers IoT. "
            "A decisao de usar apenas loggers foi abandonada porque aprendemos que "
            "baterias quimicas nao sao confiaveis em ambientes gelados com temperatura "
            "abaixo de -10C.",
            learning_state=LearningState.OBSERVED,
            origin_episode_ids=[epid],
            evidence_ids=[evid],
            works_under_conditions="Rotas curtas com temperatura externa acima de 0C",
            fails_under_conditions="Rotas longas com temperatura abaixo de -10C, onde "
            "bateria pode falhar sem redundancia",
            generalization_degree="Especifico para equipamentos eletronicos com bateria "
            "operando em frio extremo",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.MEDIUM,
            entities=[
                {"name": "redundancia", "entity_type": "concept"},
                {"name": "logger IoT", "entity_type": "equipment"},
            ],
        )
        store.save_memory(ln)
        created.append(lid)

    # --- Checkpoint: Phase 2 ---
    cid = "chk-boreal-p2"
    if store.get_memory(cid) is None:
        ck = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Checkpoint Fase 2 do Projeto Boreal. Incidente na UBS Belo Monte "
            "registrado com 200 doses perdidas por falha de monitoramento. Hipotese de "
            "falha de bateria em investigacao. Aprendizado sobre insuficiencia de logger "
            "unico documentado. Operacoes suspensas para rotas com temperatura abaixo de "
            "-5C ate que o problema de confiabilidade das baterias seja resolvido.",
            current_state="Incidente documentado, hipotese registrada, investigacao autorizada.",
            last_completed_action="Registro do incidente e abertura de investigacao",
            active_decisions=["dec-boreal-iot"],
            pending_items=["Teste de bateria em camara fria", "Analise do logger pelo fabricante"],
            blockers=["Operacoes suspensas em rotas com temperatura abaixo de -5C"],
            artifacts_and_versions={"relatorio-incidente": "v1.0"},
            next_allowed_action="Executar teste de laboratorio para verificar hipotese de bateria",
            known_risks=["Mais perdas se hipotese confirmada sem alternativa"],
            deep_dive_refs=["relatorio-incidente-001", "hyp-battery-failure"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
        )
        store.save_memory(ck)
        created.append(cid)

    # Relations
    relations: list[tuple[str, str, str, RelationType]] = [
        ("rel-07-hyp-der-epi", hid, epid, RelationType.DERIVED_FROM),
        ("rel-08-hyp-sup-evi", hid, evid, RelationType.SUPPORTED_BY),
        ("rel-09-lrn-der-epi", lid, epid, RelationType.DERIVED_FROM),
        ("rel-10-evi-par-epi", evid, epid, RelationType.PART_OF),
        ("rel-11-chk-sum-hyp", cid, hid, RelationType.SUMMARIZES),
        ("rel-12-epi-cau-dec", epid, "dec-boreal-iot", RelationType.CAUSED_BY),
    ]

    for rid, src, tgt, rtype in relations:
        existing = store.search_relations(source_id=src, target_id=tgt, relation_type=rtype)
        if not existing:
            rel = MemoryRelation(id=rid, source_id=src, target_id=tgt,
                                 relation_type=rtype, confidence=Confidence.HIGH)
            store.save_relation(rel)

    return created
