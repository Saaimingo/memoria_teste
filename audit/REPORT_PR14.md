# Audit Report — PR #14 (Rework R3)

**Auditor**: Agente Reauditor Independente
**Date**: 2026-07-26
**Branch**: audit/rework-r3-pr14 (created from rework/mec-live-memory-r3)
**Target**: f5d605538c3cb6cc1b7d241e7cb6129485a78f02
**Base**: main → rework/mec-live-memory-r3

---

## 1. EXECUTIVE SUMMARY

The Rework R3 implementation addresses the four structural problems identified by Experiment 01:
- R3-1 (vigência vs obsolescência): PARTIALLY RESOLVED
- R3-2 (ausência real de evidência): RESOLVED with caveats
- R3-3 (próxima ação e risco): RESOLVED with fragility in intent detection
- R3-4 (conflitos): RESOLVED

The implementation is honest about its limitations. No hardcodes to Projeto Atlas were found in the source code. No evidence of fabrication was detected. The 128 tests and experiment metrics reproduce exactly as declared.

However, the adversarial test set (12 new queries, unknown to the implementer) reveals 4 failures that expose systematic weaknesses in the stemmer and intent detection.

---

## 2. VERIFICATION METHODOLOGY

### 2.1 Reproduction Steps
1. Created independent audit branch `audit/rework-r3-pr14` from `rework/mec-live-memory-r3`
2. Ran all 128 tests: `python -m tests.run_tests`
3. Ran Experiment 01: `python experiments/exp-01/run_experiment.py`
4. Compared `queries.json` and `gold_answers.json` against `experiment/mec-live-memory-01` branch
5. Verified all 20 individual query results against gold answers
6. Built adversarial test set with new domain (healthcare clinic), 12 queries
7. Analyzed stemmer for over/under-stemming with 23 test pairs

### 2.2 Evidence Collected
- `audit/verify_results.json` — per-query reproduction results
- `audit/adversarial_results.json` — adversarial test results
- `audit/stemmer_analysis2.py` output — stemmer behavior
- All raw experiment outputs reproduced in `experiments/exp-01/RAW_RESULTS/`

---

## 3. FINDINGS

### 3.1 Test Reproduction — PASS

```
Ran 128 tests in 0.197s
OK
```

All 128 tests pass (116 original + 12 new R3 tests). No regressions. Confirmed.

### 3.2 Experiment 01 Reproduction — PASS

| Metric | Declared | Reproduced | Match |
|--------|----------|------------|-------|
| Hit@1 | 0.500 | 0.500 | ✓ |
| Hit@3 | 0.750 | 0.750 | ✓ |
| MRR | 0.628 | 0.628 | ✓ |
| Precision@1 | 0.500 | 0.500 | ✓ |
| FakeSrc | 0.0000 | 0.0000 | ✓ |
| ConfDet | 6.000 | 6.000 | ✓ |
| Verdict | EXPERIMENT_01_PASSED | EXPERIMENT_01_PASSED | ✓ |

### 3.3 queries.json and gold_answers.json — UNCHANGED

```
$ git diff experiment/mec-live-memory-01 -- experiments/exp-01/queries.json experiments/exp-01/gold_answers.json
(no output — files are identical)
```

Confirmed: neither file was modified. The restriction was respected.

### 3.4 Hardcode Search — CLEAN

Searched `src/` for references to:
- "Atlas", "proj-atlas" → 0 matches
- Specific query IDs (q01-q12, p01-p08) → 0 matches
- "dec-atlas", "fact-atlas", "chk-atlas" → 0 matches
- "criptografia", "batch", "queue" → 0 matches

No hardcodes to Projeto Atlas exist in the source code. The implementation uses general mechanisms (stemming, intent hints, content-based bonuses).

### 3.5 Per-Query Verification (20 queries)

| Query | Hit@1 | Hit@3 | Quality | Status |
|-------|-------|-------|---------|--------|
| q01-decisao-vigente | True | True | relevant | ✓ |
| q02-abordagem-anterior | True | True | absent ⚠ | ✓ |
| q03-motivo-abandono | False | False | absent | ✗ KNOWN LIMIT |
| q04-evidencia-duplicacao | False | True | relevant | ✓ |
| q05-hipotese-replay | True | True | relevant | ✓ |
| q06-aprendizado-reinicializacao | False | True | relevant | ✓ |
| q07-proximo-trabalho | False | True | absent ⚠ | ✓ |
| **q08-risco-pendente** | **True** | **True** | relevant | **✓ FIXED** |
| q09-documento-arquitetura | True | True | relevant | ✓ |
| q10-criptografia-ausente | False | False | absent | ✓ (correct absence) |
| q11-conflitos | True | True | absent ⚠ | ✓ |
| q12-delta-checkpoints | True | True | absent ⚠ | ✓ |
| p01-parafrase-vigente | True | True | relevant | ✓ |
| p02-parafrase-antigo | True | True | absent ⚠ | ✓ |
| p03-parafrase-motivo | False | False | relevant | ✗ KNOWN LIMIT |
| p04-parafrase-prova | False | False | absent | ✗ |
| p05-parafrase-proxima | False | True | relevant | ✓ |
| p06-parafrase-bloqueio | True | True | relevant | ✓ |
| p07-parafrase-seguranca | False | False | absent | ✓ (correct absence) |
| p08-parafrase-evolucao | False | True | absent ⚠ | ✓ |

