"""Auditoria Exp-02 PR#17 — Verificação individual dos 27 resultados.

Para cada uma das 27 queries do experimento, compara:
  - o Hit@1, Hit@3, MRR declarados em RAW_RESULTS/per_query_final.json
  - o esperado em gold_answers.json
  - o resultado ao reexecutar a query contra o banco populado

Reporta discrepâncias entre o declarado e o reproduzido, e avalia
individualmente se cada acerto é lexicamente justo ou se parece ter
sido fabricado por alinhamento de conteúdo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mec_lab.evaluation import Evaluator, EvalDataset
from mec_lab.retrieval import HybridRetriever
from mec_lab.storage import Storage

EXP_DIR = REPO_ROOT / "audit" / "exp02_pr17" / "artifacts" / "experiments" / "exp-02"
PROJECT_ID = "proj-boreal"


def populate_all(store: Storage) -> None:
    import importlib.util
    for phase in range(1, 6):
        phase_file = EXP_DIR / f"populate_phase_{phase}.py"
        spec = importlib.util.spec_from_file_location(f"populate_phase_{phase}", phase_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.populate(store, PROJECT_ID)


def main() -> int:
    store = Storage(":memory:")
    store.init_schema()
    populate_all(store)

    queries_path = EXP_DIR / "queries.json"
    gold_path = EXP_DIR / "gold_answers.json"
    declared_path = EXP_DIR / "RAW_RESULTS" / "per_query_final.json"

    queries = EvalDataset.from_json(queries_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    declared = json.loads(declared_path.read_text(encoding="utf-8"))

    retriever = HybridRetriever(store)
    evaluator = Evaluator(store, retriever)
    metrics = evaluator.evaluate(queries)

    declared_map = {d["query_id"]: d for d in declared}
    gold_map = {a["query_id"]: a for a in gold["answers"]}

    out_rows = []
    discrepancies = 0
    for sr in metrics.per_query:
        qid = sr.query_id
        dec = declared_map.get(qid, {})
        g = gold_map.get(qid, {})

        row = {
            "query_id": qid,
            "temporal_state": g.get("temporal_state", "?"),
            "gold_primary": g.get("primary_expected_ids", []),
            "declared_hit_1": dec.get("hit_1"),
            "declared_hit_3": dec.get("hit_3"),
            "declared_mrr": dec.get("mrr"),
            "reproduced_hit_1": sr.hit_1,
            "reproduced_hit_3": sr.hit_3,
            "reproduced_mrr": round(sr.mrr, 4),
            "match": (
                sr.hit_1 == dec.get("hit_1")
                and sr.hit_3 == dec.get("hit_3")
                and abs(sr.mrr - dec.get("mrr", 0.0)) < 1e-6
            ),
            "fake_sources": sr.fake_sources,
            "num_retrieved": sr.num_retrieved,
            "relevant_retrieved": sr.relevant_retrieved,
        }
        if not row["match"]:
            discrepancies += 1
        out_rows.append(row)

    print(f"Total queries: {len(out_rows)}")
    print(f"Discrepancies between declared and reproduced: {discrepancies}")
    print()
    print(f"{'Query ID':<32} {'State':<14} {'H1(d/r)':<12} {'H3(d/r)':<12} {'MRR(d/r)':<22} {'Match'}")
    print("-" * 110)
    for r in out_rows:
        h1 = f"{r['declared_hit_1']}/{r['reproduced_hit_1']}"
        h3 = f"{r['declared_hit_3']}/{r['reproduced_hit_3']}"
        mrr = f"{r['declared_mrr']}/{r['reproduced_mrr']}"
        mark = "OK" if r["match"] else "DIFF"
        print(f"{r['query_id']:<32} {r['temporal_state']:<14} {h1:<12} {h3:<12} {mrr:<22} {mark}")

    out_path = REPO_ROOT / "audit" / "exp02_pr17" / "verify_27_results.json"
    out_path.write_text(json.dumps(out_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalvo em: {out_path}")
    return 0 if discrepancies == 0 else 1


if __name__ == "__main__":
    sys.exit(main())