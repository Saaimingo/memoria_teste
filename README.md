# memoria_teste — MEC Lab

Laboratório experimental para testar, medir e falsificar hipóteses do MEC antes de sua incorporação ao Harness Cognitivo.

## Propósito

Este repositório nasceu como ambiente isolado para responder, por meio de software e evidências, se uma memória estruturada consegue:

- distinguir fato, decisão, hipótese, evidência, aprendizado, documento, episódio e checkpoint;
- recuperar projetos e experiências a partir de pistas incompletas;
- reconstruir contexto sem carregar conversas inteiras;
- explicar por que determinada memória foi recuperada;
- declarar incerteza, conflito e ausência de informação;
- preservar proveniência, causalidade e temporalidade;
- reduzir contexto, latência e tokens sem degradar a qualidade da retomada.

## Regra central

> O laboratório deve descobrir onde as teses do MEC funcionam, onde falham e quais condições limitam sua aplicação.

Não deve produzir uma demonstração fabricada para confirmar a hipótese.

## Estado atual

O MEC atingiu o marco **R4.1 — memória operacional estruturada aprovada para integração controlada**.

O resultado validado localmente inclui:

- ingestão determinística de projetos;
- SQLite persistente;
- proveniência;
- arquivos, símbolos, comandos CLI e histórico Git;
- serial, MAC, protocolo, ticket, caminho e SHA;
- quatro estados de recuperação;
- até três esclarecimentos;
- ausência confiável;
- restrição negativa para identificador inexistente;
- idempotência integral;
- compatibilidade com o R3;
- 310 testes passando;
- fake source rate de 0% na validação manual.

Commit local aprovado:

`edd3c342f5962535b81bb55c35a9d70f001adf33`

**Importante:** a cadeia R4.1 ainda precisa ser publicada no GitHub. A documentação desta branch registra o estado técnico validado, mas não afirma que o código local já está presente na `main` remota.

## Documentos principais

- [`docs/ESPECIFICACAO_EXPERIMENTAL.md`](docs/ESPECIFICACAO_EXPERIMENTAL.md) — teses, arquitetura mínima e critérios originais.
- [`docs/PLANO_DE_AVALIACAO.md`](docs/PLANO_DE_AVALIACAO.md) — dataset, cenários, métricas e avaliação.
- [`docs/STATUS_MEC_R41.md`](docs/STATUS_MEC_R41.md) — estado técnico, contrato público, evidências e limitações do R4.1.
- [`docs/ADR-0002-HERMES_AGENT_COMO_BASE.md`](docs/ADR-0002-HERMES_AGENT_COMO_BASE.md) — decisão de usar um fork controlado do Hermes Agent como fundação operacional do Harness.
- [`docs/ROADMAP_POS_MEC_R41.md`](docs/ROADMAP_POS_MEC_R41.md) — sequência de consolidação, fork, localização `pt-BR`, plugin MEC e retomada do Harness.
- [`PROTOCOL_ISOLATED_ORCHESTRATION.md`](PROTOCOL_ISOLATED_ORCHESTRATION.md) — protocolo experimental criado após falhas de coordenação observadas.
- [`PROMPT_HERMES.md`](PROMPT_HERMES.md) — ordem histórica de implementação do laboratório.

## Contrato de recuperação R4.1

A interface assistida retorna exatamente um destes estados:

- `MEMORY_CONFIRMED`
- `AMBIGUOUS_CANDIDATES`
- `CLARIFICATION_REQUIRED`
- `MEMORY_NOT_FOUND`

O MEC não deve converter uma candidata fraca em lembrança confirmada apenas para produzir resposta.

Quando uma consulta contém identificador explícito inexistente, texto ou semântica não podem substituir a identidade ausente.

## Relação com o Harness Cognitivo

O desenvolvimento isolado do MEC deve ser pausado no R4.1 após a consolidação remota.

O próximo movimento arquitetural é:

1. publicar e revisar o MEC R4.1;
2. criar um fork controlado de `NousResearch/hermes-agent`;
3. preservar o upstream e a licença MIT;
4. localizar a experiência humana do Desktop para `pt-BR`;
5. preservar código, comandos, símbolos e termos técnicos em inglês;
6. integrar o MEC como Memory Provider Plugin;
7. validar o circuito real com um provider suportado;
8. retomar as demais fases do Harness Cognitivo.

O Hermes será reutilizado para capacidades operacionais comuns. O diferencial próprio continuará concentrado em memória, cognição, governança, rastreabilidade, auditoria e aprendizagem operacional.

## Próxima ação permitida

> Publicar a cadeia local do MEC R4.1, abrir Pull Request, executar CI remota e revisar o diff antes do merge.
