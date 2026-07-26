"""Audit verification script — reproduces all 20 queries and compares with gold answers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mec_lab.evaluation import EvalDataset
from mec_lab.retrieval import HybridRetriever, RetrievalConfig
from mec_lab.storage import Storage

# Dynamic import of populate scripts (same approach as run_experiment.py)
import importlib.util as _iu

EXP_DIR = Path(__file__).resolve().parents[1] / "experiments" / "exp-01"


def _load_module(name, path):
    spec = _iu.spec_from_file_location(name, path)
    mod = _iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p1 = _load_module("populate_phase_1", EXP_DIR / "populate_phase_1.py").populate
p2 = _load_module("populate_phase_2", EXP_DIR / "populate_phase_2.py").populate
p3 = _load_module("populate_phase_3", EXP_DIR / "populate_phase_3.py").populate
p4 = _load_module("populate_phase_4", EXP_DIR / "populate_phase_4.py").populate

PROJECT_ID = "proj-atlas"


def main():
    store = Storage(":memory:")
    store.init_schema()

    # Populate all 4 phases
    p1(store, PROJECT_ID)
    p2(store, PROJECT_ID)
    p3(store, PROJECT_ID)
    p4(store, PROJECT_ID)

    # Load queries and gold answers
    queries_path = Path(__file__).resolve().parents[1] / "experiments" / "exp-01" / "queries.json"
    gold_path = Path(__file__).resolve().parents[1] / "experiments" / "exp-01" / "gold_answers.json"

    dataset = EvalDataset.from_json(queries_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    retriever = HybridRetriever(store, config=RetrievalConfig())

    results = []
    for qc in dataset.queries:
        result = retriever.search(qc.query, project_id=qc.expected_project_id)
        top5_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
        top5_scores = [cs.total_score for cs in result.candidate_scores[:5]]

        # Check Hit@1 and Hit@3
        expected = set(qc.expected_ids)
        hit_1 = top5_ids[0] in expected if top5_ids else False
        hit_3 = any(mid in expected for mid in top5_ids[:3])

        # Check gold matches
        gold_entry = gold["answers"].get(qc.query_id, {})
        gold_ids = set(gold_entry.get("expected_ids", []))
        gold_hit_1 = top5_ids[0] in gold_ids if top5_ids else False
        gold_hit_3 = any(mid in gold_ids for mid in top5_ids[:3])

        entry = {
            "query_id": qc.query_id,
            "query": qc.query,
            "expected_ids": qc.expected_ids,
            "gold_expected_ids": list(gold_ids),
            "top5_ids": top5_ids,
            "top5_scores": [round(s, 4) for s in top5_scores],
            "hit_1": hit_1,
            "hit_3": hit_3,
            "gold_hit_1": gold_hit_1,
            "gold_hit_3": gold_hit_3,
            "quality": result.quality,
            "conflicts": result.conflicts,
            "missing": result.missing_information,
            "num_conflicts": len(result.conflicts),
        }
        results.append(entry)

        status = "✓" if (hit_1 or hit_3) else "✗"
        print(f"[{status}] {qc.query_id}: Hit@1={hit_1}, Hit@3={hit_3}, quality={result.quality}, "
              f"top3={top5_ids[:3]}")

    # Summary
    total = len(results)
    hit_1_count = sum(1 for r in results if r["hit_1"])
    hit_3_count = sum(1 for r in results if r["hit_3"])
    print(f"\n=== SUMMARY ===")
    print(f"Total queries: {total}")
    print(f"Hit@1: {hit_1_count}/{total} = {hit_1_count/total:.3f}")
    print(f"Hit@3: {hit_3_count}/{total} = {hit_3_count/total:.3f}")

    # Save raw results
    audit_dir = Path(__file__).resolve().parent
    (audit_dir / "verify_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResults saved to audit/verify_results.json")


if __name__ == "__main__":
    main()
