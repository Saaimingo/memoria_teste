# MEC Lab — Architecture

## Overview

The MEC Lab is an experimental baseline for testing structured causal memory (MEC) hypotheses. It provides typed memory persistence, graph-based relations, multi-strategy retrieval, and reproducible evaluation — all running offline on SQLite.

## Package Structure

```
src/mec_lab/
├── __init__.py          # version
├── __main__.py          # python -m mec_lab entry
├── domain/
│   ├── __init__.py      # re-exports
│   ├── enums.py         # MemoryType, EpistemicStatus, RelationType, etc.
│   └── models.py        # Pydantic v2 models: Fact, Decision, Hypothesis, etc.
├── storage/
│   └── __init__.py      # SQLite backend, schema v1, CRUD, import/export
├── retrieval/
│   └── __init__.py      # LexicalRetriever, HybridRetriever, clue extraction, semantic adapters
├── context/
│   └── __init__.py      # CapsuleBuilder, layered capsule reconstruction
├── evaluation/
│   └── __init__.py      # Evaluator, metrics, ablation runner, report generator
└── cli/
    ├── __init__.py      # Click CLI: 12 commands
    └── __main__.py      # python -m mec_lab.cli entry
```

## Data Flow

```
Free-text query
  → extract_clues() (deterministic heuristics)
  → HybridRetriever.search()
    ├── Lexical score (Jaccard word overlap)
    ├── Semantic score (DeterministicSemanticAdapter: hash-based vector)
    ├── Entity match
    ├── Type bonus
    ├── Graph relation boost
    ├── Temporal validity check
    └── State/epistemic quality
  → RetrievalResult (separated by type, with conflicts, missing, inferences)
  → CapsuleBuilder.build()
    ├── Layer 1: Checkpoints
    ├── Layer 2: Active decisions
    ├── Layer 3: Current facts
    ├── Layer 4: Related episodes
    ├── Layer 5: Applicable learnings
    └── Layer 6: Documents
  → Capsule (with size metrics, gaps, conflicts)
  → build_resumption_prompt() → agent-readable text
```

## Key Design Decisions

1. **SQLite with no FK enforcement on project_id**: Allows loading memories before projects.
2. **Unified `memories` table with `extra_json`**: All 8 memory types stored in one table; type-specific fields serialized to JSON.
3. **Deterministic semantic adapter**: Produces stable, reproducible pseudo-embeddings via MD5 hashing. Not a real semantic model — intentionally simple for baseline.
4. **No LLM dependency**: All scoring is formula-based; inference generation uses heuristics only.
5. **Click instead of Typer**: Chosen because Click was already available in the environment.
6. **unittest instead of pytest**: Same reason — environment constraints.

## Scales and Limits

- Designed for <10K memories; SQLite single-file, no sharding.
- Embedding cache in-memory; not suitable for large-scale production.
- All operations are synchronous; no async support.