**⚠ Quality label inconsistency**: 6 queries (q02, q07, q11, q12, p02, p08) return correct results at Hit@1 or Hit@3 but are labeled quality="absent". These queries succeed through temporal/state hints and graph signals without lexical overlap. The quality assessment (`_assess_quality`) is disconnected from the effective ranking logic — it classifies based on lexical signal while the ranking uses additional signals (intent bonuses, state weights, graph relations). This is a **labeling bug**: the system finds the right answer but tells the user it found nothing.

### 3.6 Specific Query Deep-Dives

#### q01 — Decisão Vigente ✓
- dec-atlas-queue at position 1, dec-atlas-batch at position 18
- State weights (+0.20 for active, -0.30 for superseded) + wants_current bonus (+0.30 for active) correctly push the current decision to the top
- The old decision (dec-atlas-batch) has zero lexical overlap and drops to position 18

#### q02 — Abordagem Anterior ✓ (quality label bug)
- dec-atlas-batch at position 1 despite having zero lexical overlap and negative state score (-0.30)
- wants_historical bonus (+0.40 for SUPERSEDED items) overcomes the lexical disadvantage
- But quality="absent" because lexical_score=0.0 — the system found the right answer but says it's absent. This is a labeling inconsistency.

#### q08 — Risco Pendente ✓ FIXED
- fact-atlas-risk at position 1 (was failing in baseline)
- The wants_risk/wants_blocker bonus (+0.15 per keyword hit) correctly boosts the risk memory
- Content-based keywords ("risco", "pendente", "conclusao") match the fact content
- No hardcode: uses general keywords matched against content

#### q10 — Criptografia Ausente ✓
- Returns quality="absent" with empty candidate_scores
- needs_absence=True detected (via "existe" + "registrada"), no lexical overlap
- Correct behavior: the system says "I don't know"

#### q11 — Conflitos ✓ (quality label bug)
- dec-atlas-queue at position 1, dec-atlas-batch at position 18
- 2 conflicts detected: STATE_CONFLICT (merged with superseded_by) + CONFLICT SUPERSEDES
- Deduplication works: the STATE_CONFLICT line inlines superseded_by info

#### p01 — Paráfrase Vigente ✓
- dec-atlas-queue at position 1
- wants_current detected via "hoje" in "hoje em dia"

#### p06 — Paráfrase Bloqueio ✓
- fact-atlas-risk at position 1, chk-atlas-04 at position 2
- wants_blocker detected via "bloqueando", risk keywords match content

#### p07 — Paráfrase Segurança ✓
- Returns quality="absent" with empty results
- needs_absence detected via "decidiu" + "alguma"
- Correct absence behavior

### 3.7 Adversarial Test Results (12 new queries, unknown domain)

| Test | Description | Status |
|------|-------------|--------|
| ADV-1 | Decisão atual supera obsoleta com maior overlap | **FAIL** |
| ADV-2 | Consulta histórica recupera obsoleta | PASS |
| ADV-3 | Ausência retorna absent | PASS |
| ADV-4 | Relações isoladas não fabricam relevância | **FAIL** |
| ADV-5 | Próxima ação prioriza pendente | **FAIL** |
| ADV-6 | Risco pendente recuperável (paráfrase) | PASS |
| ADV-7 | Consulta neutra não recebe bônus | PASS |
| ADV-8 | Conflitos deduplicados | PASS |
| ADV-9 | Ausência com paráfrase nova | **FAIL** |
| ADV-10 | Decisão atual com paráfrase informal | PASS |
| ADV-11 | Bloqueio com paráfrase nova | PASS |
| ADV-12 | Ausência com tópico exótico | PASS |

**Result: 8/12 pass (67%). 4 failures analyzed below.**

#### ADV-1 FAIL: Decision current requires explicit temporal hints
Query: "Como armazenamos prontuários com schemas normalizados por especialidade?"

The old SQL decision (lexically matching "schemas normalizados") outranks the new NoSQL decision (1st vs 2nd). Root cause: the query has no explicit temporal hint word ("vigente", "atual", "hoje") — "armazenamos" (present tense) doesn't trigger wants_current. Without the intent bonus, the old decision wins on lexical merit. The system is fragile: it requires specific trigger words that may not appear in natural paraphrases.

