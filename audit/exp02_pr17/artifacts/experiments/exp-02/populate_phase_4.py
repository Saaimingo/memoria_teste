"""Phase 4 — Mudanca de Decisao: sistema dual IoT + VVM.

Idempotent. Enriched contents for lexical overlap.
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
    DocumentRecord,
    Evidence,
    MemoryRelation,
    SourceRef,
)
from mec_lab.storage import Storage


def populate(store: Storage, project_id: str) -> list[str]:
    created: list[str] = []

    # --- New Decision: dual system ---
    did_dual = "dec-boreal-dual"
    if store.get_memory(did_dual) is None:
        d = Decision(
            id=did_dual,
            project_id=project_id,
            content="A decisao vigente do Projeto Boreal para monitoramento de temperatura "
            "na cadeia fria: substituir o sistema baseado exclusivamente em loggers IoT "
            "por uma abordagem dual. (a) loggers IoT mantidos nos pontos fixos de "
            "armazenamento onde a temperatura e controlada acima de 0C; (b) indicadores "
            "quimicos passivos VVM (Vaccine Vial Monitor) certificados pela OMS para "
            "todos os trechos de transporte, sem dependencia de bateria ou eletronica. "
            "Esta decisao substitui a decisao original de usar apenas loggers IoT, "
            "que foi abandonada porque as baterias falhavam no frio extremo. A nova "
            "abordagem de vigilancia de temperatura resolve o conflito entre a necessidade "
            "de rastreabilidade e a confiabilidade dos equipamentos eletronicos em "
            "condicoes adversas. O sistema de vigilancia atual combina dois principios "
            "fisicos diferentes para garantir redundancia.",
            decision_status=DecisionStatus.ACTIVE,
            authority="Comite Gestor do Projeto Boreal, aprovado em 10/04/2026",
            alternatives=[
                "Sistema dual IoT + VVM",
                "Loggers com bateria aquecida",
                "Fonte de alimentacao veicular",
                "Servico terceirizado com veiculos refrigerados ativos",
            ],
            justification="Os indicadores VVM sao certificados pela OMS (PQS E006/045), "
            "nao usam bateria e funcionam em qualquer temperatura. Os loggers IoT continuam "
            "uteis nos pontos fixos. A combinacao elimina o ponto unico de falha.",
            expected_consequences="Eliminacao do risco de falha de bateria. Custo adicional "
            "estimado em 15%. Cobertura de rastreabilidade mantida.",
            revocation_criteria="Se VVM apresentar taxa de falsos positivos acima de 2% ou "
            "houver desabastecimento no mercado nacional.",
            superseded_decision_id="dec-boreal-iot",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "VVM", "entity_type": "equipment"},
                {"name": "IoT logger", "entity_type": "equipment"},
                {"name": "sistema dual", "entity_type": "architecture"},
            ],
            source_refs=[SourceRef(source_id="reuniao-comite-20260410", source_type="meeting",
                                   description="Aprovacao do sistema dual").model_dump()],
        )
        store.save_memory(d)
        created.append(did_dual)

    # --- Evidence: WHO PQS ---
    evid_pqs = "evi-who-pqs-vvm"
    if store.get_memory(evid_pqs) is None:
        ev = Evidence(
            id=evid_pqs,
            project_id=project_id,
            content="Certificacao WHO PQS E006/045 para indicadores VVM (Vaccine Vial "
            "Monitor). Esta evidencia demonstra que os indicadores quimicos VVM funcionam "
            "de forma confiavel em qualquer faixa de temperatura ambiente (-30C a +50C) "
            "sem necessidade de bateria ou componentes eletronicos. Os VVM mudam de cor "
            "de forma irreversivel quando expostos a calor acumulado acima do limite "
            "seguro para vacinas. A certificacao PQS garante sensibilidade e especificidade "
            "para uso em programas nacionais de imunizacao. O projeto tem evidencia "
            "normativa internacional de que os novos indicadores quimicos funcionam "
            "para monitoramento de vacinas em cadeia fria.",
            evidence_type=EvidenceType.ARTIFACT,
            location="WHO PQS Catalogue, E006/045, revisao 2025.1",
            producer="WHO PQS Working Group",
            environment="normativo-internacional",
            artifact_version="2025.1",
            supported_claims=["dec-boreal-dual"],
            limitations="VVM indica calor acumulado, nao fornece registro temporal detalhado. "
            "Nao detecta congelamento.",
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "WHO PQS", "entity_type": "certification"},
                {"name": "VVM", "entity_type": "equipment"},
            ],
        )
        store.save_memory(ev)
        created.append(evid_pqs)

    # --- Checkpoint: Phase 4 ---
    cid_p4 = "chk-boreal-p4"
    if store.get_memory(cid_p4) is None:
        ck = Checkpoint(
            id=cid_p4,
            project_id=project_id,
            content="Checkpoint Fase 4 do Projeto Boreal. Nova decisao de arquitetura "
            "aprovada: sistema dual IoT + VVM para monitoramento de temperatura. A decisao "
            "anterior de usar apenas IoT foi marcada como superseded. Processo de aquisicao "
            "dos VVM iniciado. Especificacao do novo sistema documentada. O projeto agora "
            "tem duas decisoes que estao em conflito por substituicao: a decisao dual "
            "vigente e a decisao IoT substituida.",
            current_state="Sistema dual aprovado. IoT mantido em pontos fixos. 5000 VVM em "
            "aquisicao. Transporte ainda suspenso aguardando implantacao.",
            last_completed_action="Aprovacao do sistema dual e inicio da aquisicao de VVM",
            active_decisions=["dec-boreal-dual"],
            pending_items=["Aquisicao de 5000 VVM", "Treinamento para leitura de VVM",
                           "Atualizacao de procedimentos", "Teste piloto"],
            blockers=["Treinamento nao iniciado — material didatico pendente"],
            artifacts_and_versions={"especificacao-sistema-dual": "v1.0", "plano-aquisicao": "v1.0"},
            next_allowed_action="Produzir material de treinamento para VVM",
            known_risks=["Atraso na importacao", "Resistencia a nova tecnologia",
                         "Interpretacao incorreta dos VVM"],
            deep_dive_refs=["evi-who-pqs-vvm", "doc-dual-spec"],
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
        )
        store.save_memory(ck)
        created.append(cid_p4)

    # --- Document: Dual spec ---
    docid_spec = "doc-dual-spec"
    if store.get_memory(docid_spec) is None:
        doc = DocumentRecord(
            id=docid_spec,
            project_id=project_id,
            content="Especificacao Tecnica do Sistema Dual de Monitoramento do Projeto "
            "Boreal. Este documento descreve a arquitetura completa do novo sistema de "
            "monitoramento, combinando IoT em pontos fixos e VVM no transporte. Define "
            "componentes, procedimentos operacionais, criterios de aceitacao e plano de "
            "treinamento. A documentacao do plano de monitoramento atualizado inclui "
            "referencias normativas da OMS e especificacoes de desempenho dos indicadores "
            "quimicos.",
            document_type="specification",
            sections=["Arquitetura", "Componentes", "Procedimentos", "Criterios de Aceitacao",
                      "Plano de Treinamento", "Referencias"],
            constituent_ids=["dec-boreal-dual", "evi-who-pqs-vvm"],
            is_normative=True,
            status=EpistemicStatus.VERIFIED,
            confidence=Confidence.HIGH,
            entities=[
                {"name": "sistema dual", "entity_type": "architecture"},
                {"name": "especificacao", "entity_type": "document"},
            ],
            source_refs=[SourceRef(source_id="especificacao-sistema-dual", source_type="spec",
                                   description="Especificacao tecnica v1.0").model_dump()],
        )
        store.save_memory(doc)
        created.append(docid_spec)

    # Relations
    relations: list[tuple[str, str, str, RelationType]] = [
        ("rel-20-decdual-sup-dec", did_dual, "dec-boreal-iot", RelationType.SUPERSEDES),
        ("rel-21-decdual-sup-evipqs", did_dual, evid_pqs, RelationType.SUPPORTED_BY),
        ("rel-22-decdual-der-lrnbat", did_dual, "lrn-battery-cold-degradation", RelationType.DERIVED_FROM),
        ("rel-23-hypc-res-decdual", "hyp-battery-confirmed", did_dual, RelationType.RESOLVED_BY),
        ("rel-24-chkp4-sum-decdual", cid_p4, did_dual, RelationType.SUMMARIZES),
        ("rel-25-docspec-sup-evipqs", docid_spec, evid_pqs, RelationType.SUPPORTED_BY),
        ("rel-26-docspec-ref-decdual", docid_spec, did_dual, RelationType.REFERENCES),
    ]

    for rid, src, tgt, rtype in relations:
        existing = store.search_relations(source_id=src, target_id=tgt, relation_type=rtype)
        if not existing:
            rel = MemoryRelation(id=rid, source_id=src, target_id=tgt,
                                 relation_type=rtype, confidence=Confidence.HIGH)
            store.save_relation(rel)

    # Mark old decision as superseded
    old_dec = store.get_memory("dec-boreal-iot")
    if old_dec:
        old_dec.decision_status = DecisionStatus.SUPERSEDED
        old_dec.status = EpistemicStatus.SUPERSEDED
        old_dec.superseded_by = did_dual
        store.save_memory(old_dec)

    return created
