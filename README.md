# memoria_teste — MEC Lab

Laboratório experimental para testar, medir e falsificar hipóteses do MEC (Memória Estruturada e Causal) antes de qualquer incorporação ao Harness Cognitivo principal.

## Propósito

Este repositório não é o MEC definitivo e não faz parte do código produtivo do Harness Cognitivo.

Ele existe para responder, por meio de software e evidências, se uma memória estruturada consegue:

- distinguir fato, decisão, hipótese, evidência, aprendizado, documento, episódio e checkpoint;
- recuperar projetos e experiências a partir de pistas incompletas;
- reconstruir contexto sem carregar conversas inteiras;
- explicar por que determinada memória foi recuperada;
- declarar incerteza, conflito e ausência de informação;
- preservar proveniência, causalidade e temporalidade;
- reduzir contexto, latência e tokens sem degradar a qualidade da retomada.

## Regra central

> O laboratório deve tentar descobrir onde as teses do MEC funcionam, onde falham e quais condições limitam sua aplicação.

Não deve produzir uma demonstração fabricada para confirmar a hipótese.

## Documentos

- [`docs/ESPECIFICACAO_EXPERIMENTAL.md`](docs/ESPECIFICACAO_EXPERIMENTAL.md) — escopo, teses, arquitetura mínima e critérios.
- [`docs/PLANO_DE_AVALIACAO.md`](docs/PLANO_DE_AVALIACAO.md) — dataset, cenários, métricas e teste cego.
- [`PROMPT_HERMES.md`](PROMPT_HERMES.md) — ordem completa para implementação pelo Hermes.

## Estado

Fundação documental criada. Implementação ainda não iniciada.

## Relação com o Harness Cognitivo

Este laboratório é isolado. Resultados somente poderão voltar ao Harness principal depois de:

1. execução reproduzível;
2. evidências preservadas;
3. análise independente;
4. decisão arquitetural explícita.
