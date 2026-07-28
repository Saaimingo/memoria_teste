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

O MEC atingiu o marco **R4.1 — memória operacional estruturada aprovada e integrada à `main`**.

A versão consolidada inclui:

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
- fixture operacional portátil;
- `PyYAML>=6.0` como dependência de produção;
- CI em Python 3.12 no Ubuntu e Windows;
- 313 testes passando em ambos os sistemas;
- zero falhas, zero skips e zero xfails;
- fake source rate de 0% na validação manual.

Commit final da cadeia R4.1:

`9830d35d1f8669ffd351cb3f3eab4df1e8f36a64`

Merge na `main`:

`4b04963b73e5af3eb880db7dd33a53510d09cf93`

Pull Request de código:

`#22 — feat(mec): entregar memória operacional MEC R4.1`

## Documentos principais

- [`docs/ESPECIFICACAO_EXPERIMENTAL.md`](docs/ESPECIFICACAO_EXPERIMENTAL.md) — teses, arquitetura mínima e critérios originais.
- [`docs/PLANO_DE_AVALIACAO.md`](docs/PLANO_DE_AVALIACAO.md) — dataset, cenários, métricas e avaliação.
- [`docs/STATUS_MEC_R41.md`](docs/STATUS_MEC_R41.md) — estado técnico, contrato público, evidências e limitações do R4.1.
- [`docs/ADR-0002-HERMES_AGENT_COMO_BASE.md`](docs/ADR-0002-HERMES_AGENT_COMO_BASE.md) — decisão de usar um fork controlado do Hermes Agent como fundação operacional do Harness.
- [`docs/ROADMAP_POS_MEC_R41.md`](docs/ROADMAP_POS_MEC_R41.md) — sequência de fork, localização `pt-BR`, plugin MEC e retomada do Harness.
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

O desenvolvimento isolado do MEC fica pausado no R4.1.

O próximo movimento arquitetural é:

1. criar um fork controlado de `NousResearch/hermes-agent`;
2. preservar o upstream e a licença MIT;
3. registrar o commit-base do fork;
4. executar a suíte oficial relevante;
5. iniciar CLI e Desktop a partir do source checkout;
6. localizar a experiência humana do Desktop para `pt-BR`;
7. preservar código, comandos, símbolos e termos técnicos em inglês;
8. integrar o MEC como Memory Provider Plugin;
9. validar o circuito real com um provider suportado;
10. retomar as demais fases do Harness Cognitivo.

O Hermes será reutilizado para capacidades operacionais comuns. O diferencial próprio continuará concentrado em memória, cognição, governança, rastreabilidade, auditoria e aprendizagem operacional.

## Próxima ação permitida

> Criar o baseline do fork do Hermes Agent e iniciar o spike técnico de localização nativa `pt-BR`.