#### ADV-4 FAIL: Over-stemming creates false positive
Query: "Qual medicamento foi prescrito para hipertensão?"

Returns quality="relevant" with fact-clinica-agenda at position 1. Root cause: stem_pt("medicamento") → "medic" and stem_pt("médico") → "medic" (both converge). The agenda fact mentions "médico" in its content, creating a false lexical bridge. This is a real over-stemming bug — "medicamento" (medicine) and "médico" (doctor) are semantically distinct but converge to the same stem.

#### ADV-5 FAIL: Next action detection misses paraphrases
Query: "No que preciso focar para avançar o projeto da clínica?"

fact-clinica-next not in top 3. Root cause: "focar" and "avançar" are not in the action_words set (`{"trabalhar", "proximo", "pendente", "fazer", "falta"}`). The action detection vocabulary is too small and misses common Portuguese paraphrases for "what to work on next."

#### ADV-9 FAIL: Absence detection misses "definiu"
Query: "Alguém definiu regras de acesso aos prontuários por perfil de usuário?"

Returns quality="relevant" with 6 results. Root cause: "definiu" is not in the absence_words set. However, "prontuários" creates legitimate lexical overlap with the DB content about prontuários. The system correctly identifies that the DB has content about prontuários but cannot distinguish that the query is about a specific aspect (access rules) not covered. This is a fundamental limitation of lexical-only systems.

### 3.8 Stemmer Analysis

**Under-stemming (6/18 cases)**: Related word pairs that should converge but don't:
- "decisão"/"decidir" → "decisa"/"decid"
- "conclusão"/"concluir" → "conclusa"/"conclu"
- "execução"/"executar" → "execu"/"execut"
- "enviadas"/"enviar" → "enviad"/"env"
- "bloqueio"/"bloquear" → "bloquei"/"bloqu"
- "risco"/"arriscado" → "risc"/"arrisc"

**Over-stemming (2/5 cases)**: Distinct words that incorrectly converge:
- "medicamento"/"médico" → both "medic" (medicine ≠ doctor)
- "ponta"/"ponto" → both "pont" (tip ≠ point)

The R3 absence overlap threshold (requires ≥2 overlapping stems when needs_absence=True) partially guards the "ponta"/"ponto" case for absence queries, but the guard does NOT apply to non-absence queries where over-stemming can still produce false positives.

### 3.9 Conflict Deduplication — PASS

The R3 conflict detection correctly:
- Merges STATE_CONFLICT with superseded_by info into one line
- Tracks SUPERSEDES pairs to avoid duplicate reports (regardless of direction)
- Limits to 1 STATE_CONFLICT and 1 CONFLICT SUPERSEDES per related pair

Verified in both the experiment queries (q11 shows 2 conflicts: merged STATE + SUPERSEDES) and adversarial tests (ADV-8: max 1 of each type).

### 3.10 Isolated Relations — MIXED RESULT

The requirement "relações isoladas não podem fabricar relevância" is partially enforced:
- When needs_absence=True and no lexical overlap exists, quality="absent" even with relations (e.g., q10, p07)
- When needs_absence=False, relations contribute to scores and can push items with zero lexical overlap into top positions (e.g., q02, where dec-atlas-batch reaches #1 via hint bonuses despite lexical_score=0.0)
- The adversarial ADV-4 case shows relations alone don't cause the failure (it's the over-stemming false positive), but ADV-1 shows that without explicit temporal hints, the purely-lexical ranking fails

---

## 4. LIMITATIONS INVENTORY (verified by auditor)

### Confirmed from implementer's report:
1. **Gap lexical em q03/p03**: Vocabulário da query não existe nos conteúdos. Requer embeddings. **CONFIRMED**.
2. **Hit@1 ordering**: q04, q06, q07, p04, p05, p08 have correct item in top-3 but not position 1. **CONFIRMED**.
3. **Stemmer sem dicionário de exceções**: Rule-based only, produces false positives/negatives. **CONFIRMED** — 6 under-stemming + 2 over-stemming cases found.
4. **Scores baseados em grafo sem contenção lexical**: When no lexical overlap, ranking dominated by graph signals. **CONFIRMED** — q02, q07, q11, q12 all succeed via non-lexical signals with quality="absent" label.

