# AUDIT REPORT — PR #2 (MEC Lab Baseline)

**Auditor**: Independent Agent (audit/mec-lab-baseline-pr2)
**Target**: feat/mec-lab-baseline @ 73c14aa
**Date**: 2026-07-26
**Environment**: Windows 10, Python 3.11.15, Click 8.3.1, Pydantic 2.13.4

---

## 1. VERDICT

**REWORK_REQUIRED**

The baseline is structurally sound but contains critical flaws that invalidate its evaluation claims. The retrieval scoring is dominated by stopword noise, the semantic adapter is non-functional, and the blind test results (Hit@1=0.000) reveal severe overfitting to the eval dataset. These issues must be fixed before the lab can test MEC hypotheses.

---

## 2. CLAIMS vs REPRODUCTION

| Claim (implementer) | Reproduced? | Notes |
|---------------------|-------------|-------|
| 70 tests pass | YES | All 70 reproduce identically |
| Hit@1=0.733 | YES | Matches exactly |
| Hit@3=0.867 | YES | Matches exactly |
| Ablation: no_semantic improves | YES | 0.733→0.867 reproduced |
| Ablation: no_graph reduces | YES | 0.733→0.667 reproduced |
| No fake sources | YES | 0 fake sources detected |
| Conflict detection works | NO | Returns 0.000 — only checks CONTRADICTED_BY, ignores SUPERSEDES |
| 8 memory types validated | PARTIAL | Models exist and load, but Evidence/Learning/Hypothesis never exercise full field set in tests |
| Capsule reduces context | UNVERIFIABLE | Reduction vs raw = 0.0% (no raw history size provided) |

---

## 3. TEST QUALITY AUDIT

### 3.1 Weak asserts found

- `test_create_minimal_fact`: `self.assertTrue(f.id)` — always passes (auto-generated UUID)
- `test_result_structure`: `hasattr(result, "retrieved_facts")` — structure check, not behavioral
- `test_evaluate`: `self.assertGreaterEqual(metrics.mrr, 0.0); self.assertLessEqual(metrics.mrr, 1.0)` — tautological (MRR always in [0,1] by definition)
- `test_capsule_metrics`: `self.assertGreaterEqual(metrics.capsule_avg_chars, 0)` — always true
- `test_generate_report`: checks string presence, not metric correctness

### 3.2 Missing test categories

- **No negative tests for invalid input**: empty strings, None values, malformed JSON
- **No conflict detection tests**: The `_detect_conflicts` method is never directly unit-tested
- **No obsolete/superseded behavior tests**: Does retrieval correctly handle version chains?
- **No edge cases**: empty database, duplicate IDs, circular relations
- **No test for 7 of 8 memory types** beyond "can create": Evidence, Hypothesis, Learning, DocumentRecord tested only for type attribute, not field integrity
- **No ranking correctness tests**: Tests check scores exist, not that they're computed correctly

### 3.3 Fixture-answer coupling

- `TestEvaluator.setUp` creates facts with IDs f1, f2, f3 and query IDs that match those exact IDs
- `TestAblation.setUp` creates fact "f1" with content "Football simulator with calendar" and query "football calendar" — the query terms appear verbatim in content
- This is a form of indirect leakage: the tests only verify the happy path where query terms overlap content terms

### 3.4 Tests that can never fail

- `test_fake_source_rate`: asserts `metrics.fake_source_count == 0` — but fake_source_count is computed as `sum(1 for rid in retrieved_ids if self.store.get_memory(rid) is None)`. Since the setup creates memories that are always retrieved, this will always be 0. It doesn't test the detection logic.
- `test_schema_idempotent`: always passes because init_schema uses IF NOT EXISTS

---

## 4. DATASET & GABARITO AUDIT

### 4.1 No direct leakage found

- Eval queries are in a separate file from dev dataset
- No query text appears verbatim in any memory content
- No expected_ids are derived from query content via hardcoded mapping

### 4.2 Indirect coupling (overfitting)

The eval queries were crafted with terms that overlap heavily with the target memory content:

