# PROMPT REWORK R3 — Correções após Experimento Real 01

## Papel

Você é o Agente Implementador do Rework R3 do MEC Lab.

## Base

- partir de `main`;
- criar a branch `rework/mec-live-memory-r3`;
- abrir PR draft para `main`;
- não alterar a branch do experimento;
- não fazer merge, tag ou release.

## Autoridade documental

Leia integralmente:

1. `experiments/exp-01/REPORT.md` na branch `experiment/mec-live-memory-01`;
2. PR #12;
3. código e testes atuais da `main`;
4. relatórios de auditoria anteriores apenas como contexto.

## Objetivo

Corrigir as limitações estruturais reveladas pelo Experimento Real 01 sem hardcodes para o Projeto Atlas e sem modificar o gabarito do experimento para melhorar artificialmente as métricas.

## Problemas obrigatórios

### R3-1 — Vigência versus obsolescência

Quando a consulta pede a decisão atual ou vigente, memórias `ACTIVE` ou `VERIFIED` que substituem outras devem superar as memórias `SUPERSEDED` ou `OBSOLETE`, mesmo quando a memória antiga possui maior sobreposição lexical.

Quando a consulta pede explicitamente histórico, antes ou versão anterior, a memória obsoleta deve permanecer recuperável.

A solução deve ser sensível à intenção da consulta. Não basta aumentar globalmente uma penalidade.

### R3-2 — Ausência real de evidência

Consultas sem suporte no banco não podem retornar todas as memórias como `relevant` apenas por terem relações ou pontuação residual.

Implemente uma política explícita e testável de abstention/ausência, distinguindo:

- `relevant`;
- `weak`;
- `absent`.

A ausência deve considerar força lexical/TF-IDF, cobertura dos termos relevantes e sinais do grafo. Relações isoladas não podem fabricar relevância.

### R3-3 — Próxima ação e risco pendente

Consultas de próxima ação, pendência, risco e trabalho seguinte devem priorizar memórias adequadas ao tipo/intenção, como checkpoints, hypotheses, decisions ou facts marcados como pendentes, sem hardcodes por identificador ou conteúdo do Atlas.

### R3-4 — Conflitos

Preservar a detecção correta de `SUPERSEDES`, `OBSOLETE`, versões e contradições, evitando duplicação ou sobre-detecção do mesmo conflito lógico.

## Restrições anti-overfitting

- não alterar `experiments/exp-01/gold_answers.json`;
- não alterar `experiments/exp-01/queries.json`;
- não criar regras específicas para Atlas, batch, queue, alertas ou IDs conhecidos;
- não acessar holdouts reservados das auditorias;
- não esconder resultados ruins;
- não remover consultas que falham.

## Testes obrigatórios

Adicionar testes comportamentais gerais cobrindo pelo menos:

1. decisão atual supera a superseded com maior overlap literal;
2. consulta histórica recupera a superseded;
3. consulta sem evidência retorna `absent` e zero resultados úteis;
4. relações isoladas não geram relevância;
5. próxima ação prioriza memória pendente adequada;
6. risco pendente é recuperável;
7. consulta neutra não recebe bônus de intenção;
8. conflito lógico não é duplicado;
9. todos os 116 testes anteriores permanecem passando.

## Evidências

Produza:

- `evidence/rework-r3/REPORT.md`;
- resultados brutos dos testes;
- comparação antes/depois no Experimento Real 01;
- análise por consulta;
- declaração explícita de limitações restantes.

Reexecute o Experimento Real 01 sem alterar suas consultas ou gabarito.

## Estado final máximo

`READY_FOR_INDEPENDENT_REAUDIT`
