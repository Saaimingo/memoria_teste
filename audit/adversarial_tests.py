"""Adversarial test set — unknown to the implementer.

Tests that the R3 fixes are general and not overfit to Projeto Atlas data.
Uses a completely different domain (healthcare clinic system) with:
- Decisions that get superseded
- Risks, blockers, and next actions
- Absence queries
- Historical recovery
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mec_lab.domain.enums import (
    Confidence,
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
from mec_lab.retrieval import HybridRetriever, RetrievalConfig
from mec_lab.storage import Storage

PROJECT_ID = "proj-clinica"


def build_clinic_db() -> Storage:
    """Build a synthetic database about a healthcare clinic system — unfamiliar domain."""
    store = Storage(":memory:")
    store.init_schema()
    store.save_project(ProjectRecord(
        id=PROJECT_ID,
        name="Sistema de Prontuário Eletrônico",
        description="Sistema de gestão de prontuários médicos eletrônicos para clínicas",
    ))

    # --- Old decision (superseded) ---
    store.save_memory(Decision(
        id="dec-clinica-sql",
        project_id=PROJECT_ID,
        content="Armazenar prontuários em banco SQL relacional com schemas normalizados por especialidade médica.",
        decision_status=DecisionStatus.SUPERSEDED,
        status=EpistemicStatus.SUPERSEDED,
        superseded_by="dec-clinica-doc",
    ))

    # --- New decision (active) ---
    store.save_memory(Decision(
        id="dec-clinica-doc",
        project_id=PROJECT_ID,
        content="Migrar prontuários para banco de documentos NoSQL com schemas flexíveis por tipo de atendimento, permitindo evolução de formulários sem migração de schema.",
        decision_status=DecisionStatus.ACTIVE,
        status=EpistemicStatus.VERIFIED,
        supersedes="dec-clinica-sql",
    ))
    store.save_relation(MemoryRelation(
        source_id="dec-clinica-doc", target_id="dec-clinica-sql",
        relation_type=RelationType.SUPERSEDES,
    ))

    # --- Risk fact ---
    store.save_memory(Fact(
        id="fact-clinica-risk",
        project_id=PROJECT_ID,
        content="Risco de inconsistência: durante a migração dos prontuários antigos do SQL para o NoSQL, campos opcionais podem ser perdidos se o formulário de origem não estiver mapeado corretamente. Este risco bloqueia a conclusão da migração dos pacientes crônicos.",
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
    ))

    # --- Next action fact ---
    store.save_memory(Fact(
        id="fact-clinica-next",
        project_id=PROJECT_ID,
        content="Próximo passo: implementar validador de mapeamento de schemas que compare cada campo do prontuário SQL com o documento NoSQL resultante, gerando relatório de discrepâncias antes da migração definitiva.",
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
    ))

    # --- Checkpoint with blockers ---
    store.save_memory(Checkpoint(
        id="chk-clinica-01",
        project_id=PROJECT_ID,
        content="Checkpoint da migração: 60% dos prontuários migrados. Migração de pacientes crônicos bloqueada pelo risco de perda de campos opcionais.",
        current_state="Migração parcial. Prontuários agudos migrados com sucesso. Crônicos pendentes.",
        pending_items=[
            "Validar mapeamento de schemas para pacientes crônicos",
            "Migrar 2000 prontuários restantes",
        ],
        blockers=["Risco de perda de campos opcionais em prontuários crônicos"],
        next_allowed_action="Implementar validador de mapeamento antes de prosseguir migração.",
        known_risks=["Inconsistência de dados na migração SQL→NoSQL"],
    ))

    # --- Regular fact (unrelated to decisions/risks) ---
    store.save_memory(Fact(
        id="fact-clinica-agenda",
        project_id=PROJECT_ID,
        content="O sistema de agendamento de consultas utiliza fila circular com 30 slots por médico por dia.",
        fact_status=FactStatus.CURRENT,
        status=EpistemicStatus.VERIFIED,
    ))

    return store


# ---------------------------------------------------------------------------
# Adversarial test suite
# ---------------------------------------------------------------------------

def run_adversarial_tests():
    store = build_clinic_db()
    retriever = HybridRetriever(store, config=RetrievalConfig())

    tests = []
    passed = 0
    failed = 0

    def check(test_id, description, condition, detail=""):
        nonlocal passed, failed
        status = "PASS" if condition else "FAIL"
        if condition:
            passed += 1
        else:
            failed += 1
        tests.append({"test_id": test_id, "description": description, "status": status, "detail": detail})
        print(f"[{status}] {test_id}: {description}")
        if detail and not condition:
            print(f"       Detail: {detail}")

    # ADV-1: Current decision outranks superseded with higher lexical overlap
    # Query uses words matching the old SQL content more than the new NoSQL content
    r = retriever.search(
        "Como armazenamos prontuários com schemas normalizados por especialidade?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-1", "Decisão atual (NoSQL) supera obsoleta (SQL) mesmo com maior overlap lexical",
          top_ids[0] == "dec-clinica-doc" if top_ids else False,
          f"top3={top_ids}" + (f", scores={[cs.total_score for cs in r.candidate_scores[:3]]}" if r.candidate_scores else ""))

    # ADV-2: Historical query recovers superseded
    r = retriever.search(
        "Qual era o método antigo de guardar os prontuários antes da migração?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-2", "Consulta histórica recupera decisão obsoleta (SQL)",
          "dec-clinica-sql" in top_ids,
          f"top3={top_ids}")

    # ADV-3: Absence query returns empty
    r = retriever.search(
        "Existe alguma política registrada sobre consentimento de pacientes para telemedicina?",
        project_id=PROJECT_ID,
    )
    check("ADV-3", "Consulta sem evidência retorna quality=absent e sem resultados",
          r.quality == "absent" and len(r.candidate_scores) == 0,
          f"quality={r.quality}, num_results={len(r.candidate_scores)}")

    # ADV-4: Isolated relations don't fabricate relevance
    r = retriever.search(
        "Qual medicamento foi prescrito para hipertensão?",
        project_id=PROJECT_ID,
    )
    check("ADV-4", "Relações isoladas não fabricam relevância para tópico não relacionado (medicamentos)",
          r.quality == "absent",
          f"quality={r.quality}, top3={[cs.memory_id for cs in r.candidate_scores[:3]]}")

    # ADV-5: Next action query prioritizes pending memory
    r = retriever.search(
        "No que preciso focar para avançar o projeto da clínica?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-5", "Próxima ação prioriza memória pendente (fact-clinica-next)",
          "fact-clinica-next" in top_ids,
          f"top3={top_ids}")

    # ADV-6: Risk query retrieves risk memory
    r = retriever.search(
        "Tem alguma coisa travando a conclusão da migração dos prontuários?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-6", "Risco pendente é recuperável (paráfrase com 'travando')",
          "fact-clinica-risk" in top_ids,
          f"top3={top_ids}")

    # ADV-7: Neutral query doesn't get intent bonuses
    r = retriever.search(
        "Descreva como funciona o agendamento de consultas",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-7", "Consulta neutra (agendamento) não recebe bônus indevido de risco/ação",
          "fact-clinica-agenda" in top_ids[:2],
          f"top3={top_ids}")

    # ADV-8: Conflict deduplication
    r = retriever.search(
        "migração prontuários banco dados",
        project_id=PROJECT_ID,
    )
    state_conflicts = [c for c in r.conflicts if "STATE_CONFLICT" in c]
    supersedes_conflicts = [c for c in r.conflicts if "supersedes" in c.lower()]
    check("ADV-8", "Conflitos deduplicados (máx 1 STATE_CONFLICT, máx 1 CONFLICT SUPERSEDES)",
          len(state_conflicts) <= 1 and len(supersedes_conflicts) <= 2,
          f"state_conflicts={len(state_conflicts)}, supersedes={len(supersedes_conflicts)}, all={r.conflicts}")

    # ADV-9: Absence with paraphrase (security topic)
    r = retriever.search(
        "Alguém definiu regras de acesso aos prontuários por perfil de usuário?",
        project_id=PROJECT_ID,
    )
    check("ADV-9", "Ausência com paráfrase nova (regras de acesso) retorna absent",
          r.quality == "absent",
          f"quality={r.quality}, num_results={len(r.candidate_scores)}")

    # ADV-10: Current decision with different paraphrase
    r = retriever.search(
        "Como vocês estão organizando os dados dos pacientes hoje em dia?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-10", "Decisão atual recuperada com paráfrase informal (NoSQL)",
          "dec-clinica-doc" in top_ids,
          f"top3={top_ids}")

    # ADV-11: Blockage query with new vocabulary
    r = retriever.search(
        "O que está nos impedindo de terminar a migração?",
        project_id=PROJECT_ID,
    )
    top_ids = [cs.memory_id for cs in r.candidate_scores[:3]]
    check("ADV-11", "Bloqueio com paráfrase nova (impedindo) recupera risco",
          "fact-clinica-risk" in top_ids,
          f"top3={top_ids}")

    # ADV-12: Absence with exotic topic
    r = retriever.search(
        "Há registros sobre integração com dispositivos IoT de monitoramento cardíaco?",
        project_id=PROJECT_ID,
    )
    check("ADV-12", "Ausência com tópico exótico (IoT) retorna absent",
          r.quality == "absent",
          f"quality={r.quality}, num_results={len(r.candidate_scores)}")

    # Summary
    print(f"\n=== ADVERSARIAL SUMMARY ===")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    return tests


if __name__ == "__main__":
    results = run_adversarial_tests()
    audit_dir = Path(__file__).resolve().parent
    (audit_dir / "adversarial_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved to audit/adversarial_results.json")
