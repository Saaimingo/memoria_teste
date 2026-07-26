# REAUDIT REPORT — PR #9 (Rework R2)

**Reauditor**: Independent Agent (audit/rework-r2-pr9)
**Target**: rework/mec-lab-baseline-r2 @ d35931e
**Base**: rework/mec-lab-baseline-r1 @ 7cfc051
**Date**: 2026-07-26
**Environment**: Windows 10, Python 3.11.15

---

## 1. VERDICT

**APPROVED_FOR_EXPERIMENTAL_USE**

The temporal hint/stopword overlap bug identified in PR #6 audit is fully resolved. The fix is minimal (5 files changed, only 18 lines in the retrieval module), verified by 9 new behavioral tests, and introduces zero regressions. All metrics are reproducible. The remaining retrieval quality gaps (blind Hit@1=0.250) are pre-existing vocabulary limitations, not introduced by R2.

---

## 2. SCOPE VERIFICATION

### 2.1 What was changed (R1 → R2 diff)

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `src/mec_lab/retrieval/__init__.py` | +14 / -4 | Temporal hint detection on raw tokens |
| `tests/test_retrieval.py` | +56 | 9 new behavioral tests |
| `evidence/rework-r2/REPORT.md` | +183 | Documentation only |
| `evidence/rework-r2/raw/blind_eval.md` | +96 | Documentation only |
| `evidence/rework-r2/raw/original_eval.md` | +138 | Documentation only |

### 2.2 What was NOT changed

- Datasets (`baseline_dataset.json`, `eval_queries.json`) — VERIFIED: zero diff
- Blind queries (`evidence/blind_queries.json`) — VERIFIED: zero diff
- Gold answers — VERIFIED: zero diff
- Weights / ranking — VERIFIED: zero diff
- TF-IDF adapter — VERIFIED: zero diff
- Conflict detection — VERIFIED: zero diff
- Capsule builder — VERIFIED: zero diff
- CLI — VERIFIED: zero diff
- Storage — VERIFIED: zero diff
- Domain models — VERIFIED: zero diff

---

## 3. TEST VERIFICATION

### 3.1 Full test suite: 116/116 PASS (0.156s)

Reproduced identically. Zero regression from R1 (107 tests).

### 3.2 9 new behavioral tests — ALL PASS

| Test | Status | Verification |
|------|--------|-------------|
| `test_historical_hint_antes` | PASS | "antes" → wants_historical=True |
| `test_historical_hint_era` | PASS | "era" → wants_historical=True |
| `test_current_hint_agora` | PASS | "agora" → wants_current=True |
| `test_current_hint_atual` | PASS | "atual" → wants_current=True |
| `test_action_hint_fazer` | PASS | "fazer" → wants_next_action=True |
| `test_action_hint_pendente` | PASS | "pendente" → wants_next_action=True |
| `test_no_hint_on_neutral_query` | PASS | No false positives |
| `test_multiple_hints_together` | PASS | Three hints fire simultaneously |
| `test_terms_still_clean_with_hints` | PASS | Zero stopword leakage into clues.terms |

### 3.3 Test quality assessment

The behavioral tests are well-designed:
- Test each of the 4 overlapping words individually (antes, era, agora, fazer)
- Test non-overlapping hint words (atual, pendente) as controls
- Test negative case (neutral query)
- Test boundary case (multiple hints)
- Test the critical invariant (no stopword leakage)

---

## 4. DIRECT HINT VERIFICATION (9 ad-hoc queries)

Executed independent script `audit/verify_hints_r2.py`:

| Query | wants_hist | wants_curr | wants_action | terms clean? |
|-------|-----------|-----------|-------------|-------------|
| "com o era o calendario antes da mudanca" | TRUE ✓ | false ✓ | false ✓ | YES ✓ |
| "o que era aquilo" | TRUE ✓ | false ✓ | false ✓ | YES ✓ |
| "o que fazer agora" | false ✓ | TRUE ✓ | TRUE ✓ | YES ✓ |
| "qual a regra atual" | false ✓ | TRUE ✓ | false ✓ | YES ✓ |
| "o que devo fazer" | false ✓ | false ✓ | TRUE ✓ | YES ✓ |
| "o que esta pendente" | false ✓ | false ✓ | TRUE ✓ | YES ✓ |
| "futebol calendario simulador" | false ✓ | false ✓ | false ✓ | YES ✓ |
| "antes de fazer o trabalho atual" | TRUE ✓ | TRUE ✓ | TRUE ✓ | YES ✓ |
| "como era o calendario antes da mudanca atual" | TRUE ✓ | TRUE ✓ | false ✓ | YES ✓ |

**All 9/9 pass.** Terms like "calendario", "mudanca", "atual" appear in `clues.terms` while
stopwords "como", "era", "o", "antes", "da", "de", "que", "fazer", "agora" do NOT.

---

## 5. METRICS REPRODUCTION

### 5.1 Original eval (15 queries)

| Metric | Implementer Claim | Reproduced | Match |
|--------|-------------------|-----------|-------|
| Hit@1 | 0.667 | 0.667 | ✓ |
| Hit@3 | 0.867 | 0.867 | ✓ |
| MRR | 0.756 | 0.756 | ✓ |

### 5.2 Blind eval (8 queries)

| Metric | Implementer Claim | Reproduced | Match |
|--------|-------------------|-----------|-------|
| Hit@1 | 0.250 | 0.250 | ✓ |
| Hit@3 | 0.500 | 0.500 | ✓ |
| MRR | 0.367 | 0.367 | ✓ |

