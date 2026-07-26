# Experimento Real 01 — Relatório Final

**Data**: 2026-07-26
**Projeto**: Projeto Atlas (sistema de alertas operacionais)
**Branch**: experiment/mec-live-memory-01
**Veredito**: EXPERIMENT_01_FAILED

## Sumário Executivo

O experimento testou se o baseline MEC Lab consegue acompanhar uma história
de projeto em quatro fases e responder corretamente consultas sobre estado
vigente, histórico, conflito, próxima ação e ausência de evidência.

**Resultado**: 6 de 20 consultas com Hit@1 (30%). A decisão vigente (fila
persistente) foi superada pela decisão obsoleta (processamento em lote) no
ranking. O sistema não detecta ausência de evidência — retorna memórias
irrelevantes com qualidade "relevant". A próxima ação e o risco pendente
não aparecem no topo.

116 testes preservados. Fake source rate = 0. Todos os 8 tipos de memória
usados substantivamente.

| Métrica | Valor |
|---------|-------|
| Hit@1 | 0.300 |
| Hit@3 | 0.600 |
| MRR | 0.444 |
| Precision@1 | 0.300 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 16.000 |

## Memórias por Tipo

| Tipo | Quantidade | IDs |
|------|-----------|-----|
| Fact | 4 | fact-atlas-obj, fact-atlas-impl, fact-atlas-risk, fact-atlas-next |
| Decision | 2 | dec-atlas-batch (SUPERSEDED), dec-atlas-queue (ACTIVE) |
| Hypothesis | 2 | hyp-atlas-cap, hyp-atlas-replay |
| Evidence | 3 | evi-atlas-bench, evi-atlas-log, evi-atlas-queue-bench |
| Learning | 1 | lrn-atlas-idem |
| Episode | 1 | epi-atlas-dup |
| Checkpoint | 4 | chk-atlas-01 a chk-atlas-04 |
| Document | 1 | doc-atlas-arch |

**Total**: 18 memórias, 22 relações.

## Per-Query Results

| Query ID | Hit@1 | Hit@3 | MRR | Prec@1 | Conflicts |
|----------|-------|-------|-----|--------|-----------|
| q01-decisao-vigente | False | True | 0.333 | 0.000 | 3 |
| q02-abordagem-anterior | False | False | 0.067 | 0.000 | 3 |
| q03-motivo-abandono | True | True | 0.500 | 1.000 | 3 |
| q04-evidencia-duplicacao | False | True | 0.333 | 0.000 | 0 |
| q05-hipotese-replay | True | True | 0.500 | 1.000 | 0 |
| q06-aprendizado-reinicializacao | True | True | 1.000 | 1.000 | 3 |
| q07-proximo-trabalho | False | False | 0.111 | 0.000 | 3 |
| q08-risco-pendente | False | True | 0.250 | 0.000 | 3 |
| q09-documento-arquitetura | False | True | 0.250 | 0.000 | 0 |
| q10-criptografia-ausente | False | False | 0.000 | 0.000 | 0 |
| q11-conflitos | True | True | 0.500 | 1.000 | 3 |
| q12-delta-checkpoints | True | True | 0.500 | 1.000 | 3 |
| p01-parafrase-vigente | False | True | 0.250 | 0.000 | 3 |
| p02-parafrase-antigo | False | False | 0.077 | 0.000 | 3 |
| p03-parafrase-motivo | True | True | 0.500 | 1.000 | 3 |
| p04-parafrase-prova | False | False | 0.167 | 0.000 | 0 |
| p05-parafrase-proxima | False | False | 0.091 | 0.000 | 3 |
| p06-parafrase-bloqueio | False | True | 0.200 | 0.000 | 3 |
| p07-parafrase-seguranca | False | False | 0.000 | 0.000 | 3 |
| p08-parafrase-evolucao | True | True | 1.000 | 1.000 | 3 |

## Fatos Observados

### F1 — Decisão obsoleta supera a vigente (FALHA CRÍTICA)

Na consulta "Qual abordagem está vigente para processar os alertas?" (q01),
a decisão antiga `dec-atlas-batch` (processamento em lote, status SUPERSEDED)
obteve score 0.363, enquanto a decisão vigente `dec-atlas-queue` (fila
persistente, status ACTIVE) obteve score 0.220.

**Causa**: O motor lexical favorece correspondência literal de palavras.
"Processar os alertas" tem sobreposição com "Processar alertas em lote"
(Jaccard 0.133), mas zero sobreposição com "Substituir processamento em
lote por fila persistente" — a decisão nova não contém as palavras de
busca porque seu texto é sobre a substituição, não sobre o processamento
em si.

A penalidade de estado (-0.10 para SUPERSEDED) é insuficiente para
compensar a vantagem lexical da decisão antiga.

### F2 — Ausência de evidência não é detectada

Consultas sobre tópicos inexistentes (q10: criptografia, p07: segurança
ponta a ponta) retornam 18 memórias com qualidade "relevant". O sistema
não possui mecanismo de cutoff que distinga "resultados fracamente
relacionados" de "nenhum resultado relevante".

A qualidade "relevant" é atribuída porque o score mínimo de relevância
(0.08) é facilmente atingido via relation_score (0.2-0.5) em qualquer
memória conectada ao grafo de relações.

### F3 — Próxima ação e risco não ranqueiam no topo

`fact-atlas-next` (próximo trabalho) e `fact-atlas-risk` (risco pendente)
aparecem nas posições 6 e 5 respectivamente em suas consultas alvo. O
score é dominado por relation_score (relações compartilhadas por muitas
memórias), diluindo o sinal lexical.

### F4 — Conflitos detectados, mas sem especificidade

