"""Auditoria Exp-02 PR#17 — Reprodutibilidade em 3 execucoes independentes.

Executa o experimento 3 vezes sem alterar artefatos, capturando metricas
finais e ausencia para comparacao. NAO modifica queries.json ou gold_answers.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = REPO_ROOT / "audit" / "exp02_pr17" / "artifacts" / "experiments" / "exp-02"
RUN_SCRIPT = EXP_DIR / "run_experiment.py"
OUT_DIR = REPO_ROOT / "audit" / "exp02_pr17" / "reruns"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_once(idx: int) -> dict:
    """Run the experiment once and collect final metrics."""
    print(f"\n{'='*60}\nEXECUTION {idx}/3\n{'='*60}")
    env = {"PYTHONPATH": str(REPO_ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, str(RUN_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**__import__("os").environ, **env},
    )
    stdout = proc.stdout
    stderr = proc.stderr

    # Parse aggregate_metrics.json written by the run
    agg_path = EXP_DIR / "RAW_RESULTS" / "aggregate_metrics.json"
    agg = json.loads(agg_path.read_text(encoding="utf-8"))
    fm = agg["final_metrics"]
    abs_eval = agg["absence_evaluation"]

    # Save run log
    (OUT_DIR / f"run_{idx}_stdout.txt").write_text(stdout, encoding="utf-8")
    (OUT_DIR / f"run_{idx}_stderr.txt").write_text(stderr, encoding="utf-8")
    (OUT_DIR / f"run_{idx}_aggregate.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    metrics = {
        "run": idx,
        "exit_code": proc.returncode,
        "num_queries": fm["num_queries"],
        "hit_1_rate": fm["hit_1_rate"],
        "hit_3_rate": fm["hit_3_rate"],
        "hit_5_rate": fm["hit_5_rate"],
        "mrr": fm["mrr"],
        "precision_1": fm["precision_1"],
        "fake_source_rate": fm["fake_source_rate"],
        "fake_source_count": fm["fake_source_count"],
        "deterministic": agg["deterministic"],
        "absence": {
            qid: {
                "is_absent": v["is_absent"],
                "quality": v["quality"],
                "num_candidates": v["num_candidates"],
                "top_score": v["top_score"],
            }
            for qid, v in abs_eval.items()
        },
    }
    print(f"  exit={proc.returncode}")
    print(f"  Hit@1={metrics['hit_1_rate']:.4f} Hit@3={metrics['hit_3_rate']:.4f} MRR={metrics['mrr']:.4f}")
    print(f"  FakeSrc={metrics['fake_source_rate']:.4f} Absence={sum(1 for v in metrics['absence'].values() if v['is_absent'])}/5")
    return metrics


def main() -> int:
    runs = [run_once(i) for i in range(1, 4)]

    # Compare across runs
    all_match = True
    base = runs[0]
    for idx, r in enumerate(runs[1:], 2):
        ok = (
            r["hit_1_rate"] == base["hit_1_rate"]
            and r["hit_3_rate"] == base["hit_3_rate"]
            and r["mrr"] == base["mrr"]
            and r["fake_source_rate"] == base["fake_source_rate"]
            and r["num_queries"] == base["num_queries"]
            and all(
                r["absence"][qid]["is_absent"] == base["absence"][qid]["is_absent"]
                for qid in base["absence"]
            )
        )
        if not ok:
            all_match = False
        print(f"\nRun 1 vs Run {idx}: {'IDENTICAL' if ok else 'DIFFERS'}")

    print(f"\n{'='*60}")
    print(f"DETERMINISM (3 runs): {'CONFIRMED' if all_match else 'FAILED'}")
    print(f"{'='*60}")

    summary = {
        "runs": runs,
        "determinism_confirmed": all_match,
        "base_metrics": {
            "hit_1_rate": base["hit_1_rate"],
            "hit_3_rate": base["hit_3_rate"],
            "hit_5_rate": base["hit_5_rate"],
            "mrr": base["mrr"],
            "precision_1": base["precision_1"],
            "fake_source_rate": base["fake_source_rate"],
            "fake_source_count": base["fake_source_count"],
            "num_queries": base["num_queries"],
            "absence_correct": sum(1 for v in base["absence"].values() if v["is_absent"]),
            "absence_total": len(base["absence"]),
        },
    }
    (OUT_DIR / "rerun_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if all_match else 1


if __name__ == "__main__":
    sys.exit(main())