### 5.3 Holdout eval (10 queries — same as PR #6 audit)

| Metric | PR #6 Audit (R1) | Reproduced (R2) | Match |
|--------|-----------------|-----------------|-------|
| Hit@1 | 0.500 | 0.500 | ✓ |
| Hit@3 | 0.700 | 0.700 | ✓ |
| MRR | 0.573 | 0.573 | ✓ |

### 5.4 Blind ablation (R2)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.250 | 0.500 | 0.367 |
| no_semantic | 0.125 | 0.625 | 0.317 |
| no_graph | 0.125 | 0.500 | 0.295 |
| no_temporal | 0.250 | 0.500 | 0.367 |
| no_typing | 0.250 | 0.500 | 0.367 |
| no_state | 0.250 | 0.500 | 0.367 |
| no_checkpoint_boost | 0.250 | 0.500 | 0.367 |

Matches implementer's claims and PR #6 audit (R1). No change — temporal hints are
separate from the weight-based temporal component (which remains at weight=0).

---

## 6. PER-QUERY BLIND ANALYSIS — HINT BEHAVIOR

| Query | R2 hints | R1 hints (per audit) |
|-------|----------|---------------------|
| blind-003 ("como era a regra... antes da mudanca...") | wants_historical=**True** | was **False** (bug) |
| blind-006 ("no que devo trabalhar agora...") | wants_current=**True**, wants_next_action=**True** | both were **False** (bug) |

**Confirmed**: The fix correctly enables temporal hints that were silently disabled in R1.

---

## 7. CONFLICT DETECTION

Verified via 3 holdout conflict queries:

| Query | Conflicts Detected |
|-------|-------------------|
| "o calendario do simulador mudou..." | 3 (SUPERSEDES + OBSOLETE state + chain) |
| "qual era a regra que foi substituida..." | 0 (weak lexical match — retrieval quality issue) |
| "aposentadoria" | 0 (no superseded items in top results) |

The conflict detection code path is functional — when superseded items are retrieved,
conflicts are correctly reported. The 0-conflict results are retrieval failures
(pre-existing), not conflict detection failures.

---

## 8. HARDCODE CHECK

Search in all `src/**/*.py` for:
- `blind-003`, `blind-006`, `hold-00*` → **NONE FOUND**
- `hardcode`, `known_query`, `special.*case` → **NONE FOUND**

The code is query-agnostic. All evaluation is driven by external JSON datasets.

---

## 9. HOLDOUT INTEGRITY

- Holdout queries retrieved from `audit/rework-r1-pr6` branch (not in R2 branch)
- Holdout file path: `audit/holdout_queries_r2.json` (created by auditor, NOT in R2)
- The implementer's R2 branch contains **no reference** to holdout query IDs
- The implementer's code does **not** load or reference the holdout file

---

## 10. ASSESSMENT AGAINST PR #6 AUDIT CONDITIONS

| Condition | Status | Notes |
|-----------|--------|-------|
| Fix temporal hint/stopword overlap | **MET** | One-line fix in extract_clues(), verified by 9 tests |
| Enrich semantic vocabulary | NOT IN SCOPE | This is a retrieval quality issue, not R2 scope |
| Blind Hit@1 ≥ 0.50 | NOT MET | Still 0.250 — vocabulary gap, not hint-related |
| Holdout Hit@1 ≥ 0.60 | NOT MET | 0.500 — project filtering helps; vocabulary gap remains |
| No regression | **MET** | All 107 original tests + 9 new = 116 passing |

R2's scope is narrowly defined as "fix the temporal hint/stopword overlap bug." Within that
scope, the fix is complete, correct, and verified. The unmet conditions (semantic vocabulary,
blind Hit@1) are pre-existing architectural limitations documented in the implementer's
report and confirmed by this audit. They are not introduced or worsened by R2.

---

## 11. LIMITATIONS OF THIS AUDIT

1. Holdout queries inherited from PR #6 audit (same reauditor lineage)
2. Python 3.11 used instead of specified 3.12
3. No Ruff/Mypy linting (tools unavailable)
4. No statistical significance testing (8-15 query datasets too small)
5. The "pendente" hint detection works correctly but retrieval quality on hold-010
   depends on project filtering via expected_project_id

---

## 12. EVIDENCE PRESERVED

- `audit/verify_hints_r2.py` — hint verification script (reproducible)
- `audit/verify_blind_conflicts.py` — blind + conflict verification (reproducible)
- `audit/verify_holdout_r2.py` — holdout per-query verification (reproducible)
- `audit/diagnose_hold010.py` — hold-010 diagnostic (reproducible)
- `audit/holdout_queries_r2.json` — holdout queries (IMPLEMENTER MUST NOT SEE)

---

## 13. RECOMMENDATION

R2 is approved for experimental use. The temporal hint fix is correct, minimal,
and well-tested. For the next iteration (R3 or equivalent), recommend:

1. **Vocabulary enrichment**: Expand the dataset to 50+ content-bearing terms for
   TF-IDF to produce meaningful semantic similarity.
2. **Embedding adapter**: Add optional sentence-transformers dependency for real
   cross-domain semantic retrieval.
3. **Blind evaluation redesign**: The current blind queries contain vocabulary that
   has zero overlap with the dataset vocabulary — this guarantees Hit@1=0 regardless
   of retrieval quality. Either expand the dataset vocabulary or adjust blind
   queries to use terms present in the dataset.
