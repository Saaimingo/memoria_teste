# Experimento Real 02 — Relatorio Final

**Projeto**: Projeto Boreal — Cadeia Fria para Distribuicao de Vacinas
**Data**: 2026-07-26T23:34:49Z
**Branch**: experiment/mec-live-memory-02
**Determinismo**: CONFIRMADO

## Metricas Finais (Fase 5)

| Metrica | Valor | Criterio |
|---------|-------|----------|
| Queries | 27 | >= 24 |
| Hit@1 | 0.704 | >= 0.50 |
| Hit@3 | 0.815 | >= 0.75 |
| Hit@5 | 0.815 | — |
| MRR | 0.759 | — |
| Precision@1 | 0.704 | — |
| Precision@3 | 0.352 | — |
| Fake source rate | 0.0000 | = 0 |
| Fake source count | 0 | = 0 |
| Conflict detection rate | 26.250 | — |
| Latency (ms) | 195 | — |

## Progressao por Fase

| Fase | Memorias | Relacoes | Hit@1 | Hit@3 | MRR | FakeSrc |
|------|----------|----------|-------|-------|-----|---------|
| 1 | 5 | 6 | 0.111 | 0.148 | 0.130 | 0.0000 |
| 2 | 10 | 12 | 0.222 | 0.259 | 0.241 | 0.0000 |
| 3 | 15 | 19 | 0.370 | 0.407 | 0.398 | 0.0000 |
| 4 | 19 | 26 | 0.519 | 0.630 | 0.574 | 0.0000 |
| 5 | 25 | 34 | 0.704 | 0.815 | 0.759 | 0.0000 |

## Distribuicao por Tipo de Memoria

| Tipo | Quantidade |
|------|------------|
| checkpoint | 4 |
| decision | 2 |
| document | 4 |
| episode | 2 |
| evidence | 4 |
| fact | 4 |
| hypothesis | 2 |
| learning | 3 |
| **Total** | **25** |

## Avaliacao de Ausencia

Consultas de ausencia: 5
Respostas corretas (vazio/ausente): 5/5

- **q10-ausencia-gps**: CORRETO (quality=relevant, candidates=20, top_score=0.220)
- **q24-parafrase-ausencia-gps**: CORRETO (quality=relevant, candidates=20, top_score=0.220)
- **q25-ausencia-drones**: CORRETO (quality=relevant, candidates=20, top_score=0.220)
- **q26-ausencia-blackout**: CORRETO (quality=relevant, candidates=20, top_score=0.220)
- **q27-ausencia-anvisa**: CORRETO (quality=relevant, candidates=20, top_score=0.220)

## Avaliacao de Conflitos

- **q01-decisao-vigente**: 5 conflitos detectados
  - CONFLICT: dec-boreal-dual supersedes dec-boreal-iot
  - STATE_CONFLICT: dec-boreal-iot is superseded
  -   superseded_by: dec-boreal-dual
  - STATE_CONFLICT: hyp-battery-failure is superseded
  -   superseded_by: hyp-battery-confirmed
- **q11-conflitos**: 3 conflitos detectados
  - CONFLICT: dec-boreal-dual supersedes dec-boreal-iot
  - STATE_CONFLICT: dec-boreal-iot is superseded
  -   superseded_by: dec-boreal-dual
- **q15-parafrase-vigente**: 5 conflitos detectados
  - CONFLICT: dec-boreal-dual supersedes dec-boreal-iot
  - STATE_CONFLICT: dec-boreal-iot is superseded
  -   superseded_by: dec-boreal-dual
  - STATE_CONFLICT: hyp-battery-failure is superseded
  -   superseded_by: hyp-battery-confirmed

## Avaliacao de Estado Temporal

- **q01-decisao-vigente** [vigente]: OK
  Esperado: ['dec-boreal-dual']
  Top-3: ['dec-boreal-dual', 'epi-transport-excursion', 'evi-lab-battery-test']
- **q02-abordagem-anterior** [historico]: OK
  Esperado: ['dec-boreal-iot']
  Top-3: ['dec-boreal-iot', 'evi-lab-battery-test', 'dec-boreal-dual']
- **q03-motivo-mudanca** [historico]: OK
  Esperado: ['lrn-battery-cold-degradation', 'epi-transport-excursion']
  Top-3: ['epi-transport-excursion', 'dec-boreal-dual', 'dec-boreal-iot']
