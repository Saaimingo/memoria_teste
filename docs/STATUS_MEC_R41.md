# Estado Técnico — MEC R4.1

**Data do registro:** 2026-07-27  
**Estado arquitetural:** aprovado para integração controlada  
**Veredito canônico:** `MEC_R41_OPERATIONAL_RETRIEVAL_APPROVED`

## 1. Aviso de rastreabilidade

O código aprovado do MEC R4.1 foi produzido e validado no repositório local, no commit:

`edd3c342f5962535b81bb55c35a9d70f001adf33`

Mensagem:

`fix(mec): enforce identifier absence and full ingestion idempotency`

No momento deste registro, esse commit ainda não está publicado no repositório remoto. Este documento registra o resultado técnico validado, mas não substitui a publicação da cadeia de commits, a execução da CI remota e a revisão do diff antes do merge na `main`.

## 2. Conclusão do ciclo experimental

O MEC deixou de ser apenas uma hipótese documental. A versão R4.1 demonstrou uma fatia operacional capaz de:

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
- manter compatibilidade com o `HybridRetriever` R3.

## 3. Contrato público de recuperação

A recuperação assistida retorna exatamente um dos seguintes estados:

- `MEMORY_CONFIRMED`
- `AMBIGUOUS_CANDIDATES`
- `CLARIFICATION_REQUIRED`
- `MEMORY_NOT_FOUND`

### `MEMORY_CONFIRMED`

Existe uma candidata suficientemente forte e consistente com os identificadores, metadados, relações, vigência e demais sinais disponíveis.

### `AMBIGUOUS_CANDIDATES`

Existem duas ou mais entidades realmente distintas e plausíveis. Segmentos irmãos do mesmo arquivo ou entidade devem ser agrupados antes da classificação.

### `CLARIFICATION_REQUIRED`

Há indícios de memória relacionada, mas falta uma pista discriminatória. O ciclo pode solicitar no máximo três esclarecimentos.

### `MEMORY_NOT_FOUND`

Nenhuma lembrança confiável foi localizada com os parâmetros fornecidos. O estado não afirma que a memória é absolutamente inexistente; afirma que não há evidência suficiente para tratá-la como lembrança confirmada.

Após três esclarecimentos insuficientes, o encerramento em `MEMORY_NOT_FOUND` é obrigatório.

## 4. Restrição negativa de identidade

Quando uma consulta contém um identificador explícito reconhecido, a identidade tem precedência sobre o score textual.

Comportamento obrigatório:

- identificador único existente: pode produzir `MEMORY_CONFIRMED`;
- identificador com várias correspondências legítimas: `AMBIGUOUS_CANDIDATES`;
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

A validação final foi executada três vezes sobre um banco novo.

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

## 7. Evidência de testes

Resultado canônico final:

- 271 testes anteriores preservados;
- 39 testes novos;
- 310 testes totais;
- 310 aprovados;
- 0 falhas;
- 0 erros.

A suíte completa foi executada duas vezes no commit final:

- `310 passed in 74.41s`;
- `310 passed in 72.37s`.

Uma verificação ad hoc adicional executou 13 checks focados e todos passaram. Essa verificação é evidência complementar e não deve ser somada ao total da suíte canônica.

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

No futuro, essa decisão pode evoluir para níveis explícitos de autoridade, como:

- produção;
- documentação;
- configuração;
- histórico Git;
- teste;
- exemplo;
- evidência rejeitada.

## 10. Limitações conhecidas

- formatos de identificador não reconhecidos pelo extrator não acionam a restrição negativa;
- hexadecimal curto sem contexto Git não é tratado como SHA;
- nomes parciais como `init.py` permanecem ambíguos quando existem entidades distintas;
- conteúdo puramente textual de testes não é autoridade operacional;
- a memória pessoal progressiva ainda depende da integração com o Harness;
- os pesos e thresholds devem ser observados em uso real antes de qualquer recalibração;
- o MEC não é, nesta versão, uma memória universal para qualquer conversa humana.

## 11. Cadeia local do R4

Commits relevantes produzidos localmente:

1. `d10a6912c775cdf32e4316edb6c7a2d9428554ef` — recuperação estruturada e assistida;
2. `0d3833fc50aa7004c388de3495f97e099d844259` — integração com a interface pública;
3. `353da0a827c5edadf649a757be1065b3d49b17ff` — ingestão operacional do projeto;
4. `d290a469d33f3dc02e5f134e1f0b45c57d0c121c` — recuperação simbólica e histórico Git;
5. `edd3c342f5962535b81bb55c35a9d70f001adf33` — idempotência integral e ausência de identificador.

## 12. Decisão de saída

O desenvolvimento isolado do MEC deve ser pausado no marco R4.1.

O MEC passa a ser um componente versionado destinado a integração controlada com o Harness Cognitivo. Novas alterações no núcleo devem ser motivadas por:

- defeito observado na integração real;
- necessidade comprovada por uso operacional;
- evolução formal de versão.

Antes da integração, ainda são obrigatórios:

1. publicar a cadeia local de commits;
2. abrir Pull Request;
3. executar CI remota;
4. revisar o diff acumulado;
5. confirmar que artefatos experimentais rejeitados não foram promovidos;
6. fazer merge apenas com evidência remota limpa;
7. criar uma tag de marco após o merge.
