"""Auditoria Exp-02 PR#17 — Conjunto adversarial reservado.

Roda as 15 queries adversariais reservadas (incluindo 4 de ausência NOVAS,
na forma longa natural, não encurtadas) contra o banco populado idêntico
ao do experimento. Não altera nenhum artefato do experimento.

Saída: audit/exp02_pr17/reserved_adversarial_results.json
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
RESERVED_PATH = REPO_ROOT / "audit" / "exp02_pr17" / "RESERVED_ADVERSARIAL_QUERIES.json"
PROJECT_ID = "proj-boreal"


def populate_all(store: Storage) -> None:
    import importlib.util
    for phase in range(1, 6):
        phase_file = EXP_DIR / f"populate_phase_{phase}.py"
        spec = importlib.util.spec_from_file_location(f"populate_phase_{phase}", phase_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.populate(store, PROJECT_ID)


def evaluate_query(retriever: HybridRetriever, q: dict) -> dict:
    result = retriever.search(q["query"], project_id=PROJECT_ID)
    expected = set(q["expected_ids"])
    top3_ids = [cs.memory_id for cs in result.candidate_scores[:3]]
    has_lexical = any(cs.lexical_score > 0.0 for cs in result.candidate_scores)
    is_absent = (
        result.quality == "none"
        or not has_lexical
        or len(result.candidate_scores) == 0
    )
    expected_absent = len(expected) == 0
    correct = (is_absent and expected_absent) or (
        not expected_absent and any(eid in top3_ids for eid in expected)
    )
    return {
        "query_id": q["query_id"],
        "query": q["query"],
        "category": q.get("_category", "?"),
        "expected_ids": q["expected_ids"],
        "expected_absent": expected_absent,
        "quality": result.quality,
        "num_candidates": len(result.candidate_scores),
        "top_score": result.candidate_scores[0].total_score if result.candidate_scores else 0.0,
        "top_lexical_score": result.candidate_scores[0].lexical_score if result.candidate_scores else 0.0,
        "top3_ids": top3_ids,
        "primary_in_top3": any(eid in top3_ids for eid in expected) if expected else True,
        "is_absent": is_absent,
        "absence_correct": (is_absent and expected_absent) if expected_absent else None,
        "hit_1": (not expected_absent and bool(result.candidate_scores) and result.candidate_scores[0].memory_id in expected),
        "hit_3": (not expected_absent and any(eid in top3_ids for eid in expected)),
        "correct": correct,
    }


def main() -> int:
    store = Storage(":memory:")
    store.init_schema()
    populate_all(store)
    retriever = HybridRetriever(store)
    print(f"Memories: {store.count_memories()} | Relations: {len(store.list_all_relations())}")

    data = json.loads(RESERVED_PATH.read_text(encoding="utf-8"))
    rows = []
    abs_correct = 0
    abs_total = 0
    hit1_count = 0
    hit3_count = 0
    for q in data["queries"]:
        r = evaluate_query(retriever, q)
        rows.append(r)
        if r["expected_absent"]:
            abs_total += 1
            if r["absence_correct"]:
                abs_correct += 1
        else:
            if r["hit_1"]:
                hit1_count += 1
            if r["hit_3"]:
                hit3_count += 1
        status = "OK" if r["correct"] else "FAIL"
        cat = r["category"]
        print(f"\n  [{status}] {r['query_id']} ({cat})")
        print(f"      q: {r['query']}")
        print(f"      quality={r['quality']} cands={r['num_candidates']} top_score={r['top_score']:.4f} top_lex={r['top_lexical_score']:.4f}")
        print(f"      top3={r['top3_ids']} expected={r['expected_ids']}")
        if r["expected_absent"]:
            print(f"      is_absent={r['is_absent']} absence_correct={r['absence_correct']}")

    n_present = len(rows) - abs_total
    print()
    print("=" * 70)
    print(f"RESERVED ADVERSARIAL RESULTS")
    print("=" * 70)
    print(f"  Total queries: {len(rows)}")
    print(f"  Absence queries: {abs_total} | correct: {abs_correct}/{abs_total}")
    print(f"  Present queries (Hit@1/Hit@3): {hit1_count}/{n_present} = {hit1_count/max(1,n_present):.3f} | {hit3_count}/{n_present} = {hit3_count/max(1,n_present):.3f}")
    print("=" * 70)

    out_path = REPO_ROOT / "audit" / "exp02_pr17" / "reserved_adversarial_results.json"
    summary = {
        "total": len(rows),
        "absence_total": abs_total,
        "absence_correct": abs_correct,
        "present_queries": n_present,
        "hit_1_count": hit1_count,
        "hit_3_count": hit3_count,
        "hit_1_rate": hit1_count / max(1, n_present),
        "hit_3_rate": hit3_count / max(1, n_present),
        "results": rows,
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalvo em: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())