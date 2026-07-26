# REAUDIT REPORT — PR #6 (Rework R1)

**Reauditor**: Independent Agent (audit/rework-r1-pr6)  
**Target**: rework/mec-lab-baseline-r1 @ 7cfc051  
**Base**: feat/mec-lab-baseline @ 73c14aa  
**Date**: 2026-07-26  
**Environment**: Windows 10, Python 3.11.15, Pydantic 2.13.4, Click 8.3.1

---

## 1. VERDICT

**REWORK_REQUIRED**

The rework fixes critical bugs from the original baseline (conflict detection, semantic adapter, stopword filtering) and adds meaningful test coverage. However, a newly introduced bug in temporal hint detection (stopword/hint overlap) and persistent weak retrieval performance on blind/holdout queries mean the system is not yet ready to test MEC hypotheses. A minor targeted fix cycle should resolve the remaining issues.

---

## 2. CLAIMS vs REPRODUCTION

| Claim (implementer) | Reproduced? | Notes |
|---------------------|-------------|-------|
| 107 tests pass | YES | All 107 reproduce identically (0.158s) |
| Original eval Hit@1=0.667 | YES | Exact match |
| Original eval Hit@3=0.867 | YES | Exact match |
| Original eval MRR=0.756 | YES | Exact match |
| Blind eval Hit@1=0.250 | YES | Exact match |
| Blind eval Hit@3=0.500 | YES | Exact match |
| Blind eval MRR=0.367 | YES | Exact match |
| Conflict detection fixed | YES | SUPERSEDES, OBSOLETE, version conflicts detected |
| TF-IDF replaces MD5 hash | YES | Real vector space, deterministic, local |
| Stopword filtering active | YES | 120+ PT+EN stopwords filter content tokens |
| No hardcodes for known queries | YES | Code is query-agnostic; eval from JSON only |
| init.py vs __init__.py divergence | NONE FOUND | All packages use correct `__init__.py` naming |
| 30 negative/edge tests | YES | 37 added, covering empty DB, invalid input, circular rels, etc. |
| No merge, tag, or release | YES | PR #6 remains draft |

---

## 3. NEW CRITICAL FINDING: Temporal Hint Bug

### 3.1 Root cause

The shared stopword list (`normalize.py`) and temporal hint words (`extract_clues()`) have overlapping entries:

| Word | In STOPWORDS? | Used as hint? | Consequence |
|------|--------------|---------------|-------------|
| `antes` | YES | `wants_historical` | Hint NEVER fires |
| `era` | YES | `wants_historical` | Hint NEVER fires |
| `agora` | YES | `wants_current` | Hint NEVER fires |
| `fazer` | YES | `wants_next_action` | Hint NEVER fires |

### 3.2 Impact

The `extract_clues()` function computes `clues.terms` via `tokenize()` which removes stopwords BEFORE the temporal hint check:

```python
clues.terms = tokenize(query)  # stopwords removed here
...
for token in clues.terms:      # checked here — but 'antes' already gone
    if token in historical_words:
        clues.wants_historical = True
```

Query "como era o calendario antes da mudanca":
- Terms after stopword removal: `['calendario', 'mudanca']`
- `wants_historical` = False (should be True)
- Historical items don't get the +0.25 score boost

### 3.3 Severity

**HIGH** — The temporal hint system, touted as an R1 innovation, is silently non-functional for its most important trigger words. Queries asking about historical/obsolete state don't receive the intended score adjustments.

### 3.4 Fix complexity

**LOW** — Move the temporal hint check to operate on raw tokens (before stopword removal) or use a separate pass that doesn't filter stopwords. One-line change in `extract_clues()`.

---

## 4. HOLD OUT TEST RESULTS (NEW, IMPLEMENTER-UNSEEN)

10 queries created by the reauditor, never exposed to the implementer:

| Metric | Value |
|--------|-------|
| Hit@1 | 0.500 |
| Hit@3 | 0.700 |
| MRR | 0.573 |
| Precision@1 | 0.500 |
| Conflict detection rate | 3.000 |
| Fake source rate | 0.0000 |

### Per-query breakdown:

| Query | Hit@1 | Hit@3 | Notes |
|-------|-------|-------|-------|
| hold-001 (domain search) | TRUE | TRUE | Strong lexical match |
| hold-002 (vague temporal) | FALSE | TRUE | Temporal hint bug impacts this |
| hold-003 (entity-driven) | TRUE | TRUE | Entity names match content |
| hold-004 (conflict-aware) | TRUE | TRUE | 3 conflicts detected correctly |
| hold-005 (cross-domain) | TRUE | TRUE | Shared vocabulary helps |
| hold-006 (obsolete nav) | FALSE | FALSE | Can't find the version pair |
| hold-007 (missing tool) | N/A | N/A | Correctly returns empty |
| hold-008 (inference sep) | N/A | N/A | Correctly returns empty |
| hold-009 (single word) | TRUE | TRUE | 3 conflicts detected |
| hold-010 (checkpoint) | FALSE | TRUE | Checkpoint at rank 3, not 1 |

