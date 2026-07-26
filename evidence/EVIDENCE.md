# MEC Lab — Baseline Evidence

## Execution Summary

- **Date**: 2026-07-26
- **Python**: 3.11.15
- **Database**: SQLite (WAL mode)
- **Dataset**: mec-lab-baseline-dataset v1.0
- **Eval dataset**: mec-lab-eval-dataset v1.0

## Commands Executed

```
python -m mec_lab --db mec_lab.db init-db
python -m mec_lab --db mec_lab.db load-dataset datasets/dev/baseline_dataset.json
python -m mec_lab --db mec_lab.db evaluate datasets/eval/eval_queries.json --ablation
python -m mec_lab --db mec_lab.db export-report datasets/eval/eval_queries.json --output evidence/report.md
python -m tests.run_tests
```

## Test Results

70 tests passed, 0 failed (unittest).

## Configuration

- Lexical weight: 1.0
- Semantic weight: 0.3
- Entity weight: 0.5
- Type weight: 0.5
- Relation weight: 0.4
- Temporal weight: 0.3
- State weight: 0.4
- Project weight: 0.6
- Top-K: 20
- Semantic adapter: DeterministicSemanticAdapter (hash-based, dimension=64)

## Key Metrics (full_mec variant)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Hit@1 | 0.733 | >= 0.80 | BELOW |
| Hit@3 | 0.867 | >= 0.95 | BELOW |
| MRR | 0.800 | — | — |
| Precision@1 | 0.733 | — | — |
| Fake source rate | 0.000 | 0 | PASS |
| Conflict detection rate | 0.000 | — | NEEDS INVESTIGATION |
| Capsule avg chars | 727 | — | — |

## Ablation Highlights

- Removing semantic (deterministic hash) IMPROVES Hit@1 from 0.733 to 0.867
- Removing graph REDUCES Hit@1 from 0.733 to 0.667
- Removing state IMPROVES Hit@1 to 0.800
- Temporal, typing, and checkpoint boost had no measurable effect

## Limitations

1. Semantic search uses deterministic hashing, not real embeddings — actually harms performance
2. No LLM-based re-ranking or inference generation
3. Conflict detection not triggering for supersedes relations
4. Dataset is synthetic (30 memories, 25 relations)
5. Thresholds from PLANO_DE_AVALIACAO.md not met: Hit@1=0.733 vs 0.80 target, Hit@3=0.867 vs 0.95 target
6. Python 3.11 used instead of 3.12 due to environment constraints
7. No ruff/mypy linting executed (tools not available in environment)
8. No real embedding model available (sentence-transformers not installed)
