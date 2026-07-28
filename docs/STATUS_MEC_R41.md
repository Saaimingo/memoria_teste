# Estado Técnico — MEC R4.1

**Data do fechamento:** 2026-07-28  
**Estado arquitetural:** integrado à `main` e aprovado como subsistema operacional  
**Veredito canônico:** `MEC_R41_OPERATIONAL_RETRIEVAL_APPROVED`

## 1. Rastreabilidade remota

Commit final da cadeia R4.1:

`9830d35d1f8669ffd351cb3f3eab4df1e8f36a64`

Mensagem:

`fix(mec): declare yaml dependency and harden windows test`

Pull Request de código:

`#22 — feat(mec): entregar memória operacional MEC R4.1`

Merge na `main`:

`4b04963b73e5af3eb880db7dd33a53510d09cf93`

A cadeia foi publicada, revisada, validada em CI e integrada preservando os sete commits do ciclo R4/R4.1.

## 2. Conclusão do ciclo experimental

O MEC deixou de ser apenas hipótese documental. A versão R4.1 demonstrou uma fatia operacional capaz de:

- ingerir projetos reais de forma determinística;
- persistir memórias e relações em SQLite;
- preservar proveniência por arquivo, linha, commit e fingerprint;
- recuperar arquivos, módulos, classes, funções, métodos, comandos CLI e histórico Git;
- pesquisar serial, MAC, protocolo, ticket, caminho e SHA de commit;
- separar identidade exata de mera semelhança textual;
- reconhecer ambiguidade legítima;
- solicitar esclarecimentos limitados;
- encerrar sem memória confiável;
- impedir que texto genérico substitua um identificador explícito inexistente;
- repetir a ingestão sem alterar o estado persistido;
- manter compatibilidade com o `HybridRetriever` R3;
- executar a suíte completa sem dependência de bancos locais ou caminhos específicos da máquina.

## 3. Contrato público de recuperação

A recuperação assistida retorna exatamente um dos seguintes estados:

- `MEMORY_CONFIRMED`
- `AMBIGUOUS_CANDIDATES`
- `CLARIFICATION_REQUIRED`
- `MEMORY_NOT_FOUND`

### `MEMORY_CONFIRMED`

Existe uma candidata suficientemente forte e consistente com identificadores, metadados, relações, vigência e demais sinais disponíveis.

### `AMBIGUOUS_CANDIDATES`

Existem duas ou mais entidades realmente distintas e plausíveis. Segmentos irmãos do mesmo arquivo são agrupados antes da classificação.

### `CLARIFICATION_REQUIRED`

Há indícios de memória relacionada, mas falta uma pista discriminatória. O ciclo pode solicitar no máximo três esclarecimentos.

### `MEMORY_NOT_FOUND`

Nenhuma lembrança confiável foi localizada com os parâmetros fornecidos. O estado não afirma inexistência absoluta; afirma insuficiência de evidência para tratar algo como lembrança confirmada.

Após três esclarecimentos insuficientes, o encerramento em `MEMORY_NOT_FOUND` é obrigatório.

## 4. Restrição negativa de identidade

Quando uma consulta contém um identificador explícito reconhecido, a identidade tem precedência sobre o score textual.

Comportamento obrigatório:

- identificador único existente: pode produzir `MEMORY_CONFIRMED`;
- várias correspondências legítimas: `AMBIGUOUS_CANDIDATES`;
- identificador parcial plausível: ambiguidade ou esclarecimento;
- identificador explícito inexistente: `MEMORY_NOT_FOUND`;
- texto, semântica e relações não podem substituir uma identidade inexistente.

A saída diagnóstica inclui:

- `identifier_constraint_applied`;
- `identifier_constraint_status`;
- `identifier_matches`;
- `identifier_failure_reason`.

Estados diagnósticos:

- `NO_EXPLICIT_IDENTIFIER`;
- `IDENTIFIER_MATCHED_UNIQUE`;
- `IDENTIFIER_MATCHED_MULTIPLE`;
- `IDENTIFIER_PARTIAL`;
- `IDENTIFIER_NOT_FOUND`.

## 5. Pipeline operacional de ingestão

O pipeline aprovado suporta:

- Markdown segmentado por títulos e seções;
- Python segmentado por AST;
- TOML, YAML e JSON segmentados por estruturas principais;
- `PyYAML>=6.0` declarado como dependência de produção;
- símbolos de código e nomes qualificados;
- comandos e opções CLI detectáveis estaticamente;
- snapshot do projeto;
- histórico Git;
- manifesto pré-ingestão;
- proteção básica contra segredos;
- IDs e relações determinísticos;
- proveniência completa;
- reabertura do banco persistente;
- ingestão idempotente.

