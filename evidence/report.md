# MEC Lab — Evaluation Report

**Dataset**: mec-lab-eval-dataset
**Version**: 0.1.0
**Commit**: 
**Generated**: 2026-07-26T19:33:59.711117+00:00

## Aggregate Metrics

| Metric | Value |
|--------|-------|
| Queries | 15 |
| Precision@1 | 0.733 |
| Precision@3 | 0.467 |
| Precision@5 | 0.400 |
| Recall@3 | 0.733 |
| Recall@5 | 0.850 |
| Hit@1 | 0.733 |
| Hit@3 | 0.867 |
| Hit@5 | 0.867 |
| MRR | 0.800 |
| nDCG | 0.721 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 0.000 |
| Capsule avg chars | 727 |
| Capsule avg tokens | 181 |
| Reduction vs raw | 0.0% |
| Latency (ms) | 41 |

## Ablation Results

| Variant | Hit@1 | Hit@3 | MRR | Precision@1 |
|---------|-------|-------|-----|-------------|
| full_mec | 0.733 | 0.867 | 0.800 | 0.733 |
| no_semantic | 0.867 | 0.867 | 0.867 | 0.867 |
| no_graph | 0.667 | 0.867 | 0.756 | 0.667 |
| no_temporal | 0.733 | 0.867 | 0.800 | 0.733 |
| no_typing | 0.733 | 0.867 | 0.800 | 0.733 |
| no_state | 0.800 | 0.867 | 0.833 | 0.800 |
| no_checkpoint_boost | 0.733 | 0.867 | 0.800 | 0.733 |

## Per-Query Results

### q001-football-calendar
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.731
- Precision@1: 1.000
- Conflicts detected: 0

### q002-finance-duplicate
- Hit@1: False, Hit@3: True
- MRR: 0.500, nDCG: 0.596
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
- MRR: 1.000, nDCG: 0.904
- Precision@1: 1.000
- Conflicts detected: 0

### q006-queue-duplicate
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.851
- Precision@1: 1.000
- Conflicts detected: 0

### q007-football-status
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.932
- Precision@1: 1.000
- Conflicts detected: 0

### q008-obsolete-fact
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.420
- Precision@1: 1.000
- Conflicts detected: 0

### q009-analogy-duplication
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.909
- Precision@1: 1.000
- Conflicts detected: 0

### q010-missing-project
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### q011-conflict-test
- Hit@1: False, Hit@3: True
- MRR: 0.500, nDCG: 0.478
- Precision@1: 0.000
- Conflicts detected: 0

### q012-hypothesis-football
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q013-evidence-finance
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q014-finance-decision
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### q015-football-checkpoint
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

## Limitations

- Baseline semantic search uses deterministic hashing, not real embeddings.
- No LLM-based re-ranking or inference generation.
- Dataset is synthetic; real-world performance may differ.
