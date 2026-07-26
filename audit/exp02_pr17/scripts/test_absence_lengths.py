"""Auditoria Exp-02 PR#17 — Análise das queries de ausência: curtas vs longas.

Hipótese do PR #17: as 5 queries de ausência foram encurtadas para evitar
falsos positivos (over-level lexical overlap). Este script testa:
  1. As queries curtas atuais (commit) — confirmam ausência?
  2. Versões longas plausíveis (sentence queries) — falhariam?

Construímos versões longas que um autor naturalmente teria escrito ANTES
de encurtar, seguindo o padrão das outras queries do dataset (q01-q09).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mec_lab.retrieval import HybridRetriever
from mec_lab.storage import Storage

EXP_DIR = REPO_ROOT / "audit" / "exp02_pr17" / "artifacts" / "experiments" / "exp-02"
PROJECT_ID = "proj-boreal"


def populate_all(store: Storage) -> None:
    """Run all 5 phases to populate the store."""
    import importlib.util
    for phase in range(1, 6):
        phase_file = EXP_DIR / f"populate_phase_{phase}.py"
        spec = importlib.util.spec_from_file_location(f"populate_phase_{phase}", phase_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.populate(store, PROJECT_ID)


# As 5 queries de ausência no commit atual (CURTAS)
SHORT_ABS = {
    "q10-ausencia-gps": "rastreamento GPS",
    "q24-parafrase-ausencia-gps": "satelite rastreamento localizacao",
    "q25-ausencia-drones": "drones aereos",
    "q26-ausencia-blackout": "blackout eletrico",
    "q27-ausencia-anvisa": "anvisa regulatorio",
}

# Versões LONGAS plausíveis — sentenças naturais no estilo das queries q01-q09.
# Estas são RECONSTRUÇÕS hipotéticas do que poderia ter sido a versão original.
LONG_ABS = {
    "q10-ausencia-gps": "O projeto possui rastreamento GPS em tempo real para as cargas de vacinas durante o transporte?",
    "q24-parafrase-ausencia-gps": "Existe algum sistema de localizacao satelital que permita rastrear as remessas em tempo real na cadeia fria?",
    "q25-ausencia-drones": "O projeto utiliza drones aereos para entrega de vacinas em centros remotos?",
    "q26-ausencia-blackout": "Qual e o protocolo de contingencia para blackout eletrico nos centros de armazenamento?",
    "q27-ausencia-anvisa": "O projeto possui documentacao sobre conformidade regulatoria com a ANVISA?",
}


def run_query(retriever: HybridRetriever, qid: str, query: str) -> dict:
    result = retriever.search(query, project_id=PROJECT_ID)
    has_lexical = any(cs.lexical_score > 0.0 for cs in result.candidate_scores)
    is_absent = (
        result.quality == "none"
        or not has_lexical
        or len(result.candidate_scores) == 0
    )
    top = result.candidate_scores[0] if result.candidate_scores else None
    return {
        "query_id": qid,
        "query_text": query,
        "quality": result.quality,
        "num_candidates": len(result.candidate_scores),
        "top_score": top.total_score if top else 0.0,
        "top_lexical_score": top.lexical_score if top else 0.0,
        "top_id": top.memory_id if top else None,
        "has_lexical_overlap": has_lexical,
        "is_absent": is_absent,
    }


def main() -> int:
    store = Storage(":memory:")
    store.init_schema()
    populate_all(store)
    retriever = HybridRetriever(store)

    print(f"Memories: {store.count_memories()} | Relations: {len(store.list_all_relations())}")
    print()

    results = {"short": {}, "long": {}}

    print("=" * 80)
    print("QUERIES DE AUSÊNCIA — VERSÃO CURTA (atual, commit 0cb4ea0)")
    print("=" * 80)
    for qid, q in SHORT_ABS.items():
        r = run_query(retriever, qid, q)
        results["short"][qid] = r
        status = "ABSENT (correto)" if r["is_absent"] else "FALSE POSITIVE (falhou)"
        print(f"\n  {qid}: '{q}'")
        print(f"    -> {status}")
        print(f"    quality={r['quality']} candidates={r['num_candidates']} top_score={r['top_score']:.4f} top_lexical={r['top_lexical_score']:.4f}")
        print(f"    top_id={r['top_id']}")

    print()
    print("=" * 80)
    print("QUERIES DE AUSÊNCIA — VERSÃO LONGA (reconstrução hipotética)")
    print("=" * 80)
    for qid, q in LONG_ABS.items():
        r = run_query(retriever, qid, q)
        results["long"][qid] = r
        status = "ABSENT (correto)" if r["is_absent"] else "FALSE POSITIVE (falhou)"
        print(f"\n  {qid}: '{q}'")
        print(f"    -> {status}")
        print(f"    quality={r['quality']} candidates={r['num_candidates']} top_score={r['top_score']:.4f} top_lexical={r['top_lexical_score']:.4f}")
        print(f"    top_id={r['top_id']}")

    # Summary
    short_correct = sum(1 for r in results["short"].values() if r["is_absent"])
    long_correct = sum(1 for r in results["long"].values() if r["is_absent"])
    print()
    print("=" * 80)
    print(f"RESUMO: curtas corretas {short_correct}/{len(SHORT_ABS)} | longas corretas {long_correct}/{len(LONG_ABS)}")
    print("=" * 80)

    out_path = REPO_ROOT / "audit" / "exp02_pr17" / "absence_length_analysis.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalvo em: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())