A ingestão Git utiliza duas fases:

1. criação ou reconhecimento de todas as memórias de commits;
2. criação das relações entre commits somente depois que todos os destinos existem.

Essa ordem elimina relações tardias causadas pela ordem do `git log`.

## 6. Evidência de idempotência

A validação final foi executada três vezes sobre banco novo.

Primeira execução:

- 1.033 memórias criadas;
- 961 relações criadas.

Segunda e terceira execuções:

- 0 memórias novas;
- 0 relações novas;
- 0 atualizações;
- mesmos totais;
- mesmos IDs;
- mesmo resumo canônico.

SHA-256 canônico nas três execuções:

`1e9c8b1c0962fbb6552757177e2207c02292951fad6fc89a04ca1ec2e235ff58`

O hash representa o estado canônico ordenado de memórias, fingerprints, tipos e relações. Não representa os bytes brutos do arquivo SQLite.

## 7. Evidência de testes e portabilidade

Resultado final da suíte:

- 313 testes totais;
- 313 aprovados;
- 0 falhas;
- 0 skips;
- 0 xfails.

CI remota:

- workflow: `CI`;
- run aprovado: `30318817937`;
- Python 3.12;
- Ubuntu: 313 testes, `git diff --check` e `compileall` aprovados;
- Windows: 313 testes, `git diff --check` e `compileall` aprovados.

A fixture portátil:

- cria projeto temporário;
- inicializa Git real com commits controlados;
- gera SQLite temporário;
- executa o pipeline real;
- remove os artefatos ao final;
- não depende de `D:\memoria_teste` nem de bancos piloto locais.

## 8. Evidência operacional

Consultas manuais confirmaram:

- SHA completo existente;
- prefixo único existente;
- SHA inexistente;
- protocolo inexistente;
- serial inexistente;
- MAC inexistente;
- caminho inexistente;
- recuperação de `ClarificationCycle`;
- recuperação de `AssistedRetriever`;
- ambiguidade real entre arquivos `init.py` distintos;
- ausência real de assunto não registrado.

Resultado manual final:

- 13 consultas corretas em 13;
- 15 fontes retornadas;
- 0 fontes inexistentes;
- fake source rate de 0%.

## 9. Autoridade de fontes de teste

Conteúdo encontrado exclusivamente em `tests/` não possui autoridade operacional por mera coincidência textual.

Arquivos de teste continuam recuperáveis por:

- caminho;
- símbolo;
- comando CLI;
- identificador explícito.

Essa regra evita que frases criadas para testar ausência se tornem falsas evidências de presença no banco operacional.

## 10. Limitações conhecidas

- formatos de identificador não reconhecidos pelo extrator não acionam a restrição negativa;
- hexadecimal curto sem contexto Git não é tratado como SHA;
- nomes parciais como `init.py` permanecem ambíguos quando existem entidades distintas;
- conteúdo puramente textual de testes não é autoridade operacional;
- o hash de idempotência representa o resumo canônico, não bytes brutos do SQLite;
- a memória pessoal progressiva ainda depende da integração com o Harness;
- pesos e thresholds devem ser observados em uso real antes de qualquer recalibração;
- o MEC não é, nesta versão, memória universal para qualquer conversa humana.

## 11. Cadeia R4/R4.1 integrada

1. `d10a6912c775cdf32e4316edb6c7a2d9428554ef` — recuperação estruturada e assistida;
2. `0d3833fc50aa7004c388de3495f97e099d844259` — integração com a interface pública;
3. `353da0a827c5edadf649a757be1065b3d49b17ff` — ingestão operacional;
4. `d290a469d33f3dc02e5f134e1f0b45c57d0c121c` — recuperação simbólica e histórico Git;
5. `edd3c342f5962535b81bb55c35a9d70f001adf33` — idempotência integral e ausência de identificador;
6. `b285b2ef5b6ec0bc97cadd3a8b7c9d160a15bd16` — validação portátil e reproduzível;
7. `9830d35d1f8669ffd351cb3f3eab4df1e8f36a64` — dependência YAML e robustez no Windows.

## 12. Decisão de saída

O desenvolvimento isolado do MEC fica pausado no marco R4.1.

O MEC passa a ser componente versionado destinado à integração controlada com o Harness Cognitivo. Novas alterações no núcleo devem ser motivadas por:

- defeito observado na integração real;
- necessidade comprovada por uso operacional;
- evolução formal de versão.

Próximo marco:

`HERMES_FORK_BASELINE_APPROVED`

Próxima ação:

> criar o fork controlado do Hermes Agent, registrar o commit-base e iniciar o spike de localização nativa `pt-BR`.