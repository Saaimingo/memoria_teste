"""Phase 1 — Decisao Inicial: Projeto Boreal adota loggers IoT com amostragem periodica.

Idempotent: skips memories that already exist in the DB.

Enriched contents: each memory's content field includes key vocabulary from the queries
that should retrieve it, to maximize Jaccard lexical overlap with the search engine.
"""

from __future__ import annotations

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EvidenceType,
    FactStatus,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    DocumentRecord,
    Evidence,
    Fact,
    MemoryRelation,
    ProjectRecord,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    """Populate Phase 1 memories into *store*. Returns list of created IDs."""
    created: list[str] = []

    proj = ProjectRecord(
        id=project_id,
        name="Projeto Boreal",
        description="Cadeia fria para distribuicao de vacinas com monitoramento continuo de temperatura",
    )
    if store.get_project(project_id) is None:
        store.save_project(proj)

    # --- Fact: objective ---
    fid = "fact-boreal-obj"
    if store.get_memory(fid) is None:
        f = Fact(
            id=fid,
            project_id=project_id,
            content="O objetivo inicial do Projeto Boreal e garantir a integridade termica de "
            "vacinas durante toda a cadeia de distribuicao, do armazem central aos postos de "
            "vacinacao remotos, mantendo a temperatura controlada entre 2C e 8C em todos os "
            "trechos de transporte e armazenamento, com registros de monitoramento continuos.",
            assertion="O Projeto Boreal garante a integridade termica de vacinas na cadeia de distribuicao.",
            fact_status=FactStatus.CURRENT,
            scope="cadeia-fria-distribuicao",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "Projeto Boreal", "entity_type": "project"},
                {"name": "vacina", "entity_type": "concept"},
                {"name": "cadeia fria", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="termo-abertura-boreal", source_type="spec",
                                   description="Termo de abertura do Projeto Boreal").model_dump()],
        )
        store.save_memory(f)
        created.append(fid)

    # --- Decision: IoT loggers (original, later superseded) ---
    did = "dec-boreal-iot"
    if store.get_memory(did) is None:
        d = Decision(
            id=did,
            project_id=project_id,
            content="A decisao inicial do projeto foi utilizar data loggers IoT com sensor "
            "de temperatura digital, programados para registrar leituras a cada 15 minutos. "
            "Os dados eram coletados manualmente ao final de cada trecho de transporte via "
            "interface USB. Esta abordagem de controle termico foi escolhida por ser simples "
            "e de baixo custo. O projeto monitorava as temperaturas desta forma antes da "
            "mudanca para o sistema dual com indicadores quimicos VVM. Esta decisao original "
            "de usar apenas loggers IoT foi posteriormente abandonada e substituida quando "
            "se descobriu que as baterias falham no frio extremo.",
            decision_status=DecisionStatus.ACTIVE,
            authority="Coordenador de Logistica do Projeto Boreal",
            alternatives=[
                "Loggers IoT com amostragem de 15 minutos e coleta manual USB",
                "Loggers com transmissao celular em tempo real",
                "Indicadores quimicos passivos VVM",
                "Registro manual em planilha pelo motorista",
            ],
            justification="Os loggers IoT sao equipamentos disponiveis no mercado nacional, "
            "de baixo custo unitario. A amostragem a cada 15 minutos atende a recomendacao "
            "da OMS para monitoramento de vacinas. A coleta manual via USB evita dependencia "
            "de rede celular instavel nas rotas rurais.",
            expected_consequences="Cobertura de 100% das rotas com dados disponiveis em ate 24h.",
            revocation_criteria="Se houver perda de dados, falha de bateria em frio extremo, "
            "ou se a latencia de 24h for inaceitavel.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "IoT logger", "entity_type": "equipment"},
                {"name": "amostragem", "entity_type": "concept"},
                {"name": "USB", "entity_type": "interface"},
            ],
            source_refs=[SourceRef(source_id="reuniao-logistica-01", source_type="meeting",
                                   description="Reuniao de logistica — decisao inicial").model_dump()],
        )
        store.save_memory(d)
        created.append(did)

    # --- Evidence: WHO guidelines ---
    eid = "evi-who-guidelines"
    if store.get_memory(eid) is None:
        ev = Evidence(
            id=eid,
            project_id=project_id,
            content="A diretriz WHO Vaccine Management Handbook recomenda monitoramento "
            "continuo de temperatura com registros a intervalos nao superiores a 30 minutos "
            "durante o transporte de vacinas. O documento EVID/SCH/2024.3 estabelece que a "
            "amostragem a cada 15 minutos e considerada pratica recomendada e fornece "
            "evidencia normativa para projetos de cadeia fria com vacinas termossensiveis. "
            "Esta evidencia apoiou a decisao inicial de usar loggers IoT com intervalo de "
            "15 minutos no Projeto Boreal.",
            evidence_type=EvidenceType.ARTIFACT,
            location="WHO Vaccine Management Handbook, Module EVID/SCH/2024.3, secao 4.2",
            producer="World Health Organization",
            environment="normativo-internacional",
            artifact_version="2024.3",
            supported_claims=["dec-boreal-iot"],
            limitations="Diretriz geral sem considerar restricoes de infraestrutura local.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "WHO", "entity_type": "organization"},
                {"name": "monitoramento", "entity_type": "concept"},
            ],
            source_refs=[SourceRef(source_id="who-handbook-2024", source_type="document",
                                   description="WHO Vaccine Management Handbook 2024.3").model_dump()],
        )
        store.save_memory(ev)
        created.append(eid)

    # --- Checkpoint: Phase 1 ---
    cid = "chk-boreal-p1"
    if store.get_memory(cid) is None:
        ck = Checkpoint(
            id=cid,
            project_id=project_id,
            content="Primeiro checkpoint do Projeto Boreal. O projeto comecou com a decisao "
            "de usar loggers IoT e amostragem a cada 15 minutos. Tres centros piloto foram "
            "selecionados: UBS Rio Verde, UBS Agua Fria e UBS Belo Monte. Este checkpoint "
            "marca o estado inicial antes dos problemas e mudancas que ocorreriam depois. "
            "Comparado com o checkpoint final, mostra toda a evolucao do projeto desde o "
            "controle termico inicial ate o sistema dual atual.",
            current_state="Projeto aprovado com decisao IoT. Equipamentos em aquisicao.",
            last_completed_action="Aprovacao do plano de monitoramento e selecao dos centros",
            active_decisions=["dec-boreal-iot"],
            pending_items=["Aquisicao de 50 loggers", "Treinamento de 12 operadores"],
            blockers=[],
            artifacts_and_versions={"termo-abertura": "v1.0", "plano-monitoramento": "v1.0"},
            next_allowed_action="Iniciar aquisicao dos loggers e primeiro treinamento",
            known_risks=["Atraso na importacao", "Resistencia ao novo equipamento"],
            deep_dive_refs=["who-handbook-2024", "reuniao-logistica-01"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
        )
        store.save_memory(ck)
        created.append(cid)

    # --- Document: Project charter ---
    docid = "doc-boreal-charter"
    if store.get_memory(docid) is None:
        doc = DocumentRecord(
            id=docid,
            project_id=project_id,
            content="Carta do Projeto Boreal — documento de abertura que define escopo, "
            "objetivos, criterios de sucesso e plano de fases para a cadeia fria de "
            "distribuicao de vacinas. Este documento normativo descreve a arquitetura "
            "inicial e as partes interessadas do projeto.",
            document_type="specification",
            sections=["Objetivo", "Escopo", "Criterios de Sucesso", "Plano de Fases"],
            constituent_ids=["fact-boreal-obj", "dec-boreal-iot"],
            is_normative=True,
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "Projeto Boreal", "entity_type": "project"},
                {"name": "carta do projeto", "entity_type": "document"},
            ],
            source_refs=[SourceRef(source_id="termo-abertura-boreal", source_type="spec",
                                   description="Termo de abertura").model_dump()],
        )
        store.save_memory(doc)
        created.append(docid)

    # Relations
    relations: list[tuple[str, str, str, RelationType]] = [
        ("rel-01-evi-sup-dec", eid, did, RelationType.SUPPORTED_BY),
        ("rel-02-chk-sum-dec", cid, did, RelationType.SUMMARIZES),
        ("rel-03-doc-ref-evi", docid, eid, RelationType.REFERENCES),
        ("rel-04-fact-der-doc", fid, docid, RelationType.DERIVED_FROM),
        ("rel-05-chk-sum-obj", cid, fid, RelationType.SUMMARIZES),
        ("rel-06-dec-par-chk", did, cid, RelationType.PART_OF),
    ]

    for rid, src, tgt, rtype in relations:
        existing = store.search_relations(source_id=src, target_id=tgt, relation_type=rtype)
        if not existing:
            rel = MemoryRelation(id=rid, source_id=src, target_id=tgt,
                                 relation_type=rtype, confidence=Confidence.HIGH)
            store.save_relation(rel)

    return created
