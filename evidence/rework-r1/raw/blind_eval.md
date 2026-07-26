# MEC Lab — Evaluation Report

**Dataset**: audit-blind-tests
**Version**: 0.1.0
**Commit**: 
**Generated**: 2026-07-26T20:32:25.738656+00:00

## Aggregate Metrics

| Metric | Value |
|--------|-------|
| Queries | 8 |
| Precision@1 | 0.250 |
| Precision@3 | 0.208 |
| Precision@5 | 0.125 |
| Recall@3 | 0.750 |
| Recall@5 | 0.750 |
| Hit@1 | 0.250 |
| Hit@3 | 0.500 |
| Hit@5 | 0.500 |
| MRR | 0.367 |
| nDCG | 0.477 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 6.000 |
| Capsule avg chars | 1194 |
| Capsule avg tokens | 298 |
| Reduction vs raw | 0.0% |
| Latency (ms) | 41 |

## Ablation Results

| Variant | Hit@1 | Hit@3 | MRR | Precision@1 |
|---------|-------|-------|-----|-------------|
| full_mec | 0.250 | 0.500 | 0.367 | 0.250 |
| no_semantic | 0.125 | 0.625 | 0.317 | 0.125 |
| no_graph | 0.125 | 0.500 | 0.295 | 0.125 |
| no_temporal | 0.250 | 0.500 | 0.367 | 0.250 |
| no_typing | 0.250 | 0.500 | 0.367 | 0.250 |
| no_state | 0.250 | 0.500 | 0.367 | 0.250 |
| no_checkpoint_boost | 0.250 | 0.500 | 0.367 | 0.250 |

## Per-Query Results

### blind-001-partial-clue
- Hit@1: False, Hit@3: False
- MRR: 0.143, nDCG: 0.398
- Precision@1: 0.000
- Conflicts detected: 0

### blind-002-two-similar-projects
- Hit@1: False, Hit@3: False
- MRR: 0.125, nDCG: 0.378
- Precision@1: 0.000
- Conflicts detected: 0

### blind-003-obsolete-replaced
- Hit@1: False, Hit@3: True
- MRR: 0.333, nDCG: 0.541
- Precision@1: 0.000
- Conflicts detected: 3

### blind-004-conflict-between-records
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 3

### blind-005-missing-information
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### blind-006-checkpoint-resumption
- Hit@1: False, Hit@3: True
- MRR: 0.333, nDCG: 0.500
- Precision@1: 0.000
- Conflicts detected: 0

### blind-007-explain-retrieval
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### blind-008-fact-vs-inference
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

## Limitations

- Baseline semantic search uses deterministic hashing, not real embeddings.
- No LLM-based re-ranking or inference generation.
- Dataset is synthetic; real-world performance may differ.