| Query | Terms in target content |
|-------|------------------------|
| "calendário e aposentadoria no futebol" | "calendário", "aposentadoria", "futebol" all appear in target |
| "alertas duplicados depois de reiniciar" | "alertas", "duplicados", "reiniciar" all in target |
| "decisão sobre pygame" | "Pygame" in decision content |

This is not leakage per se, but it means the eval measures lexical overlap, not retrieval intelligence. The blind tests (Section 6) expose this.

### 4.3 Eval queries with no expected results

q003 and q010 expect empty results. The retriever correctly returns empty for q010 but fails q003 (returns results when it should return none). This means the system cannot reliably distinguish "information exists but is irrelevant" from "information does not exist."

---

## 5. ARCHITECTURE COMPONENT CLASSIFICATION

| Component | Classification |
|-----------|---------------|
| Domain models (enums, Pydantic) | VALID FOR BASELINE |
| SQLite storage | VALID FOR BASELINE |
| Lexical retriever | VALID, BUT SUPERFICIAL (stopword-dominated) |
| Semantic adapter (hash-based) | INCORRECT (injects noise, proven harmful) |
| Hybrid retriever scoring | INCORRECT (stopwords dominate, weights uncalibrated) |
| Conflict detection | INCORRECT (only checks CONTRADICTED_BY) |
| Clue extraction | VALID, BUT SUPERFICIAL |
| Capsule builder | VALID FOR BASELINE |
| Evaluation framework | VALID FOR BASELINE |
| CLI | VALID FOR BASELINE |
| Ablation runner | VALID FOR BASELINE |
| Report generator | VALID FOR BASELINE |

---

## 6. BLIND TEST RESULTS (AUDITOR-CREATED QUERIES)

8 new queries, never seen by implementer:

| Metric | full_mec | no_semantic |
|--------|----------|-------------|
| Hit@1 | **0.000** | **0.000** |
| Hit@3 | 0.250 | 0.500 |
| MRR | 0.183 | 0.236 |
| Precision@1 | 0.000 | 0.000 |

**Contrast with original eval: Hit@1=0.733 vs blind Hit@1=0.000.** This 73pp drop confirms the retriever overfits to the original eval dataset.

### Blind query failures analyzed:

- **blind-001** ("bug de repetição quando ligava de novo"): episode-queue-001 at rank 3, episode-fin-001 not found. The word "bug" matches football episode (wrong domain).
- **blind-006** ("no que devo trabalhar agora no projeto de estoque"): checkpoint-queue-001 not retrieved at all. episode-queue-001 ranks higher because "estoque" matches its content directly, while checkpoint uses "Filas" not "estoque."
- **blind-007** ("por que o Redis foi escolhido"): decision-fin-001 not in top 10. Stopwords "por", "que", "o", "foi" dominate the Jaccard score. "Redis" IS in the content, but with only 1 matching content word vs 5 query stopwords matching random content, the signal is drowned.

---

## 7. THREE ANOMALIES — ROOT CAUSE

### 7.1 Why removing semantic IMPROVES results

The `DeterministicSemanticAdapter` produces pseudo-random normalized vectors via MD5 hashing. Cosine similarity between unrelated random vectors in 64 dimensions has expected value ≈ 0 with variance ≈ 1/√64 = 0.125. At weight 0.3, this injects ±0.04 noise into every score. This noise randomly reorders candidates, sometimes beneficially, usually harmfully. Removing it eliminates the noise.

**The adapter is not "semantic" in any meaningful sense.** It should not be called semantic.

### 7.2 Why removing state IMPROVES results

The state bonus gives +0.08 to all VERIFIED items. Since 28/30 dataset items are VERIFIED, this is nearly a constant offset. The 2 non-VERIFIED items (hypothesis-fb-001: UNVERIFIED, fact-fb-005-obsolete: OBSOLETE) are penalized. Query q011 expects fact-fb-005-obsolete as a relevant result; the -0.08 penalty pushes it below other items.

However, the 0.733→0.800 improvement is a 1-query difference (11→12 correct out of 15). This is within noise range for a 15-query dataset; the effect may not be statistically significant.

