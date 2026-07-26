# REWORK R2 — Relatório de Implementação

**Branch**: rework/mec-lab-baseline-r2
**Base**: rework/mec-lab-baseline-r1 @ 7cfc051
**Date**: 2026-07-26
**Python**: 3.11.15

---

## 1. Item Corrigido

### 1.1 Overlap stopwords ↔ temporal hints (BUG da auditoria PR #6)

**Causa raiz**: As palavras "antes", "era", "agora", "fazer" estavam simultaneamente
na lista de stopwords e nos conjuntos de palavras-gatilho para hints temporais.
Como a detecção de hints iterava sobre `clues.terms` (já filtrado de stopwords),
essas palavras nunca chegavam ao loop de detecção — os hints ficavam silenciosamente
desativados.

**Correção (R2)**: A detecção de hints agora usa `tokenize(query, remove_stopwords=False)`
para obter todos os tokens (incluindo stopwords). O loop de hints itera sobre esses
tokens brutos, enquanto `clues.terms` permanece limpo (stopwords removidas) para o
scoring lexical. Nenhuma stopword vaza para `clues.terms`.

**Arquivo modificado**: `src/mec_lab/retrieval/__init__.py` (função `extract_clues`)

**Verificação**: Os 9 novos testes comportamentais comprovam que:
- `antes` → `wants_historical=True`
- `era` → `wants_historical=True`
- `agora` → `wants_current=True`
- `fazer` → `wants_next_action=True`
- Múltiplos hints podem disparar simultaneamente
- Consultas neutras não disparam falsos positivos
- Stopwords não vazam para `clues.terms`

---

## 2. Testes

### 2.1 Testes preservados
107 testes originais (R1) mantidos e passando.

### 2.2 Novos testes comportamentais (R2)
9 novos testes em `test_retrieval.py` — classe `TestClueExtraction`:

| Teste | Verifica |
|-------|----------|
| `test_historical_hint_antes` | "antes" → wants_historical (era bug) |
| `test_historical_hint_era` | "era" → wants_historical (era bug) |
| `test_current_hint_agora` | "agora" → wants_current (era bug) |
| `test_current_hint_atual` | "atual" → wants_current |
| `test_action_hint_fazer` | "fazer" → wants_next_action (era bug) |
| `test_action_hint_pendente` | "pendente" → wants_next_action |
| `test_no_hint_on_neutral_query` | consulta neutra não dispara hints |
| `test_multiple_hints_together` | hints múltiplos simultâneos |
| `test_terms_still_clean_with_hints` | stopwords não vazam para terms |

**Total**: 107 + 9 = 116 testes, todos passando.

---

## 3. Métricas Comparativas R1 vs R2

### 3.1 Avaliação original (15 queries)

| Métrica | R1 | R2 | Delta |
|---------|-----|-----|-------|
| Hit@1 | 0.667 | 0.667 | 0 |
| Hit@3 | 0.867 | 0.867 | 0 |
| MRR | 0.756 | 0.756 | 0 |

**Nota**: Sem alteração — as consultas originais já atingem alto desempenho lexical.
O fix de hints beneficia consultas com linguagem natural histórica/temporal, que são
minoria no dataset original.

### 3.2 Avaliação cega (8 queries conhecidas do auditor)

| Métrica | R1 | R2 | Delta |
|---------|-----|-----|-------|
| Hit@1 | 0.250 | 0.250 | 0 |
| Hit@3 | 0.500 | 0.500 | 0 |
| MRR | 0.367 | 0.367 | 0 |

**Nota**: Sem alteração nos agregados. Porém, a nível de consulta individual, os
hints temporais agora disparam corretamente:

- `blind-003` ("como era a regra... antes da mudança..."): `wants_historical=True` (antes era `False`)
- `blind-006` ("no que devo trabalhar agora..."): `wants_current=True`, `wants_next_action=True` (antes ambos `False`)

O gap de Hit@1 permanece porque o problema raiz é a distância vocabular entre a
linguagem natural das consultas cegas e o vocabulário técnico do dataset — não
resolvível com hints lexicais apenas.

### 3.3 Ablation (blind, R2)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.250 | 0.500 | 0.367 |
| no_semantic | 0.125 | 0.625 | 0.317 |
| no_graph | 0.125 | 0.500 | 0.295 |
| no_temporal | 0.250 | 0.500 | 0.367 |
| no_typing | 0.250 | 0.500 | 0.367 |
| no_state | 0.250 | 0.500 | 0.367 |
| no_checkpoint_boost | 0.250 | 0.500 | 0.367 |

Idêntico ao R1. O componente `no_temporal` não mostra impacto porque o weight
temporal é 0.0 (componente desativado por falta de dados `valid_from`/`valid_to`).
Os temporal hints (wants_historical/wants_current) são bônus separados, não passam
pelo sistema de pesos.

---

## 4. Conflitos

Detecção de conflitos mantida integralmente:
- CONTRADICTED_BY: funcional
- SUPERSEDES: funcional
- OBSOLETE/SUPERSEDED state: funcional
- Version conflicts: funcional
- `superseded_by` chain reporting: funcional

Nenhuma regressão. Consultas que envolvem `fact-fb-005-v2 SUPERSEDES fact-fb-005-obsolete`
continuam reportando 3 conflitos.

---

## 5. O Que NÃO Foi Alterado

- Datasets originais (`baseline_dataset.json`, `eval_queries.json`)
- Gold answers
- Pesos do ranking
- TF-IDF adapter
- Conflict detection
- Capsule builder
- CLI
- Storage
- Domain models

---

## 6. Limitações Remanescentes

1. **Blind Hit@1 = 0.250**: Abaixo do threshold de 0.50. Causa raiz: vocabulário
   das consultas cegas não casa com o vocabulário do dataset. TF-IDF com 30 memórias
   produz vocabulário de ~50 termos — insuficiente para similaridade semântica
   cross-domain. Solução requer embeddings reais ou expansão de sinônimos.

2. **Vocabulário TF-IDF pequeno**: Com apenas 30 memórias, o espaço vetorial é
   esparso demais para capturar similaridades não-literais.

3. **Entity e Temporal components**: Permanecem com weight=0 por falta de dados.

4. **Ruff/Mypy**: Não executados (ferramentas indisponíveis).

---

## 7. Comandos de Reprodução

```bash
git clone https://github.com/Saaimingo/memoria_teste.git
cd memoria_teste
git checkout rework/mec-lab-baseline-r2
PYTHONPATH=src python -m tests.run_tests
PYTHONPATH=src python -m mec_lab --db test.db init-db
PYTHONPATH=src python -m mec_lab --db test.db load-dataset datasets/dev/baseline_dataset.json
PYTHONPATH=src python -m mec_lab --db test.db evaluate datasets/eval/eval_queries.json --ablation
PYTHONPATH=src python -m mec_lab --db test.db evaluate evidence/blind_queries.json --ablation
```

---

## 8. Estado

**READY_FOR_INDEPENDENT_REAUDIT**

- 116 testes passando (zero regressões)
- Bug de overlap stopwords/hints corrigido com 9 testes comportamentais
- Conflitos preservados
- Datasets e gold answers originais intocados
- Nenhum hardcode para consultas conhecidas
- Nenhum merge, tag ou release
- Harness Cognitivo não alterado
- Novo holdout do auditor NÃO foi acessado