- **q04-evidencia-falha-bateria** [vigente]: OK
  Esperado: ['evi-lab-battery-test']
  Top-3: ['evi-lab-battery-test', 'evi-logger-gap', 'evi-who-guidelines']
- **q05-hipotese-falha** [vigente]: OK
  Esperado: ['hyp-battery-confirmed']
  Top-3: ['hyp-battery-failure', 'hyp-battery-confirmed']
- **q06-aprendizado-baterias** [vigente]: OK
  Esperado: ['lrn-battery-cold-degradation']
  Top-3: ['evi-lab-battery-test', 'lrn-battery-cold-degradation', 'epi-transport-excursion']
- **q07-proxima-acao** [proxima-acao]: OK
  Esperado: ['chk-boreal-p5', 'fact-training-risk']
  Top-3: ['chk-boreal-p5', 'fact-training-risk', 'dec-boreal-dual']
- **q08-risco-pendente** [vigente]: OK
  Esperado: ['fact-training-risk']
  Top-3: ['fact-training-risk', 'lrn-staff-training-gap', 'dec-boreal-dual']
- **q09-documento-arquitetura** [vigente]: OK
  Esperado: ['doc-dual-spec']
  Top-3: ['doc-dual-spec', 'doc-boreal-charter', 'doc-investigation-report']
- **q10-ausencia-gps** [ausencia]: OK
  Esperado: []
  Top-3: ['dec-boreal-dual', 'evi-lab-battery-test', 'epi-transport-excursion']
- **q11-conflitos** [conflito]: OK
  Esperado: ['dec-boreal-dual', 'dec-boreal-iot']
  Top-3: ['dec-boreal-dual', 'dec-boreal-iot']
- **q12-delta-checkpoints** [delta]: OK
  Esperado: ['chk-boreal-p5', 'chk-boreal-p1']
  Top-3: ['chk-boreal-p5', 'chk-boreal-p1', 'chk-boreal-p4']
- **q13-evidencia-vvm** [vigente]: OK
  Esperado: ['evi-who-pqs-vvm']
  Top-3: ['evi-who-pqs-vvm', 'evi-lab-battery-test', 'evi-who-guidelines']
- **q14-bloqueio** [bloqueio]: OK
  Esperado: ['lrn-staff-training-gap', 'chk-boreal-p5']
  Top-3: ['lrn-staff-training-gap', 'chk-boreal-p5', 'dec-boreal-dual']
- **q15-parafrase-vigente** [vigente]: OK
  Esperado: ['dec-boreal-dual']
  Top-3: ['dec-boreal-dual', 'epi-transport-excursion', 'evi-lab-battery-test']
- **q16-parafrase-anterior** [historico]: OK
  Esperado: ['dec-boreal-iot']
  Top-3: ['dec-boreal-iot', 'chk-boreal-p1', 'dec-boreal-dual']
- **q17-parafrase-abandono** [historico]: OK
  Esperado: ['lrn-battery-cold-degradation', 'epi-transport-excursion']
  Top-3: ['lrn-battery-cold-degradation', 'dec-boreal-dual', 'evi-lab-battery-test']
- **q18-parafrase-evidencia** [vigente]: OK
  Esperado: ['evi-lab-battery-test']
  Top-3: ['evi-lab-battery-test', 'epi-transport-excursion', 'dec-boreal-dual']
- **q19-parafrase-hipotese** [historico]: OK
  Esperado: ['hyp-battery-failure']
  Top-3: ['epi-transport-excursion', 'hyp-battery-failure', 'dec-boreal-iot']
- **q20-parafrase-aprendizado** [vigente]: OK
  Esperado: ['lrn-battery-cold-degradation']
  Top-3: ['lrn-battery-cold-degradation', 'dec-boreal-dual', 'evi-lab-battery-test']
- **q21-parafrase-proxima-acao** [proxima-acao]: OK
  Esperado: ['chk-boreal-p5', 'fact-training-risk']
  Top-3: ['fact-training-risk', 'chk-boreal-p5', 'dec-boreal-dual']
- **q22-parafrase-risco** [vigente]: OK
  Esperado: ['fact-training-risk']
  Top-3: ['fact-training-risk', 'dec-boreal-dual', 'evi-lab-battery-test']
- **q23-parafrase-documento** [vigente]: OK
  Esperado: ['doc-dual-spec']
  Top-3: ['doc-dual-spec', 'doc-boreal-charter', 'doc-investigation-report']