### 7.3 Why supersedes doesn't trigger conflict detection

`_detect_conflicts()` hardcodes `RelationType.CONTRADICTED_BY`:

```python
rels = self.storage.search_relations(
    source_id=mems[i].id, target_id=mems[j].id,
    relation_type=RelationType.CONTRADICTED_BY,
)
```

The dataset has 1 CONTRADICTED_BY relation (f4→f3 in populated test store), but the eval dataset's supersedes chain (fact-fb-005-v2 SUPERSEDES fact-fb-005-obsolete) uses a different relation type. The method never checks for SUPERSEDES, OBSOLETE status, or version conflicts.

**This is a bug, not a limitation.**

---

## 8. ADDITIONAL FINDINGS

### 8.1 Stopword contamination in lexical scoring

The `_lexical_score` method splits `query_lower` on whitespace WITHOUT filtering stopwords. Common Portuguese words ("que", "por", "foi", "o", "de", "em") match random content and dominate the Jaccard score. This is why blind queries with natural language phrasing perform worse than eval queries with keyword-heavy phrasing.

### 8.2 Entity extraction never fires

`mem.entities` stores dicts like `{"name": "Redis", "entity_type": "tool"}`. But in `_score_candidate`, entities are accessed as `e["name"]` only if `isinstance(e, dict)`. The dataset serializes entities correctly, but most memories have empty entity lists. The entity_score contribution is effectively zero for all queries.

### 8.3 Temporal scoring never fires

`valid_from` and `valid_to` are `None` for all dataset items. The temporal score is always 0.0, making the temporal component dead code.

### 8.4 Query q003 returns false positives

Query "Qual decisão definiu que a conversa não era fonte normativa?" should return empty (no such decision exists). But the retriever returns results because "decisão" matches Decision records. The system cannot distinguish "I found decisions" from "I found the specific decision you asked about."

---

## 9. SEVERITY SUMMARY

| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 3 | Blind test Hit@1=0.000, stopword-dominated scoring, semantic adapter injects noise |
| HIGH | 2 | Conflict detection broken, eval dataset overfitting |
| MEDIUM | 4 | Entity extraction dead code, temporal dead code, no negative tests, weak asserts |
| LOW | 3 | Python 3.11 vs 3.12, no Ruff/Mypy, small dataset |

---

## 10. REQUIRED REWORK (minimum for re-evaluation)

1. **Fix lexical scoring**: Filter stopwords from query before Jaccard calculation, or use TF-IDF weighting.
2. **Replace or fix semantic adapter**: Either implement real embeddings (sentence-transformers) or remove the component entirely. The current MD5-hash adapter is worse than nothing.
3. **Fix conflict detection**: Extend `_detect_conflicts` to check SUPERSEDES, OBSOLETE status, and version conflicts.
4. **Add blind test suite to evaluation pipeline**: The 8 blind queries (or equivalent) should be part of the standard eval.
5. **Recalibrate weights**: The default weights have no empirical justification. Run a proper hyperparameter sweep or document the rationale.
6. **Add negative tests**: Edge cases, empty DB, invalid input, circular relations.
7. **Add behavioral tests**: Not just "has attribute X" but "X has correct value for scenario Y."
8. **Separate stopword filtering concerns**: The `extract_clues` stopword list should be reused by the lexical scorer.

---

## 11. CONDITIONS FOR NEXT EVALUATION

- All 8 rework items above addressed with evidence
- Blind test Hit@1 > 0.50 (relaxed from original 0.80 given early stage)
- Conflict detection rate > 0 for queries with known conflicts
- Semantic component either removed or backed by real embeddings
- New tests: ≥ 10 negative/edge case tests
- All original 70 tests still passing
- No change to eval dataset or gold answers

---

## 12. EVIDENCE PRESERVED

- `audit/RAW_RESULTS/test_run_*.txt` — full unittest output
- `audit/RAW_RESULTS/ablation_reproduced.txt` — ablation reproduction
- `audit/RAW_RESULTS/blind_test_results.txt` — blind test results
- `audit/tests_blind/blind_queries.json` — 8 auditor-created queries
