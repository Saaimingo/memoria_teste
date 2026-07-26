# PROMPT — EXPERIMENTO REAL 01 DO MEC LAB

## Papel

Você é o Agente Executor do Experimento Real 01 do MEC Lab.

Você não deve redesenhar o sistema, trocar arquitetura, recalibrar pesos ou corrigir código durante a execução do experimento. Seu papel é usar a versão aprovada na `main`, registrar evidências e apontar falhas observadas.

## Objetivo

Testar se o MEC Lab consegue acompanhar uma história de projeto ao longo do tempo e recuperar corretamente:

1. o fato ou regra vigente;
2. o que ficou obsoleto;
3. por que uma decisão foi tomada;
4. qual evidência sustenta a decisão;
5. o que mudou entre versões;
6. quais conflitos ainda existem;
7. qual é o próximo trabalho registrado;
8. quando não existe evidência suficiente para responder.

## Base e branch

- base obrigatória: `main`
- branch obrigatória: `experiment/mec-live-memory-01`
- PR final: draft para `main`
- não fazer merge, tag ou release

## Cenário controlado

Crie um projeto sintético chamado `Projeto Atlas`.

O projeto deve representar a construção de um sistema de alertas operacionais. A história deve possuir pelo menos quatro fases cronológicas claramente separadas.

### Fase 1 — decisão inicial

Registre, no mínimo:

- objetivo inicial do projeto;
- decisão de usar processamento em lote;
- justificativa da escolha;
- evidência que sustentava a decisão naquele momento;
- primeiro checkpoint;
- próxima ação planejada.

### Fase 2 — problema observado

Registre, no mínimo:

- episódio de alertas duplicados após reinicialização;
- evidência reproduzível do problema;
- hipótese de causa;
- aprendizagem obtida;
- checkpoint atualizado;
- relação explícita entre problema, hipótese e evidência.

### Fase 3 — mudança de decisão

Registre, no mínimo:

- nova decisão de substituir processamento em lote por fila persistente;
- motivo da mudança;
- relação `SUPERSEDES` entre decisão nova e antiga;
- decisão antiga marcada como obsoleta;
- evidência da nova escolha;
- conflito ou incompatibilidade entre versões;
- checkpoint contendo o novo estado vigente.

### Fase 4 — estado atual

Registre, no mínimo:

- implementação parcial da fila persistente;
- risco ainda pendente;
- próximo trabalho prioritário;
- documento de referência;
- checkpoint final;
- item cuja resposta correta seja ausência de evidência.

## Cobertura mínima de memória

O experimento deve usar todos os oito tipos:

- Fact
- Decision
- Hypothesis
- Evidence
- Learning
- Episode
- Checkpoint
- Document

Use relações suficientes para formar uma cadeia causal e temporal explícita. Inclua, quando aplicável:

- SUPPORTS
- CAUSED_BY
- DERIVED_FROM
- SUPERSEDES
- CONTRADICTED_BY
- BLOCKS
- RELATED_TO

Não invente relações que não existam no enum do sistema. Confirme os nomes reais antes de popular o banco.

## Execução longitudinal obrigatória

Não carregue toda a história de uma vez.

Execute o experimento em quatro etapas independentes:

1. popular somente a Fase 1 e consultar;
2. adicionar a Fase 2 e consultar novamente;
3. adicionar a Fase 3 e repetir as consultas;
4. adicionar a Fase 4 e executar a avaliação final.

Preserve snapshots ou bancos separados por fase para permitir reprodução.

## Consultas obrigatórias

Crie consultas em linguagem natural e paráfrases, sem copiar literalmente os conteúdos armazenados.

Teste, no mínimo:

1. Qual abordagem está vigente para processar os alertas?
2. Como o sistema fazia isso antes da mudança?
3. Por que a abordagem inicial foi abandonada?
4. Que evidência demonstrou o problema de duplicação?
5. Qual hipótese explicou os alertas repetidos?
6. O que aprendemos com a reinicialização?
7. Em que devo trabalhar agora?
8. Qual risco ainda impede a conclusão?
9. Que documento descreve a arquitetura atual?
10. Existe decisão registrada sobre criptografia ponta a ponta?
11. Quais versões ou memórias estão em conflito?
12. O que mudou entre o primeiro e o último checkpoint?

Adicione pelo menos oito paráfrases adversariais, usando vocabulário diferente do conteúdo armazenado.

## Gabarito

O gabarito deve ser criado antes de executar a avaliação final.

Para cada consulta, registre:

- IDs esperados;
- IDs aceitáveis secundários;
- resposta esperada em linguagem humana;
- estado temporal esperado: histórico, vigente, próxima ação ou ausência;
- conflito esperado, quando aplicável;
- justificativa do gabarito.

Não altere o gabarito depois de observar os resultados. Qualquer correção posterior deve ser registrada como errata, com motivo e diff.

## Métricas e análise

Calcule por fase e no consolidado:

- Hit@1
- Hit@3
- MRR
- Precision@1
- taxa de ausência correta
- taxa de detecção de conflito
- acerto de estado temporal
- fake source rate

Além das métricas agregadas, produza análise por consulta. Uma média boa não pode esconder falhas graves em decisão vigente, obsolescência, conflito ou ausência.

## Critérios do Experimento 01

O experimento será considerado satisfatório somente se:

- todos os 116 testes existentes continuarem passando;
- todos os oito tipos de memória forem usados de forma substantiva;
- a decisão vigente superar a obsoleta nas consultas atuais;
- a decisão obsoleta continuar recuperável em consultas históricas;
- `SUPERSEDES` e obsolescência produzirem conflito detectável;
- a próxima ação correta for recuperada;
- a consulta sem evidência não produzir resposta afirmativa inventada;
- fake source rate permanecer em 0;
- todo resultado for reproduzível a partir dos artefatos versionados.

Não ajuste thresholds, pesos ou conteúdo para forçar aprovação.

## Artefatos obrigatórios

Crie:

- `experiments/exp-01/README.md`
- `experiments/exp-01/populate_phase_1.py`
- `experiments/exp-01/populate_phase_2.py`
- `experiments/exp-01/populate_phase_3.py`
- `experiments/exp-01/populate_phase_4.py`
- `experiments/exp-01/queries.json`
- `experiments/exp-01/gold_answers.json`
- `experiments/exp-01/run_experiment.py`
- `experiments/exp-01/REPORT.md`
- `experiments/exp-01/RAW_RESULTS/`

Os scripts devem ser determinísticos, idempotentes quando possível e executáveis no Windows usado pelo projeto.

## Proibições

- não usar o Harness Cognitivo principal;
- não alterar datasets antigos ou holdouts de auditoria;
- não acessar ou incorporar consultas reservadas de auditoria;
- não corrigir o motor durante o experimento;
- não criar hardcodes por query-ID;
- não reduzir critérios após observar resultados;
- não declarar sucesso apenas porque os testes unitários passaram;
- não fazer merge, tag ou release.

## Estado final permitido

Ao concluir, declare exatamente um estado:

- `EXPERIMENT_01_PASSED`
- `EXPERIMENT_01_FAILED`
- `EXPERIMENT_01_INCONCLUSIVE`

O relatório deve separar claramente:

- fatos observados;
- métricas calculadas;
- limitações;
- inferências;
- recomendação para o próximo experimento.
