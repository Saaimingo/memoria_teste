# MEC Lab — Evaluation Report

**Dataset**: mec-lab-eval-dataset
**Version**: 0.2.0
**Commit**: R2
**Generated**: 2026-07-26T21:01:36.235901+00:00

## Aggregate Metrics

| Metric | Value |
|--------|-------|
| Queries | 15 |
| Precision@1 | 0.667 |
| Precision@3 | 0.489 |
| Precision@5 | 0.427 |
| Recall@3 | 0.767 |
| Recall@5 | 0.917 |
| Hit@1 | 0.667 |
| Hit@3 | 0.867 |
| Hit@5 | 0.867 |
| MRR | 0.756 |
| nDCG | 0.718 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 18.000 |
| Capsule avg chars | 715 |
| Capsule avg tokens | 178 |
| Reduction vs raw | 0.0% |
| Latency (ms) | 53 |

## Ablation Results

| Variant | Hit@1 | Hit@3 | MRR | Precision@1 |
|---------|-------|-------|-----|-------------|
| full_mec | 0.667 | 0.867 | 0.756 | 0.667 |
| no_semantic | 0.667 | 0.800 | 0.739 | 0.667 |
| no_graph | 0.667 | 0.867 | 0.756 | 0.667 |
| no_temporal | 0.667 | 0.867 | 0.756 | 0.667 |
| no_typing | 0.667 | 0.867 | 0.756 | 0.667 |
| no_state | 0.667 | 0.867 | 0.756 | 0.667 |
| no_checkpoint_boost | 0.667 | 0.867 | 0.756 | 0.667 |

## Per-Query Results

### q001-football-calendar
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.710
- Precision@1: 1.000
- Conflicts detected: 3

### q002-finance-duplicate
- Hit@1: False, Hit@3: True
- MRR: 0.500, nDCG: 0.668
- Precision@1: 0.000
- Conflicts detected: 0

### q003-decision-normative
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### q004-football-decisions
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q005-finance-solution
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.876
- Precision@1: 1.000
- Conflicts detected: 0

### q006-queue-duplicate
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.852
- Precision@1: 1.000
- Conflicts detected: 0

### q007-football-status
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.932
- Precision@1: 1.000
- Conflicts detected: 3

### q008-obsolete-fact
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.590
- Precision@1: 1.000
- Conflicts detected: 3

### q009-analogy-duplication
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q010-missing-project
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### q011-conflict-test
- Hit@1: False, Hit@3: True
- MRR: 0.333, nDCG: 0.515
- Precision@1: 0.000
- Conflicts detected: 3

### q012-hypothesis-football
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 3

### q013-evidence-finance
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q014-finance-decision
- Hit@1: False, Hit@3: True
- MRR: 0.500, nDCG: 0.631
- Precision@1: 0.000
- Conflicts detected: 0

### q015-football-checkpoint
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 3

## Limitations

- Baseline semantic search uses deterministic hashing, not real embeddings.
- No LLM-based re-ranking or inference generation.
- Dataset is synthetic; real-world performance may differ.
