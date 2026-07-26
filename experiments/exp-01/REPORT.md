# Experimento Real 01 — Relatório

**Data**: 2026-07-26T22:41:26.209877+00:00
**Projeto**: Projeto Atlas
**Branch**: experiment/mec-live-memory-01

## Sumário Executivo

- Queries avaliadas: 20
- Hit@1: 0.500
- Hit@3: 0.750
- MRR: 0.628
- Precision@1: 0.500
- Fake source rate: 0.0000
- Conflict detection rate: 6.000
- Testes preservados: True

## Memórias por Tipo

| Tipo | Quantidade |
|------|-----------|
| fact | 4 |
| decision | 2 |
| hypothesis | 2 |
| evidence | 3 |
| learning | 1 |
| episode | 1 |
| checkpoint | 4 |
| document | 1 |

## Per-Query Results

| Query ID | Hit@1 | Hit@3 | MRR | Conflicts |
|----------|-------|-------|-----|-----------|
| q01-decisao-vigente | True | True | 1.000 | 0 |
| q02-abordagem-anterior | True | True | 1.000 | 2 |
| q03-motivo-abandono | False | False | 0.200 | 2 |
| q04-evidencia-duplicacao | False | True | 0.333 | 0 |
| q05-hipotese-replay | True | True | 1.000 | 0 |
| q06-aprendizado-reinicializacao | False | True | 0.500 | 2 |
| q07-proximo-trabalho | False | True | 0.500 | 0 |
| q08-risco-pendente | True | True | 1.000 | 2 |
| q09-documento-arquitetura | True | True | 1.000 | 0 |
| q10-criptografia-ausente | False | False | 0.000 | 0 |
| q11-conflitos | True | True | 1.000 | 2 |
| q12-delta-checkpoints | True | True | 1.000 | 0 |
| p01-parafrase-vigente | True | True | 1.000 | 0 |
| p02-parafrase-antigo | True | True | 1.000 | 2 |
| p03-parafrase-motivo | False | False | 0.200 | 2 |
| p04-parafrase-prova | False | False | 0.000 | 0 |
| p05-parafrase-proxima | False | True | 0.333 | 2 |
| p06-parafrase-bloqueio | True | True | 1.000 | 2 |
| p07-parafrase-seguranca | False | False | 0.000 | 0 |
| p08-parafrase-evolucao | False | True | 0.500 | 0 |

## Fatos Observados

(preenchido após análise dos resultados brutos)

## Métricas Calculadas

Ver RAW_RESULTS/aggregate_metrics.json e RAW_RESULTS/per_query_details.json

## Limitações

- Baseline usa apenas busca lexical + TF-IDF determinístico
- Sem re-ranqueamento por LLM
- Cenário sintético com 18 memórias

## Inferências

(preenchido após análise)

## Recomendação para o Próximo Experimento

(preenchido após análise)