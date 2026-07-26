# PROMPT — EXPERIMENTO REAL 02

## Papel

Você é o Agente Executor do Experimento Real 02 do MEC Lab.

## Objetivo

Avaliar se o motor aprovado no R3 generaliza para um domínio novo, com vocabulário, entidades, relações e evolução temporal diferentes do Projeto Atlas.

O domínio será o **Projeto Boreal**, uma operação fictícia de cadeia fria para distribuição de vacinas entre um centro regional e clínicas remotas.

Este experimento não autoriza alterações no motor, pesos, thresholds, stemmer ou regras de recuperação.

## Base e branch

- base obrigatória: `main`
- branch obrigatória: `experiment/mec-live-memory-02`
- PR final: draft para `main`

## História longitudinal obrigatória

A história deve ser populada progressivamente em cinco fases. Não carregue todas as memórias de uma vez.

### Fase 1 — Plano inicial

Registre que o Projeto Boreal decidiu usar caixas térmicas passivas com gelo reutilizável, conferência manual na saída e entrega em rota fixa duas vezes por semana.

Inclua objetivo, hipótese operacional, documento de arquitetura, evidência inicial e checkpoint.

### Fase 2 — Incidente operacional

Registre um episódio em que uma entrega chegou fora da faixa de temperatura devido a atraso de transporte e leitura tardia do termômetro.

Inclua evidências, causa provável, impacto, aprendizado e risco aberto.

### Fase 3 — Mudança de estratégia

Registre uma nova decisão que substitui parcialmente o plano inicial: sensores contínuos com alerta, rota dinâmica e prioridade para remessas críticas.

A decisão antiga deve continuar historicamente recuperável, mas não deve aparecer como vigente quando a pergunta pedir o estado atual.

Use relações como `SUPERSEDES`, `SUPPORTED_BY`, `CAUSED_BY`, `DERIVED_FROM`, `REFERENCES` e `SUMMARIZES` conforme aplicável.

### Fase 4 — Implementação parcial

Registre que os sensores foram instalados apenas em parte da frota, que a integração dos alertas ainda está incompleta e que existe um bloqueio ligado à cobertura móvel em regiões remotas.

Inclua checkpoint, fato, risco, hipótese e próxima ação.

### Fase 5 — Revisão e decisão vigente

Registre nova evidência mostrando redução de desvios de temperatura nas rotas monitoradas, mas ausência de dados suficientes nas rotas sem cobertura.

Registre a decisão vigente, o que permanece pendente, o que foi descartado e qual é o próximo experimento operacional.

## Requisitos de memória

Use substantivamente os oito tipos:

- Fact
- Decision
- Hypothesis
- Evidence
- Learning
- Episode
- Checkpoint
- Document

Crie entre 22 e 30 memórias e pelo menos 28 relações.

## Avaliação

Crie o gabarito antes da primeira avaliação final e registre isso de forma verificável.

Produza no mínimo 24 consultas:

- 14 consultas principais;
- 10 paráfrases adversariais.

As consultas devem cobrir:

1. decisão vigente;
2. decisão anterior;
3. causa do incidente;
4. evidência do desvio;
5. aprendizado produzido;
6. risco ainda aberto;
7. bloqueio atual;
8. próxima ação;
9. documento de arquitetura;
10. checkpoint mais recente;
11. item descartado ou substituído;
12. conflito ou supersessão;
13. consulta de ausência verdadeira;
14. consulta com vocabulário não literal, mas semanticamente próximo;
15. consulta histórica explícita;
16. consulta atual explícita.

Inclua pelo menos quatro consultas de ausência, sendo duas com uma palavra lexical coincidente para testar falso positivo.

## Critérios mínimos

O experimento só pode terminar como `EXPERIMENT_02_PASSED` se todos os critérios funcionais abaixo forem satisfeitos:

- decisão vigente supera a substituída em consultas atuais;
- decisão antiga aparece no top-3 em consultas históricas;
- risco e bloqueio aparecem no top-3 quando explicitamente solicitados;
- próxima ação aparece no top-3;
- consultas de ausência retornam vazio ou qualidade `absent`;
- relações isoladas não fabricam relevância;
- fake source rate = 0;
- os 128 testes atuais continuam passando;
- Hit@1 global >= 0.50;
- Hit@3 global >= 0.75;
- nenhuma consulta ou gabarito é alterado depois de ver o resultado final.

## Integridade

É proibido:

- alterar o motor;
- alterar pesos ou thresholds;
- adicionar hardcodes para Boreal, vacina, sensor, clínica, rota ou IDs do experimento;
- reutilizar queries ou gold answers do Projeto Atlas;
- consultar holdouts reservados;
- corrigir o gabarito depois da execução;
- remover consultas difíceis para melhorar métricas.

## Artefatos obrigatórios

Crie:

- `experiments/exp-02/README.md`
- `experiments/exp-02/queries.json`
- `experiments/exp-02/gold_answers.json`
- scripts de população por fase;
- `experiments/exp-02/run_experiment.py`
- snapshots após cada fase;
- `experiments/exp-02/RAW_RESULTS/`
- `experiments/exp-02/REPORT.md`

O relatório deve incluir resultados por consulta, métricas agregadas, falhas, análise causal, limitações e comparação com o Experimento 01.

## Verificação final

Antes do push:

1. rode os 128 testes;
2. execute o experimento três vezes;
3. confirme determinismo;
4. confirme que o gabarito precede a avaliação;
5. confirme que todos os oito tipos foram usados;
6. confirme ausência de alterações no motor;
7. faça commit e push da branch;
8. abra PR draft para `main`;
9. não faça merge, tag ou release.

## Estados finais permitidos

Declare exatamente um:

- `EXPERIMENT_02_PASSED`
- `EXPERIMENT_02_FAILED`
- `EXPERIMENT_02_INCONCLUSIVE`