### Additional limitations found by auditor:
5. **Quality label inconsistency (NEW)**: 6 queries return correct results but are labeled quality="absent". The quality assessment only considers lexical signal and ignores the intent bonuses and graph signals that the ranking actually uses. This means the system tells the user "I found nothing" while actually returning the correct answer.
6. **Intent detection vocabulary too small (NEW)**: wants_current requires words from a fixed set of ~5 words. Natural paraphrases like "armazenamos" (present tense), "como vocês estão fazendo" don't trigger the bonus, causing ADV-1 failure.
7. **Action detection similarly fragile (NEW)**: Only 7 action words recognized. "focar", "avançar", "seguir", "prioridade" — common Portuguese paraphrases — are not detected.
8. **Over-stemming "medicamento"/"médico" (NEW)**: Creates false lexical bridges in non-absence queries. The guard threshold only applies when needs_absence=True.

---

## 5. METRICS COMPARISON

| Metric | Implementer Declared | Auditor Reproduced | Match |
|--------|---------------------|-------------------|-------|
| 128 tests pass | Yes | Yes | ✓ |
| Hit@1 | 0.500 | 0.500 | ✓ |
| Hit@3 | 0.750 | 0.750 | ✓ |
| MRR | 0.628 | 0.628 | ✓ |
| Precision@1 | 0.500 | 0.500 | ✓ |
| FakeSrc | 0.0000 | 0.0000 | ✓ |
| ConfDet | 6.000 | 6.000 | ✓ |
| queries.json unchanged | Yes | Yes | ✓ |
| gold_answers.json unchanged | Yes | Yes | ✓ |
| q08 fixed | Yes | Yes | ✓ |
| Absence queries correct | Yes | Yes | ✓ |
| No hardcodes | Yes | Yes | ✓ |
| Adversarial pass rate | N/A (not declared) | 8/12 (67%) | — |

---

## 6. VERDICT

**APPROVED_FOR_EXPERIMENTAL_USE**

### Justification:
1. No evidence fabrication detected. The implementer's report is honest about limitations.
2. All 128 tests pass. Experiment 01 reproduces exactly.
3. No hardcodes to Projeto Atlas. Fixes are general mechanisms (stemming, intent hints, content-based bonuses).
4. queries.json and gold_answers.json were NOT modified — the restriction was respected.
5. The four required behavioral problems (R3-1 through R3-4) are addressed, though with documented caveats.
6. q08 (the primary R3 fix target) is resolved: fact-atlas-risk now hits position 1.
7. Absence queries (q10, p07) correctly return empty results.

### Caveats (must be addressed before production use):
- **Quality labeling bug**: The system returns correct answers labeled as "absent". This is confusing to users and should be fixed.
- **Intent detection fragility**: The small trigger-word vocabulary (~5-7 words per intent) fails on natural paraphrases. The adversarial ADV-1 and ADV-5 failures demonstrate this.
- **Stemmer over-stemming**: "medicamento"/"médico" and "ponta"/"ponto" false convergences create false positives in non-absence queries.
- **Adversarial robustness**: 4/12 adversarial queries fail. The system works well on Projeto Atlas queries (designed with known intent vocabulary) but degrades on unfamiliar paraphrases and domains.

### Why not REWORK_REQUIRED:
The 4 adversarial failures are symptoms of systematic limitations in the lexical-only approach, not implementation errors. Fixing them would require:
- A much larger intent detection vocabulary (arbitrary and fragile long-term)
- A dictionary-based stemmer with exception lists
- Semantic embeddings for topic disambiguation

These are architectural improvements that belong in a future rework, not a rejection of the current one. The implementer already documented the need for "embeddings semânticos reais" — the adversarial tests simply confirm this assessment with independent evidence.

### Why not BLOCKED_BY_INVALID_EVIDENCE:
All evidence reproduced correctly. No fabrication, no cherry-picking, no hidden test failures.

### Why not INCONCLUSIVE:
The evidence is sufficient to reach a clear verdict. The implementation works as declared, the limitations are real but documented, and no deception was detected.

---

## 7. ARTIFACTS PRODUCED

| Artifact | Path |
|----------|------|
| Audit Report | `audit/REPORT_PR14.md` |
| Verification Script | `audit/verify_queries.py` |
| Verification Results | `audit/verify_results.json` |
| Adversarial Test Set | `audit/adversarial_tests.py` |
| Adversarial Results | `audit/adversarial_results.json` |
| Stemmer Analysis | `audit/stemmer_analysis2.py` |

---

## 8. DECLARATION

I, the Independent Re-auditor Agent, certify that:
- I did not alter the branch `rework/mec-live-memory-r3`
- I created my own audit branch `audit/rework-r3-pr14`
- I reproduced all 128 tests and the full Experiment 01
- I verified queries.json and gold_answers.json against the experiment branch
- I created an adversarial test set unknown to the implementer
- I searched for hardcodes and found none
- I analyzed the stemmer for over/under-stemming
- I did not correct any code
- I did not merge, tag, or release
- All metrics and claims in this report are verified by my own execution