**Analysis**: Hit@1=0.500 is exactly at the relaxed 0.50 threshold. The 5 failures are in: vague temporal queries, obsolete navigation, and checkpoint resumption — all areas where the temporal hint bug or vocabulary mismatch manifests.

---

## 5. COMPARATIVE METRICS SUMMARY

| Dataset | Version | Queries | Hit@1 | Hit@3 | MRR |
|---------|---------|---------|-------|-------|-----|
| Original eval | 1.0 | 15 | 0.667 | 0.867 | 0.756 |
| Blind (auditor) | 1.0 | 8 | 0.250 | 0.500 | 0.367 |
| Holdout (reauditor) | 1.0 | 10 | 0.500 | 0.700 | 0.573 |

The 0.417 gap between original eval (0.667) and holdout (0.250→0.500) confirms the original eval dataset contains lexical overlap bias. The rework reduced this gap from 0.733→0.000 (original baseline) to 0.667→0.250-0.500 (rework R1), which is improvement but still significant.

---

## 6. COMPONENT AUDIT

### 6.1 Scoring lexical (R1: stopword-filtered Jaccard)

**VALID, IMPROVED.** Stopword filtering correctly removes ~120 PT+EN function words. The Jaccard coefficient now operates on content-bearing tokens only. Verified: stopword-only queries return no lexical matches.

### 6.2 Scoring semântico (R1: TF-IDF)

**VALID, BUT WEAK.** The TF-IDF adapter is a real vector-space model, deterministic and local. However:
- Vocabulary built from only 30 memories = 13 terms in test setup
- Cosine similarity between unrelated documents is 0.0 (no shared vocabulary)
- Cross-domain analogies get zero semantic signal
- Ablation shows no_semantic reduces Hit@3 from 0.867 to 0.800 on original eval (modest impact), and 0.500 to 0.600 on blind (counterintuitive improvement in Hit@3)

The TF-IDF adapter is honest and deterministic — a genuine improvement over MD5 hash — but the vocabulary is too small to provide meaningful semantic similarity.

### 6.3 Conflict detection (R1: extended)

**VALID, FIXED.** Now covers:
- CONTRADICTED_BY relations (was already covered)
- SUPERSEDES relations (NEW, confirmed working)
- OBSOLETE/SUPERSEDED state (NEW)
- Version conflicts (NEW)
- `superseded_by` chain reporting (NEW)

Verified: hold-004 and hold-009 detected 3 conflicts each. The original auditor's complaint about "only checks CONTRADICTED_BY" is resolved.

### 6.4 Temporal hints (R1: new feature)

**BROKEN.** The overlap between stopwords and hint trigger words silently disables the most important temporal hints. This is a design flaw, not a data limitation. See Section 3.

### 6.5 Entity scoring

**INACTIVE (weight=0).** Entity extraction code exists but entities are sparsely populated in the dataset. The implementer correctly disabled this component (weight=0) rather than generating fake scores. Honest engineering choice.

### 6.6 Temporal validity scoring

**INACTIVE (weight=0).** `valid_from`/`valid_to` are null for all dataset items. Correctly disabled. Honest.

### 6.7 Stopword normalization

**VALID.** The unified `normalize.py` with `tokenize()`, `token_set()`, and `STOPWORDS` provides a single source of truth. Both `extract_clues()` and `LexicalRetriever` use the same functions. No duplication.

### 6.8 State scoring

**WEAK.** Weight reduced from 0.4 to 0.2 per rework. The 0.2 weight still gives a small bonus to VERIFIED items. Most items are VERIFIED, making this nearly constant. The negative penalty for OBSOLETE/SUPERSEDED helps when those items are in the candidate pool.

### 6.9 Graph/relation scoring

**VALID, MODEST IMPACT.** Removing graph drops blind Hit@1 from 0.250 to 0.125 (significant) but has no effect on original eval or holdout. The graph adds value when lexical signal is weak, but benefits only a few queries.

### 6.10 Test quality

**IMPROVED.** The 37 new tests cover:
- 6 empty database tests (previously missing)
- 7 invalid input tests (previously missing)
- 2 malformed JSON tests (previously missing)
- 2 circular relation tests (previously missing)
- 2 supersedes chain tests (previously missing)
- 8 field integrity tests for all memory types (previously weak)
- 2 project scope isolation tests (new)
- 3 quality assessment tests (new)
- 2 conflict detection tests (new)
- 1 stopword filtering test (new)
- 1 stopword-only query test (new)

Remaining weaknesses:
- Some tests still use tautological asserts (`self.assertGreater(len(result.candidate_scores), 0)`)
- Test fixtures share terms with query text (lexical overlap in test setup)
- No statistical significance testing for small datasets
- Ranking correctness is tested by structure, not by specific expected scores

---

## 7. ABLATION ANALYSIS

### Original eval (15 queries)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.667 | 0.867 | 0.756 |
| no_semantic | 0.667 | 0.800 | 0.739 |
| no_graph | 0.667 | 0.867 | 0.756 |