O motor detecta corretamente o conflito SUPERSEDES entre as duas decisões.
No entanto, o mesmo conflito aparece em 15 das 20 consultas, mesmo quando
a consulta não é sobre conflitos. A taxa de detecção (16.0) reflete essa
sobre-detecção: 3 conflitos esperados no total, mas ~48 detectados
distribuídos.

### F5 — Testes preservados (116/116)

Nenhum teste existente foi quebrado. O experimento foi conduzido sem
alterar motor, pesos ou thresholds.

### F6 — Fake source rate = 0

Nenhuma memória inexistente foi retornada. Todas as 18 memórias do banco
são válidas.

## Métricas Calculadas

### Agregadas (20 consultas)

| Métrica | Valor |
|---------|-------|
| Precision@1 | 0.300 |
| Precision@3 | 0.317 |
| Hit@1 rate | 0.300 |
| Hit@3 rate | 0.600 |
| MRR | 0.444 |
| Fake source rate | 0.0000 |
| Conflict detection rate | 16.000 |

### Por fase (consultas parciais)

| Fase | Consultas | Observação |
|------|-----------|------------|
| 1 | q01, q02, q12 | Apenas 5 memórias; decisão batch é a única ativa |
| 2 | q04, q05, q06 | Evidência e hipótese do problema registradas |
| 3 | q01, q03, q11 | Conflito SUPERSEDES emerge; batch perde status |
| 4 | Todas 20 | Avaliação completa com 18 memórias |

## Limitações

1. **Baseline lexical puro**: O motor usa Jaccard + TF-IDF determinístico.
   Sem embeddings semânticos reais, paráfrases com vocabulário diferente
   do conteúdo armazenado têm score lexical zero.

2. **Peso das relações domina**: Muitas memórias compartilham
   relation_score 0.2-0.5, tornando o ranking pouco discriminativo para
   consultas que não casam lexicalmente.

3. **Penalidade de estado insuficiente**: O estado SUPERSEDED recebe
   penalidade de apenas -0.10, facilmente superada por vantagem lexical.

4. **Ausência de cutoff de relevância**: O threshold `min_relevant_score`
   (0.08) é baixo demais; relation_score sozinho ultrapassa esse valor
   para qualquer memória conectada.

5. **Extração de pistas incompleta**: O dicionário de type_keywords não
   cobre flexões verbais ("decidiu" vs "decisão"), causando comportamento
   inconsistente entre consultas morfologicamente relacionadas.

6. **Cenário pequeno**: 18 memórias é um cenário sintético controlado.
   Com mais memórias, o ranking pode melhorar (mais competição lexical)
   ou piorar (mais ruído de relações).

7. **Conflito sobre-detectado**: O mesmo SUPERSEDES aparece em quase
   todas as consultas porque ambas as decisões estão no grafo e sempre
   ranqueiam.

## Inferências

1. O baseline atual **não é confiável para recuperar a decisão vigente**
   quando a decisão nova usa vocabulário diferente da consulta. Isso é
   uma falha fundamental para um sistema de memória operacional.

2. A **ausência de detecção de "não sei"** é uma limitação arquitetural:
   o retriever sempre retorna algo, e o threshold de relevância é baixo
   demais para filtrar.

3. O **mecanismo de conflito** funciona (detecta SUPERSEDES), mas precisa
   de contexto — o conflito só deveria ser reportado quando pertinente à
   consulta, não em toda busca.

4. **Paráfrases adversariais** com vocabulário diferente do armazenado
   falham consistentemente (p02, p04, p05, p06). Isso expõe a fragilidade
   do motor puramente lexical.

5. Os 116 testes existentes **não cobrem** os cenários de memória
   longitudinal, decisão vigente vs obsoleta, ou detecção de ausência —
   o experimento revelou classes de falha que os testes unitários não
   capturam.

## Recomendação para o Próximo Experimento

1. **Experimento 02 — Recalibração de thresholds**: Investigar se ajustes
   nos pesos (aumentar state_weight, reduzir relation_weight, elevar
   min_relevant_score) resolvem as falhas F1 e F2 sem quebrar os casos
   que funcionam. Isso exige autorização para alterar pesos (proibido
   neste experimento).

2. **Experimento 03 — Embeddings semânticos reais**: Substituir o TF-IDF
   determinístico por embeddings via sentence-transformers e medir o
   impacto em paráfrases e consultas com vocabulário diferente.

3. **Experimento 04 — Detecção de ausência**: Implementar um mecanismo
   explícito de "no answer" baseado em score máximo abaixo de threshold
   calibrado, testando com consultas sobre tópicos completamente ausentes.

4. **Testes de regressão**: Adicionar casos de teste que cubram
   especificamente: decisão vigente vs obsoleta, ausência de evidência,
   e robustez a paráfrases.

## Artefatos

Todos os artefatos estão versionados em:
`experiments/exp-01/`

- `populate_phase_1.py` a `populate_phase_4.py` — scripts de população
- `queries.json` — 20 consultas (12 obrigatórias + 8 paráfrases)
- `gold_answers.json` — gabarito criado antes da avaliação
- `run_experiment.py` — orquestrador determinístico e reproduzível
- `RAW_RESULTS/` — snapshots, métricas brutas, detalhes por consulta
- `REPORT.md` — este relatório

## Verificação de Reproducibilidade

```bash
cd /d/memoria_teste
git checkout experiment/mec-live-memory-01
python experiments/exp-01/run_experiment.py
```

O experimento é determinístico: usa SQLite em memória, TF-IDF
determinístico, e seeds fixas nos IDs. Cada execução produz os
mesmos resultados.
