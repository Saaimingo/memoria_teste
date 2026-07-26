# REWORK R1 — Relatório de Implementação

**Branch**: rework/mec-lab-baseline-r1
**Base**: feat/mec-lab-baseline @ 73c14aa
**Date**: 2026-07-26
**Python**: 3.11.15

---

## 1. Itens de Rework Executados

### 1.1 Scoring lexical corrigido
- Criado `retrieval/normalize.py` com lista unificada de stopwords (PT+EN, ~120 palavras)
- LexicalRetriever e HybridRetriever usam `token_set()` com remoção de stopwords
- Jaccard calculado apenas sobre tokens portadores de conteúdo
- Normalização: lowercase, strip accents (NFKD), colapso de whitespace

### 1.2 Falsa semântica removida
- `DeterministicSemanticAdapter` (MD5 hash) substituído por `TfidfAdapter`
- TF-IDF real: vocabulário construído a partir do dataset, IDF ponderado, L2-normalizado
- Determinístico, local, sem dependências externas
- Fallback: se vocabulário vazio, vetor [0.0]
- `DeterministicSemanticAdapter` e `NullSemanticAdapter` redirecionados para `TfidfAdapter` (backward compat)

### 1.3 Conflitos e vigência corrigidos
- `_detect_conflicts()` agora verifica:
  - `CONTRADICTED_BY` (já existia)
  - `SUPERSEDES` (novo)
  - Estado `OBSOLETE` / `SUPERSEDED` (novo)
  - Encadeamento `superseded_by` (novo)
  - Conflitos de versão (IDs iguais com versions diferentes, novo)

### 1.4 Testes fortalecidos
- 70 testes originais preservados
- 37 novos testes adicionados (107 total):
  - 6 testes de banco vazio
  - 7 testes de entrada inválida
  - 2 testes de JSON malformado
  - 2 testes de relações circulares
  - 2 testes de cadeia de supersedes
  - 8 testes de integridade de campos dos 8 tipos
  - 2 testes de isolamento de escopo de projeto
  - 3 testes de qualidade (relevant/weak/none)
  - 2 testes de conflito (supersedes detectado)
  - 1 teste de stopwords filtradas
  - 1 teste de query só com stopwords

### 1.5 Ranking recalibrado
- Pesos documentados com método: grid search em {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}, maximizando MRR no dataset dev
- Lexical: 1.0 (domina), Semantic: 0.4, Graph: 0.4, State: 0.2 (reduzido), Project: 0.6
- Entity e Temporal: peso 0 (componentes desativados por falta de dados)
- Temporal hints adicionados como bônus/penalidade separados (não via pesos)

### 1.6 Componentes mortos tratados
- **Entity score**: desativado (weight=0). Entidades raramente populadas no dataset.
- **Temporal score**: desativado (weight=0). `valid_from`/`valid_to` ausentes em todos os registros.
- **Checkpoint boost**: mantido, com bônus aumentado (0.15) quando query sugere "próxima ação"
- **Typing**: mantido, com peso 0.3

### 1.7 Ausência e incerteza melhoradas
- Sistema classifica qualidade em 3 níveis: `relevant`, `weak`, `none`
- Thresholds: min_relevant_score=0.08, min_weak_score=0.02
- Consultas sem tokens de conteúdo retornam `quality="none"` e inference apropriada
- `_detect_missing()` melhorado com mensagens contextuais

### 1.8 Temporal hints (R1 addition)
- Clue extraction detecta padrões linguísticos gerais:
  - `wants_historical`: "antes", "antigo", "obsoleto", "era", "anterior", "velho"
  - `wants_current`: "atual", "agora", "vigente", "hoje"
  - `wants_next_action`: "trabalhar", "próximo", "pendente", "fazer", "falta"
- Scoring usa esses hints para boost/penalize itens históricos, atuais e checkpoints

---

## 2. Métricas

### 2.1 Avaliação original (15 queries, mesmo dataset/gabarito)

| Métrica | Baseline | Rework R1 | Delta |
|---------|----------|-----------|-------|
| Hit@1 | 0.733 | 0.667 | -0.067 |
| Hit@3 | 0.867 | 0.867 | 0 |
| MRR | 0.800 | 0.756 | -0.044 |
| Precision@1 | 0.733 | 0.667 | -0.067 |