The semantic component helps Hit@3 (3→2 correct at rank 3) but not Hit@1. Graph has no measurable effect on the original eval — the 15 queries are lexical enough that graph relationships add nothing.

### Blind queries (8 queries)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.250 | 0.500 | 0.367 |
| no_semantic | 0.125 | 0.625 | 0.317 |
| no_graph | 0.125 | 0.500 | 0.295 |

Semantic and graph both matter for blind queries — removing either drops Hit@1 by half. This confirms both components provide signal when lexical overlap is weak.

Note: Hit@3 increases when semantic is removed (0.500→0.625) — this is a counterintuitive result suggesting the TF-IDF component sometimes shuffles the correct result out of position 3 while keeping it in the top 5.

### Holdout queries (10 queries)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.500 | 0.700 | 0.573 |
| no_semantic | 0.500 | 0.600 | 0.581 |
| no_graph | 0.500 | 0.700 | 0.567 |

Same pattern: semantic helps Hit@3, graph helps MRR slightly.

---

## 8. SEVERITY SUMMARY

| Severity | Count | Items |
|----------|-------|-------|
| HIGH | 1 | Temporal hint triggers silently disabled by stopword overlap |
| MEDIUM | 2 | Blind Hit@1=0.250 below 0.50 threshold, TF-IDF vocabulary too small (13 terms) |
| LOW | 3 | Python 3.11 vs 3.12, no Ruff/Mypy, original eval still below 0.80 target |
| INFO | 2 | Entity/temporal components correctly disabled (no data), state weight nearly constant |

---

## 9. WHAT'S FIXED (from original audit's 8 items)

| # | Original Finding | Status |
|---|-----------------|--------|
| 1 | Fix lexical scoring (stopwords) | FIXED — unified stopword filtering in normalize.py |
| 2 | Replace MD5 semantic adapter | FIXED — replaced with real TF-IDF |
| 3 | Fix conflict detection | FIXED — covers SUPERSEDES, OBSOLETE, version conflicts |
| 4 | Add blind test suite | PARTIAL — existing blind queries evaluated, but no pipeline integration |
| 5 | Recalibrate weights | FIXED — grid search documented, weights adjusted |
| 6 | Add negative tests | FIXED — 37 new negative/edge tests |
| 7 | Add behavioral tests | PARTIAL — field integrity tests added, but ranking correctness not behavioral |
| 8 | Separate stopword concerns | FIXED — single normalize.py used by both clue extraction and lexical scoring |

---

## 10. CONDITIONS FOR APPROVAL

1. **Fix temporal hint/stopword overlap**: Move hint word detection before stopword filtering, or add those 4 words to a separate non-stopword hint detection pass. This is a one-line fix.
2. **Enrich semantic vocabulary**: Either expand the dataset to provide more TF-IDF vocabulary (recommended minimum: 50+ unique content terms), or add a real embedding adapter (sentence-transformers) as an optional dependency.
3. **Blind test Hit@1 ≥ 0.50 on the KNOWN blind set**: Currently 0.250. The temporal hint fix alone may not reach 0.50; vocabulary enrichment is likely needed.
4. **Holdout Hit@1 ≥ 0.60 on 10+ unseen queries**: Currently 0.500. Should be achievable with temporal hint fix.
5. **No regression**: All 107 tests must still pass; original eval metrics must not degrade below 0.60 Hit@1.

---

## 11. EVIDENCE PRESERVED

- `audit/RAW_RESULTS/test_reproduction.txt` — full test run output (107/107 passing)
- `audit/RAW_RESULTS/original_eval_reproduced.txt` — original eval ablation output
- `audit/RAW_RESULTS/blind_eval_reproduced.txt` — blind eval ablation output
- `audit/RAW_RESULTS/holdout_report.md` — holdout eval detailed report
- `audit/verify_audit.py` — audit verification script (reproducible)
- `audit/holdout_queries.json` — 10 new queries (IMPLEMENTER MUST NOT SEE)

---

## 12. LIMITATIONS OF THIS AUDIT

1. The holdout queries were crafted by the same reauditor — they may inadvertently share vocabulary patterns with the dataset.
2. The dataset is synthetic (30 memories, 25 relations) — all metrics are within this closed world.
3. No Ruff/Mypy linting could be performed (tools not available).
4. Python 3.11 was used instead of the specified 3.12.
5. The semantic component cannot be tested with real embeddings (sentence-transformers not installed).
6. Statistical significance of metric deltas cannot be assessed on 8-15 query datasets.

---

## 13. NEXT STEPS

1. Implementer reads this report and the blocked temporal hint finding.
2. Implementer creates a new branch `rework/mec-lab-baseline-r2` from `rework/mec-lab-baseline-r1`.
3. Implementer fixes the temporal hint bug and re-runs all evaluations.
4. A new reauditor (different from this one) evaluates the r2 branch with fresh holdout queries.
5. DO NOT merge, tag, or release before independent reaudit approval.