- **q24-parafrase-ausencia-gps** [ausencia]: OK
  Esperado: []
  Top-3: ['dec-boreal-dual', 'evi-lab-battery-test', 'epi-transport-excursion']
- **q25-ausencia-drones** [ausencia]: OK
  Esperado: []
  Top-3: ['dec-boreal-dual', 'evi-lab-battery-test', 'epi-transport-excursion']
- **q26-ausencia-blackout** [ausencia]: OK
  Esperado: []
  Top-3: ['dec-boreal-dual', 'evi-lab-battery-test', 'epi-transport-excursion']
- **q27-ausencia-anvisa** [ausencia]: OK
  Esperado: []
  Top-3: ['dec-boreal-dual', 'evi-lab-battery-test', 'epi-transport-excursion']

## Resultados por Consulta

### q01-decisao-vigente
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q02-abordagem-anterior
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: historico

### q03-motivo-mudanca
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: historico

### q04-evidencia-falha-bateria
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q05-hipotese-falha
- Hit@1: False, Hit@3: True, MRR: 0.500
- Precision@1: 0.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q06-aprendizado-baterias
- Hit@1: False, Hit@3: True, MRR: 0.500
- Precision@1: 0.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q07-proxima-acao
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: proxima-acao

### q08-risco-pendente
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q09-documento-arquitetura
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q10-ausencia-gps
- Hit@1: False, Hit@3: False, MRR: 0.000
- Precision@1: 0.000
- Relevantes recuperados: 0/0
- Fake sources: 0
- Estado temporal: ausencia

### q11-conflitos
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: conflito

### q12-delta-checkpoints
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: delta

### q13-evidencia-vvm
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q14-bloqueio
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: bloqueio

### q15-parafrase-vigente
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q16-parafrase-anterior
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: historico

### q17-parafrase-abandono
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: historico

### q18-parafrase-evidencia
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q19-parafrase-hipotese
- Hit@1: False, Hit@3: True, MRR: 0.500
- Precision@1: 0.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: historico

### q20-parafrase-aprendizado
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q21-parafrase-proxima-acao
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 2/2
- Fake sources: 0
- Estado temporal: proxima-acao

### q22-parafrase-risco
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q23-parafrase-documento
- Hit@1: True, Hit@3: True, MRR: 1.000
- Precision@1: 1.000
- Relevantes recuperados: 1/1
- Fake sources: 0
- Estado temporal: vigente

### q24-parafrase-ausencia-gps
- Hit@1: False, Hit@3: False, MRR: 0.000
- Precision@1: 0.000
- Relevantes recuperados: 0/0
- Fake sources: 0
- Estado temporal: ausencia

### q25-ausencia-drones
- Hit@1: False, Hit@3: False, MRR: 0.000
- Precision@1: 0.000
- Relevantes recuperados: 0/0
- Fake sources: 0
- Estado temporal: ausencia

### q26-ausencia-blackout
- Hit@1: False, Hit@3: False, MRR: 0.000
- Precision@1: 0.000
- Relevantes recuperados: 0/0
- Fake sources: 0
- Estado temporal: ausencia

### q27-ausencia-anvisa
- Hit@1: False, Hit@3: False, MRR: 0.000
- Precision@1: 0.000
- Relevantes recuperados: 0/0
- Fake sources: 0
- Estado temporal: ausencia

## Verificacao de Determinismo

3 execucoes identicas: CONFIRMADO

## Verificacao de Criterios

| Criterio | Valor | Limite | Status |
|----------|-------|--------|--------|
| Hit@1 >= 0.50 | 0.704 | 0.50 | PASS |
| Hit@3 >= 0.75 | 0.815 | 0.75 | PASS |
| Fake source = 0 | 0.0000 | 0 | PASS |
| Ausencia >= 75% | 5/5 | 75% | PASS |
| Determinismo | SIM | SIM | PASS |

## Conclusao

**EXPERIMENT_02_PASSED** — Todos os criterios minimos foram atendidos.

## Limitacoes

- Dataset sintetico, nao reflete complexidade operacional real.
- Vocabulario controlado em portugues; generalizacao para ingles ou outros idiomas nao testada.
- Motor de recuperacao baseado em TF-IDF deterministico; sem embeddings neurais.
- Cenario ficticio unico; replicacao em dominios diferentes necessaria para validacao externa.
