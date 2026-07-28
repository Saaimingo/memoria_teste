"""MEC R4 — Operational test fixture.

Frozen fixture of 35 structured operational memories spanning six contexts:

* MEC project
* Harness Cognitivo project
* equipment fleet of ACME corp
* customer support for BioLab client
* technical incidents
* documents and protocols

Deliberately includes:

* same file name in different projects
* devices from the same manufacturer
* serials with similar prefixes
* similar protocols
* MAC addresses in different formats
* Windows paths
* full and abbreviated commit SHAs
* active and superseded decisions
* non-approved hypotheses
* similar incidents on different machines
* a truly absent memory (no fixture record matches)
* three semantically close memories
* queries with incomplete identifiers

This module is the single source of truth for the R4 acceptance tests.
All IDs are explicit strings so tests can reference them without indirection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EvidenceType,
    FactStatus,
    HypothesisState,
    LearningState,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    DocumentRecord,
    Episode,
    Evidence,
    Fact,
    Hypothesis,
    Learning,
    MemoryRelation,
    ProjectRecord,
)
from mec_lab.retrieval.assisted import candidate_metadata
from mec_lab.storage import Storage

# Stable datetime anchors so the fixture is reproducible across runs.
_BASE = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
def _dt(days: int, hours: int = 0) -> datetime:
    return _BASE + timedelta(days=days, hours=hours)

# Project IDs (kept short and stable for test assertions)
PROJECT_MEC = "proj-mec"
PROJECT_HARNESS = "proj-harness"
PROJECT_FLEET = "proj-fleet"
PROJECT_SUPPORT = "proj-support"
PROJECT_INCIDENTS = "proj-incidents"
PROJECT_DOCS = "proj-docs"

# Commit SHAs (40-char full forms + their 7-char prefixes used in queries)
COMMIT_FULL_A = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4"
COMMIT_PREFIX_A = "a1b2c3d"
COMMIT_FULL_B = "ffeeddccbbaa99887766554433221100ffeeddcc"
COMMIT_PREFIX_B = "ffeeddc"


PROJECT_RECORDS: list[ProjectRecord] = [
    ProjectRecord(id=PROJECT_MEC, name="Projeto MEC", description="Motor de Memória Cognitiva"),
    ProjectRecord(id=PROJECT_HARNESS, name="Harness Cognitivo", description="Harness de orquestração"),
    ProjectRecord(id=PROJECT_FLEET, name="Frota ACME", description="Parque de equipamentos ACME"),
    ProjectRecord(id=PROJECT_SUPPORT, name="Atendimento BioLab", description="Suporte ao cliente BioLab"),
    ProjectRecord(id=PROJECT_INCIDENTS, name="Incidentes Técnicos", description="Registro de incidentes"),
    ProjectRecord(id=PROJECT_DOCS, name="Documentos e Protocolos", description="Documentação normativa"),
]


# ---------------------------------------------------------------------------
# Memory records — 35 entries
# ---------------------------------------------------------------------------

MEMORIES: list[Fact | Decision | Hypothesis | Evidence | Learning | Episode | Checkpoint | DocumentRecord] = [
    # ---- Projeto MEC (6 records) ----
    Fact(
        id="mec-f1",
        content="O MEC usa SQLite como backend de armazenamento na fase experimental.",
        project_id=PROJECT_MEC,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "repository": "memoria-teste",
            "branch": "main",
            "file_path": "src/mec_lab/storage/__init__.py",
            "file_name": "__init__.py",
            "responsible": "Saimon",
            "environment": "dev",
        },
        created_at=_dt(0),
    ),
    Decision(
        id="mec-d1-old",
        content="Adotar Jaccard puro como métrica lexical de recuperação no MEC.",
        project_id=PROJECT_MEC,
        decision_status=DecisionStatus.SUPERSEDED,
        status=EpistemicStatus.SUPERSEDED,
        superseded_by="mec-d1-new",
        authority="Saimon",
        justification="Simples e determinístico.",
        metadata={
            "repository": "memoria-teste",
            "branch": "main",
            "responsible": "Saimon",
        },
        created_at=_dt(1),
    ),
    Decision(
        id="mec-d1-new",
        content="Adotar TF-IDF com cosseno como métrica semântica e Jaccard como lexical.",
        project_id=PROJECT_MEC,
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        supersedes="mec-d1-old",
        authority="Saimon",
        justification="Cobertura semântica sem depender de LLM externo.",
        metadata={
            "repository": "memoria-teste",
            "branch": "main",
            "responsible": "Saimon",
        },
        created_at=_dt(10),
    ),
    Hypothesis(
        id="mec-h1",
        content="Hipótese: normalização de identificadores técnicos reduz falsos positivos em mais de 50%.",
        project_id=PROJECT_MEC,
        hypothesis_state=HypothesisState.PROPOSED,
        status=EpistemicStatus.REGISTERED,
        prediction="Taxa de falsos positivos cai abaixo de 5%.",
        metadata={
            "repository": "memoria-teste",
            "branch": "experiment/mec-live-memory-02-clean",
            "responsible": "Saimon",
        },
        created_at=_dt(5),
    ),
    Evidence(
        id="mec-ev1",
        content="Evidência de commit a1b2c3d introduzindo TF-IDF adapter.",
        project_id=PROJECT_MEC,
        evidence_type=EvidenceType.COMMIT,
        status=EpistemicStatus.VERIFIED,
        location="memoria-teste",
        producer="Saimon",
        metadata={
            "commit_sha": COMMIT_FULL_A,
            "repository": "memoria-teste",
            "branch": "main",
        },
        created_at=_dt(12),
    ),
    Checkpoint(
        id="mec-cp1",
        content="Checkpoint do projeto MEC: R4 em implementação.",
        project_id=PROJECT_MEC,
        current_state="Implementando R4 structured assisted retrieval",
        last_completed_action="Adicionado identifiers.py",
        next_allowed_action="Implementar assisted retrieval",
        pending_items=["Fixture operacional", "Testes de aceitação"],
        blockers=[],
        metadata={
            "repository": "memoria-teste",
            "branch": "feature/mec-r4-structured-assisted-retrieval",
            "responsible": "Saimon",
        },
        created_at=_dt(20),
    ),

    # ---- Projeto Harness Cognitivo (6 records) ----
    Fact(
        id="harness-f1",
        content="O Harness Cognitivo orquestra agentes em pipelines isolados por contexto.",
        project_id=PROJECT_HARNESS,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "repository": "hermes-agent",
            "branch": "main",
            "file_path": "src/harness/orchestrator.py",
            "file_name": "orchestrator.py",
            "responsible": "Saimon",
            "environment": "prod",
        },
        created_at=_dt(2),
    ),
    Fact(
        id="harness-f2",
        content="O Harness usa o mesmo arquivo __init__.py para diagnóstico deSkills.",
        project_id=PROJECT_HARNESS,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "repository": "hermes-agent",
            "branch": "main",
            "file_path": "src/harness/skills/__init__.py",
            "file_name": "__init__.py",
            "responsible": "Saimon",
        },
        created_at=_dt(3),
    ),
    Decision(
        id="harness-d1",
        content="Decidido: agents não podem promover o próprio resultado.",
        project_id=PROJECT_HARNESS,
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        authority="Saimon",
        justification="Evita auto-aprovação e conflito de interesse.",
        metadata={
            "repository": "hermes-agent",
            "branch": "main",
            "responsible": "Saimon",
        },
        created_at=_dt(4),
    ),
    Evidence(
        id="harness-ev1",
        content="Commit ffeeddc adicionando guard-rails de delegação.",
        project_id=PROJECT_HARNESS,
        evidence_type=EvidenceType.COMMIT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "commit_sha": COMMIT_FULL_B,
            "repository": "hermes-agent",
            "branch": "main",
        },
        created_at=_dt(8),
    ),
    Learning(
        id="harness-l1",
        content="Aprendizado: delegação em segundo plano exige notify_on_complete.",
        project_id=PROJECT_HARNESS,
        learning_state=LearningState.PROMOTED,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "repository": "hermes-agent",
            "responsible": "Saimon",
        },
        created_at=_dt(15),
    ),
    DocumentRecord(
        id="harness-doc1",
        content="Especificação do Harness Cognitivo v3.",
        project_id=PROJECT_HARNESS,
        document_type="specification",
        is_normative=True,
        metadata={
            "version": "3.0",
            "responsible": "Saimon",
        },
        created_at=_dt(6),
    ),

    # ---- Frota ACME (7 records) ----
    Fact(
        id="fleet-eq1",
        content="Equipamento ACME Spectrum serial SN-ACME-1001 ativo na linha de produção 1.",
        project_id=PROJECT_FLEET,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
            "serial_number": "SN-ACME-1001",
            "mac_address": "AA:BB:CC:DD:EE:01",
            "environment": "prod",
            "responsible": "Carlos",
        },
        created_at=_dt(0),
    ),
    Fact(
        id="fleet-eq2",
        content="Equipamento ACME Spectrum serial SN-ACME-1002 em standby na linha 2.",
        project_id=PROJECT_FLEET,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
            "serial_number": "SN-ACME-1002",
            "mac_address": "aa-bb-cc-dd-ee-02",
            "environment": "prod",
            "responsible": "Carlos",
        },
        created_at=_dt(1),
    ),
    Fact(
        id="fleet-eq3",
        content="Equipamento ACME Nova serial SN-ACME-2001 apresentou falha intermitente.",
        project_id=PROJECT_FLEET,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Nova",
            "serial_number": "SN-ACME-2001",
            "mac_address": "AABBCCDDEE03",
            "environment": "prod",
            "responsible": "Diana",
        },
        created_at=_dt(5),
    ),
    Evidence(
        id="fleet-ev1",
        content="Log de diagnóstico do equipamento SN-ACME-1001 mostrando temperatura elevada.",
        project_id=PROJECT_FLEET,
        evidence_type=EvidenceType.LOG,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "serial_number": "SN-ACME-1001",
            "manufacturer": "ACME",
            "device_model": "Spectrum",
        },
        created_at=_dt(7),
    ),
    Learning(
        id="fleet-l1",
        content="Aprendizado: equipamentos ACME Spectrum exigem reinício após reinicialização de fábrica.",
        project_id=PROJECT_FLEET,
        learning_state=LearningState.RECURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
        },
        created_at=_dt(12),
    ),
    Decision(
        id="fleet-d1",
        content="Decidido: todos os ACME Spectrum devem receber firmware 4.2 até julho.",
        project_id=PROJECT_FLEET,
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        authority="Diana",
        justification="Mitiga incidente de temperatura.",
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
            "version": "4.2",
            "responsible": "Diana",
        },
        created_at=_dt(14),
    ),
    Episode(
        id="fleet-ep1",
        content="Episódio: substituição da placa do ACME Nova SN-ACME-2001 em campo.",
        project_id=PROJECT_FLEET,
        initial_state="Equipamento em falha",
        goal="Restabelecer operação",
        result="Equipamento restabelecido",
        metadata={
            "serial_number": "SN-ACME-2001",
            "manufacturer": "ACME",
            "device_model": "Nova",
        },
        created_at=_dt(9),
    ),

    # ---- Atendimento BioLab (6 records) ----
    Fact(
        id="bio-f1",
        content="Cliente BioLab protocolou chamado TICKET-1001 sobre calibração de centrífuga.",
        project_id=PROJECT_SUPPORT,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "client_id": "BioLab",
            "ticket_number": "TICKET-1001",
            "protocol_number": "PROTO-1001",
            "responsible": "Eliane",
            "environment": "cliente",
        },
        created_at=_dt(3),
    ),
    Fact(
        id="bio-f2",
        content="Cliente BioLab protocolou chamado #1002 sobre vazamento de reagentes.",
        project_id=PROJECT_SUPPORT,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "client_id": "BioLab",
            "ticket_number": "1002",
            "protocol_number": "PROTO-1002",
            "responsible": "Eliane",
            "environment": "cliente",
        },
        created_at=_dt(5),
    ),
    Decision(
        id="bio-d1",
        content="Decidido: chamados do BioLab em ambiente de produção têm prioridade alta.",
        project_id=PROJECT_SUPPORT,
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        authority="Eliane",
        justification="Contrato SLA exige resposta em 2h.",
        metadata={
            "client_id": "BioLab",
            "environment": "prod",
            "responsible": "Eliane",
        },
        created_at=_dt(6),
    ),
    Fact(
        id="bio-f3",
        content="BioLab protocolo PROTO-1003 refere-se à manutenção preventiva trimestral.",
        project_id=PROJECT_SUPPORT,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "client_id": "BioLab",
            "protocol_number": "PROTO-1003",
            "responsible": "Eliane",
        },
        created_at=_dt(10),
    ),
    Episode(
        id="bio-ep1",
        content="Episódio: visita técnica ao BioLab para resolver TICKET-1001.",
        project_id=PROJECT_SUPPORT,
        initial_state="Calibração desalinhada",
        goal="Calibrar centrífuga",
        result="Calibração concluída e validada",
        metadata={
            "client_id": "BioLab",
            "ticket_number": "TICKET-1001",
            "responsible": "Eliane",
        },
        created_at=_dt(8),
    ),
    Learning(
        id="bio-l1",
        content="Aprendizado: centrífugas BioLab exigem recalibração após 90 dias de uso contínuo.",
        project_id=PROJECT_SUPPORT,
        learning_state=LearningState.PROMOTED,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "client_id": "BioLab",
            "responsible": "Eliane",
        },
        created_at=_dt(18),
    ),

    # ---- Incidentes Técnicos (6 records) ----
    Fact(
        id="inc-f1",
        content="Incidente: superaquecimento no equipamento ACME Spectrum da linha 1.",
        project_id=PROJECT_INCIDENTS,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
            "serial_number": "SN-ACME-1010",
            "mac_address": "AA:BB:CC:DD:EE:01",
            "environment": "prod",
        },
        created_at=_dt(11),
    ),
    Fact(
        id="inc-f2",
        content="Incidente: superaquecimento no equipamento ACME Nova SN-ACME-2001.",
        project_id=PROJECT_INCIDENTS,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Nova",
            "serial_number": "SN-ACME-2001",
            "mac_address": "AABBCCDDEE03",
            "environment": "prod",
        },
        created_at=_dt(12),
    ),
    Decision(
        id="inc-d1-old",
        content="Decidido: incidentes de temperatura devem ser resolvidos com reboot imediato.",
        project_id=PROJECT_INCIDENTS,
        decision_status=DecisionStatus.SUPERSEDED,
        status=EpistemicStatus.SUPERSEDED,
        superseded_by="inc-d1-new",
        authority="Diana",
        justification="Ação rápida de contenção.",
        metadata={
            "environment": "prod",
            "responsible": "Diana",
        },
        created_at=_dt(13),
    ),
    Decision(
        id="inc-d1-new",
        content="Decidido: incidentes de temperatura devem ser escalados para troca da placa.",
        project_id=PROJECT_INCIDENTS,
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        supersedes="inc-d1-old",
        authority="Diana",
        justification="Reboot não resolve causa raiz.",
        metadata={
            "environment": "prod",
            "responsible": "Diana",
        },
        created_at=_dt(16),
    ),
    Hypothesis(
        id="inc-h1",
        content="Hipótese: o superaquecimento está correlacionado ao firmware 3.x dos ACME.",
        project_id=PROJECT_INCIDENTS,
        hypothesis_state=HypothesisState.PROPOSED,
        status=EpistemicStatus.REGISTERED,
        metadata={
            "manufacturer": "ACME",
            "version": "3.x",
        },
        created_at=_dt(14),
    ),
    Evidence(
        id="inc-ev1",
        content="Log de incidente mostrando temperatura de 92C no ACME Spectrum.",
        project_id=PROJECT_INCIDENTS,
        evidence_type=EvidenceType.LOG,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "manufacturer": "ACME",
            "device_model": "Spectrum",
        },
        created_at=_dt(15),
    ),

    # ---- Documentos e Protocolos (4 records) ----
    DocumentRecord(
        id="doc-p1",
        content="Protocolo PROTO-2001: procedimento de calibração trimestral para centrífugas.",
        project_id=PROJECT_DOCS,
        document_type="specification",
        is_normative=True,
        metadata={
            "protocol_number": "PROTO-2001",
            "responsible": "Eliane",
        },
        created_at=_dt(4),
    ),
    DocumentRecord(
        id="doc-p2",
        content="Protocolo PROTO-2002: procedimento de manutenção corretiva para ACME Spectrum.",
        project_id=PROJECT_DOCS,
        document_type="specification",
        is_normative=True,
        metadata={
            "protocol_number": "PROTO-2002",
            "manufacturer": "ACME",
            "device_model": "Spectrum",
        },
        created_at=_dt(6),
    ),
    DocumentRecord(
        id="doc-spec1",
        content="Especificação técnica do MEC R4: recuperação assistida estruturada.",
        project_id=PROJECT_DOCS,
        document_type="specification",
        is_normative=False,
        metadata={
            "version": "R4",
            "repository": "memoria-teste",
            "file_path": "docs/R4_SPEC.md",
            "file_name": "R4_SPEC.md",
            "responsible": "Saimon",
        },
        created_at=_dt(2),
    ),
    Fact(
        id="doc-f1",
        content="Documento R4_SPEC.md descreve o pipeline híbrido de recuperação do MEC.",
        project_id=PROJECT_DOCS,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        metadata={
            "file_path": "docs/R4_SPEC.md",
            "file_name": "R4_SPEC.md",
            "responsible": "Saimon",
        },
        created_at=_dt(3),
    ),

    # ---- Legacy memory without structured metadata (compatibility) ----
    Fact(
        id="legacy-f1",
        content="Memória antiga registrada antes do R4 sobre armazenamento SQLite.",
        project_id=PROJECT_MEC,
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
        created_at=_dt(-30),
    ),
]


RELATIONS: list[MemoryRelation] = [
    MemoryRelation(
        source_id="mec-d1-new", target_id="mec-d1-old",
        relation_type=RelationType.SUPERSEDES,
    ),
    MemoryRelation(
        source_id="inc-d1-new", target_id="inc-d1-old",
        relation_type=RelationType.SUPERSEDES,
    ),
    MemoryRelation(
        source_id="fleet-ev1", target_id="fleet-eq1",
        relation_type=RelationType.SUPPORTED_BY,
    ),
    MemoryRelation(
        source_id="bio-ep1", target_id="bio-f1",
        relation_type=RelationType.OCCURRED_DURING,
    ),
    MemoryRelation(
        source_id="inc-f1", target_id="fleet-eq1",
        relation_type=RelationType.REFERENCES,
    ),
]


# ---------------------------------------------------------------------------
# Reload helper
# ---------------------------------------------------------------------------


def build_fixture_storage(db_path: str = ":memory:") -> Storage:
    """Create an in-memory Storage preloaded with the frozen R4 fixture."""
    store = Storage(db_path)
    store.init_schema()
    for proj in PROJECT_RECORDS:
        store.save_project(proj)
    for mem in MEMORIES:
        store.save_memory(mem)
    for rel in RELATIONS:
        store.save_relation(rel)
    return store


FIXTURE_MEMORY_COUNT = len(MEMORIES)
FIXTURE_PROJECT_COUNT = len(PROJECT_RECORDS)
FIXTURE_RELATION_COUNT = len(RELATIONS)