**Nota**: Queda esperada — stopwords removidas eliminam matches espúrios que inflavam a métrica original. As novas métricas refletem desempenho real sobre tokens de conteúdo.

### 2.2 Testes cegos (8 queries do auditor)

| Métrica | Baseline | Rework R1 | Delta |
|---------|----------|-----------|-------|
| Hit@1 | **0.000** | **0.250** | **+0.250** |
| Hit@3 | 0.250 | 0.500 | +0.250 |
| MRR | 0.183 | 0.367 | +0.184 |
| Precision@1 | 0.000 | 0.250 | +0.250 |

### 2.3 Ablation (testes cegos, R1)

| Variant | Hit@1 | Hit@3 | MRR |
|---------|-------|-------|-----|
| full_mec | 0.250 | 0.500 | 0.367 |
| no_semantic | 0.125 | 0.625 | 0.317 |
| no_graph | 0.125 | 0.500 | 0.295 |
| no_temporal | 0.250 | 0.500 | 0.367 |
| no_typing | 0.250 | 0.500 | 0.367 |
| no_state | 0.250 | 0.500 | 0.367 |
| no_checkpoint_boost | 0.250 | 0.500 | 0.367 |

**Análise**: TF-IDF semântico ajuda (+0.125 vs no_semantic). Grafo ajuda (+0.125 vs no_graph). Temporal, typing, state e checkpoint boost sem efeito nos cegos.

---

## 3. Limitações

1. **Blind Hit@1 = 0.250 < 0.50**: Não atingiu a meta do PROMPT_REWORK. Causa raiz: vocabulário das consultas cegas usa linguagem natural com sinônimos ("bug de repetição", "ligava de novo") que não casam com o vocabulário técnico do dataset ("duplicados", "reinicialização"). Sem embeddings reais ou expansão de sinônimos, o gap é inevitável.

2. **Queda no eval original**: Hit@1 caiu de 0.733 para 0.667 pela remoção de stopwords. As consultas originais foram construídas com matches lexicais que incluíam stopwords. O novo scoring é mais honesto.

3. **TF-IDF limitado**: O vocabulário é construído apenas do dataset (30 memórias). Não há conhecimento externo de sinônimos ou paráfrases.

4. **Embeddings reais não disponíveis**: `sentence-transformers` não instalado no ambiente. Se disponível, blind Hit@1 provavelmente subiria significativamente.

5. **Ruff/Mypy não executados**: Ferramentas não disponíveis no ambiente (SSL bloqueado para pip install).

---

## 4. Decisões Técnicas

1. **TF-IDF em vez de embeddings**: Escolhido porque é determinístico, local, e semanticamente superior ao hash MD5. Não requer downloads ou serviços externos.
2. **Entity e Temporal desativados**: Dados insuficientes no dataset para exercitar esses componentes. Manter código mas com weight=0 até que o dataset seja enriquecido.
3. **Temporal hints como bônus separados**: Não via sistema de pesos porque são ativados/desativados por consulta, não por configuração global.
4. **State weight reduzido**: De 0.4 para 0.2. O valor original causava ruído por premiar quase todos os itens igualmente.

---

## 5. Evidências

- `evidence/rework-r1/raw/original_eval.md` — avaliação original (15 queries)
- `evidence/rework-r1/raw/blind_eval.md` — avaliação cega (8 queries)
- 107 testes passando (`python -m tests.run_tests`)
- Todos os 70 testes originais mantidos

---

## 6. Comandos de Reprodução

```bash
git clone https://github.com/Saaimingo/memoria_teste.git
cd memoria_teste
git checkout rework/mec-lab-baseline-r1
PYTHONPATH=src python -m tests.run_tests
PYTHONPATH=src python -m mec_lab --db test.db init-db
PYTHONPATH=src python -m mec_lab --db test.db load-dataset datasets/dev/baseline_dataset.json
PYTHONPATH=src python -m mec_lab --db test.db evaluate datasets/eval/eval_queries.json --ablation
PYTHONPATH=src python -m mec_lab --db test.db evaluate evidence/blind_queries.json --ablation
```

---

## 7. Estado

**READY_FOR_INDEPENDENT_REAUDIT**

- Dataset original e gold answers preservados
- Nenhum hardcode para consultas cegas
- Nenhum merge, tag ou release
- Harness Cognitivo não alterado
