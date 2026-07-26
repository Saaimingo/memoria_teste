# MEC Lab — Evaluation Report

**Dataset**: reaudit-holdout-r1
**Version**: 0.1.0
**Commit**: 
**Generated**: 2026-07-26T20:49:17.517050+00:00

## Aggregate Metrics

| Metric | Value |
|--------|-------|
| Queries | 10 |
| Precision@1 | 0.500 |
| Precision@3 | 0.433 |
| Precision@5 | 0.367 |
| Recall@3 | 0.692 |
| Recall@5 | 0.750 |
| Hit@1 | 0.500 |
| Hit@3 | 0.700 |
| Hit@5 | 0.700 |
| MRR | 0.573 |
| nDCG | 0.515 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 3.000 |
| Capsule avg chars | 917 |
| Capsule avg tokens | 229 |
| Reduction vs raw | 0.0% |
| Latency (ms) | 39 |

## Ablation Results

| Variant | Hit@1 | Hit@3 | MRR | Precision@1 |
|---------|-------|-------|-----|-------------|
| full_mec | 0.500 | 0.700 | 0.573 | 0.500 |
| no_semantic | 0.500 | 0.600 | 0.581 | 0.500 |
| no_graph | 0.500 | 0.700 | 0.567 | 0.500 |
| no_temporal | 0.500 | 0.700 | 0.573 | 0.500 |
| no_typing | 0.500 | 0.700 | 0.573 | 0.500 |
| no_state | 0.500 | 0.700 | 0.573 | 0.500 |
| no_checkpoint_boost | 0.500 | 0.700 | 0.573 | 0.500 |

## Per-Query Results

### hold-001-mixed-domain-search
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.984
- Precision@1: 1.000
- Conflicts detected: 0

### hold-002-vague-temporal
- Hit@1: False, Hit@3: True
- MRR: 0.333, nDCG: 0.095
- Precision@1: 0.000
- Conflicts detected: 0

### hold-003-entity-driven
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 1.000
- Precision@1: 1.000
- Conflicts detected: 0

### hold-004-conflict-aware
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.959
- Precision@1: 1.000
- Conflicts detected: 3

### hold-005-cross-domain-analogy
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.803
- Precision@1: 1.000
- Conflicts detected: 0

### hold-006-obsolete-navigation
- Hit@1: False, Hit@3: False
- MRR: 0.059, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### hold-007-missing-tool
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### hold-008-inference-separation
- Hit@1: False, Hit@3: False
- MRR: 0.000, nDCG: 0.000
- Precision@1: 0.000
- Conflicts detected: 0

### hold-009-single-word-clue
- Hit@1: True, Hit@3: True
- MRR: 1.000, nDCG: 0.807
- Precision@1: 1.000
- Conflicts detected: 3

### hold-010-checkpoint-next-step
- Hit@1: False, Hit@3: True
- MRR: 0.333, nDCG: 0.500
- Precision@1: 0.000
- Conflicts detected: 0

## Limitations

- Baseline semantic search uses deterministic hashing, not real embeddings.
- No LLM-based re-ranking or inference generation.
- Dataset is synthetic; real-world performance may differ.
