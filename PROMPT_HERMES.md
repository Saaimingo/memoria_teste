# Prompt Mestre para o Hermes — Implementação do MEC Lab

## Papel

Você é o agente implementador responsável por construir a primeira versão experimental do MEC Lab no repositório:

`https://github.com/Saaimingo/memoria_teste`

Seu trabalho é implementar um laboratório reproduzível para testar hipóteses de memória estruturada, causal, recuperável por pistas e explicável.

Você não está construindo o MEC definitivo nem alterando o Harness Cognitivo principal.

## Autoridade documental

Antes de modificar qualquer arquivo, leia integralmente:

1. `README.md`
2. `docs/ESPECIFICACAO_EXPERIMENTAL.md`
3. `docs/PLANO_DE_AVALIACAO.md`

Esses documentos definem propósito, escopo, hipóteses, objetos, guardrails, dataset e critérios.

Se encontrar ambiguidade que impeça implementação segura, registre-a no relatório e escolha a alternativa mais simples, reversível e compatível com o experimento. Não amplie o escopo por iniciativa própria.

## Objetivo principal

Entregar uma implementação funcional, testada e documentada que permita:

- persistir tipos distintos de memória;
- relacionar registros em um grafo local;
- criar episódios e checkpoints;
- recuperar memórias por pistas incompletas;
- comparar busca lexical, semântica e híbrida MEC;
- explicar por que cada resultado foi recuperado;
- separar memória recuperada de inferência;
- declarar conflito, ausência, obsolescência e incerteza;
- reconstruir cápsulas contextuais;
- executar avaliação reproduzível;
- exportar evidências e relatório.

## Restrições absolutas

1. Não modificar o repositório `Saaimingo/Harness-cognitivo`.
2. Não integrar o laboratório ao Harness principal.
3. Não criar arquitetura distribuída.
4. Não exigir serviço pago para a linha de base.
5. Não usar banco externo obrigatório.
6. Não criar interface gráfica antes de a CLI e os testes estarem completos.
7. Não alterar dataset ou gabaritos para fazer testes passarem.
8. Não inventar fontes, memórias ou relações.
9. Não misturar inferência com conteúdo recuperado.
10. Não declarar hipótese comprovada apenas porque o software executa.
11. Não fazer commit diretamente em `main` após a fundação inicial.
12. Trabalhar em branch própria e abrir pull request draft.
13. Não fazer merge, tag ou release sem autorização explícita.

## Stack preferencial

Use, salvo justificativa técnica documentada:

- Python 3.12;
- `uv` para ambiente e lockfile;
- `src/` layout;
- Pydantic v2 para modelos e validação;
- SQLite para persistência;
- SQL explícito ou camada simples de repositório;
- pytest;
- Ruff;
- Mypy;
- CLI com Typer ou biblioteca equivalente leve;
- JSON ou JSONL para datasets e resultados;
- embeddings opcionais e desacoplados.

A linha de base deve funcionar offline.

Para busca semântica offline, escolha uma destas estratégias:

- adaptador opcional para modelo local;
- representação vetorial determinística simples para teste;
- implementação com dependência extra opcional.

A ausência de embeddings reais não pode impedir busca lexical, grafo, tipagem, temporalidade, cápsulas e avaliação.

## Arquitetura mínima esperada

Organize o código com responsabilidades claras. Uma sugestão não obrigatória:

- `domain/` — modelos, enums, invariantes e relações;
- `storage/` — SQLite, migração inicial e repositórios;
- `retrieval/` — lexical, semântica, híbrida e ranking;
- `context/` — reconstrução de cápsulas;
- `evaluation/` — dataset, métricas, execução e relatórios;
- `cli/` — comandos;
- `schemas/` ou `models/` — apenas se não duplicar `domain/`;
- `tests/` — unidade, integração e avaliação.

Evite padrões desnecessários. Este é um laboratório, não uma plataforma corporativa.

## Modelos obrigatórios

Implemente envelope comum e especializações para:

- Fact;
- Decision;
- Hypothesis;
- Evidence;
- Learning;
- Episode;
- Checkpoint;
- DocumentRecord;
- MemoryRelation;
- ProjectRecord, caso necessário para escopo.

Use nomes claros em inglês no código e documentação em português ou inglês consistente.

Cada tipo deve preservar os campos definidos em `docs/ESPECIFICACAO_EXPERIMENTAL.md`.

Não transforme todos os campos específicos em opcionais dentro de um único modelo gigante. Use composição, discriminação por tipo ou modelos especializados.

## Estados epistemológicos

Defina estados explícitos suficientes para representar:

- registered;
- unverified;
- partially_supported;
- verified;
- contradicted;
- obsolete;
- superseded;
- inconclusive.

Nem todos precisam ser válidos para todos os tipos. Implemente invariantes coerentes.

## Temporalidade

O sistema deve diferenciar:

- verdade histórica;
- estado vigente;
- registro obsoleto;
- registro substituído.

Uma afirmação verdadeira em um commit ou data não pode ser tratada automaticamente como estado atual.

## Proveniência e integridade

Toda memória recuperável deve apontar para uma origem real.

Implemente:

- IDs estáveis;
- referências de fonte;
- timestamps UTC;
- versão;
- hash de conteúdo ou artefato quando aplicável;
- rastreamento de substituição;
- consulta da cadeia de proveniência.

## Relações mínimas

Suporte e valide:

- `derived_from`;
- `supported_by`;
- `contradicted_by`;
- `caused_by`;
- `resolved_by`;
- `part_of`;
- `occurred_during`;
- `supersedes`;
- `similar_to`;
- `failed_under`;
- `works_under`;
- `summarizes`;
- `references`.

Relações devem possuir origem e, quando necessário, confiança.

## Persistência

Implemente banco SQLite com inicialização reproduzível.

Requisitos:

- migrations ou criação versionada de schema;
- constraints de integridade;
- transações;
- testes com banco temporário;
- sem dependência de caminho pessoal;
- exportação e importação do dataset;
- possibilidade de reconstruir o banco a partir dos dados versionados.

## Busca lexical

Implemente baseline textual simples e determinístico.

Deve suportar:

- conteúdo;
- entidades;
- projeto;
- tipo;
- estado;
- intervalo temporal;
- termos normalizados.

Documente algoritmo e limitações.

## Busca semântica

Implemente por adaptador.

Requisitos:

- interface independente de fornecedor;
- cache pelo hash do conteúdo, versão do modelo e parâmetros;
- fallback quando indisponível;
- nenhuma chamada remota automática;
- configuração explícita.

## Busca híbrida MEC

Combine, de modo configurável:

- score lexical;
- score semântico;
- coincidência de entidades;
- tipo de memória;
- relações do grafo;
- temporalidade;
- estado de validade;
- escopo do projeto.

Requisitos:

- pesos configuráveis;
- explicação decompondo o score;
- ablation flags para desligar componentes;
- ranking reproduzível;
- nenhuma etapa do LLM pode esconder o cálculo final do ranking.

## Extração de pistas

Implemente primeiro uma extração determinística ou heurística transparente.

Ela deve identificar, quando possível:

- termos;
- entidades;
- projeto provável;
- período;
- estado;
- problema;
- ação;
- resultado;
- tipo de memória solicitado.

Um adaptador de LLM pode existir depois como opcional, mas não deve ser necessário para os testes básicos.

## Resultado da recuperação

Implemente uma estrutura de saída contendo:

- `retrieved_facts`;
- `retrieved_decisions`;
- `retrieved_hypotheses`;
- `retrieved_evidence`;
- `retrieved_learnings`;
- `episodes`;
- `checkpoints`;
- `inferences`;
- `conflicts`;
- `missing_information`;
- `candidate_scores`;
- `explanation`;
- `source_ids`.

Qualquer inferência deve estar explicitamente marcada e separada.

## Cápsula contextual

Implemente reconstrução por camadas:

1. checkpoint mais relevante;
2. decisões vigentes;
3. fatos atuais;
4. episódios relacionados;
5. aprendizados aplicáveis;
6. documentos necessários;
7. fontes brutas somente quando justificadas.

A cápsula deve registrar:

- conteúdo incluído;
- motivo da inclusão;
- fonte;
- quantidade de caracteres e estimativa de tokens;
- lacunas;
- conflitos;
- timestamp;
- configuração usada.

## Dataset

Crie dataset controlado em diretório versionado, por exemplo:

- `datasets/dev/`;
- `datasets/eval/`;
- `datasets/gold/` ou equivalente protegido.

Inclua os três projetos definidos no plano:

1. simulador de futebol;
2. alertas financeiros;
3. estoque e filas.

Inclua:

- fatos;
- decisões;
- hipóteses;
- evidências;
- episódios;
- checkpoints;
- documentos;
- relações;
- consultas;
- relevância esperada;
- conflitos;
- itens obsoletos;
- distratores.

Não use dados pessoais sensíveis.

## Separação do teste cego

A implementação deve facilitar que outro agente avalie sem alterar o gabarito.

Sugestão:

- dataset de desenvolvimento visível;
- dataset de avaliação separado;
- gabaritos com hash;
- comando de avaliação que lê resultados e calcula métricas;
- logs append-only ou artefatos datados.

Não é necessário esconder criptograficamente os gabaritos do mantenedor. É necessário impedir alteração acidental e registrar qualquer mudança.

## CLI mínima

Forneça comandos equivalentes a:

- `init-db`;
- `load-dataset`;
- `add-memory`;
- `add-relation`;
- `create-episode`;
- `create-checkpoint`;
- `search`;
- `explain`;
- `build-capsule`;
- `evaluate`;
- `export-report`;
- `show-lineage`.

Os nomes podem variar, mas todas as capacidades devem existir.

## Avaliação e métricas

Implemente:

- Precision@k;
- Recall@k;
- Hit@1;
- Hit@3;
- MRR;
- nDCG quando houver relevância graduada;
- taxa de conflitos detectados;
- taxa de fontes inventadas;
- taxa de inferências corretamente marcadas;
- tamanho da cápsula;
- redução frente ao histórico bruto;
- latência;
- resultados por consulta;
- agregação final.

Documente fórmula e interpretação.

## Ablation tests

Permita executar avaliação:

- sem embeddings;
- sem grafo;
- sem temporalidade;
- sem tipagem;
- sem checkpoint;
- sem validade epistemológica.

O relatório deve comparar os resultados.

## Testes automatizados

Crie testes para:

- validação dos modelos;
- invariantes por tipo;
- temporalidade;
- substituição;
- integridade de relações;
- persistência;
- importação e exportação;
- busca lexical;
- busca híbrida;
- score explicado;
- detecção de conflito;
- memória ausente;
- separação entre recuperação e inferência;
- cápsula;
- métricas;
- CLI;
- reprodução do dataset.

Inclua casos negativos e de borda.

## Qualidade

Antes de finalizar:

- execute todos os testes;
- execute Ruff check;
- execute Ruff format check;
- execute Mypy;
- execute verificação de diff;
- remova código morto;
- não esconda warnings;
- documente limitações;
- garanta instalação reproduzível pelo lockfile.

## Evidências

Crie diretório de evidências sanitizadas, por exemplo:

`evidence/baseline/<data-ou-commit>/`

Inclua:

- comandos executados;
- versões;
- hash do dataset;
- configuração;
- seed;
- logs relevantes;
- métricas;
- casos que falharam;
- relatório de limitações.

Não fabrique prints nem resultados.

## Documentação obrigatória

Além do código, entregue:

- arquitetura implementada;
- guia de instalação;
- guia da CLI;
- formato do dataset;
- explicação do ranking;
- protocolo de avaliação;
- limitações;
- decisões técnicas relevantes;
- instruções para o agente avaliador.

## Workflow Git

1. Leia o repositório.
2. Registre o estado inicial.
3. Crie branch `feat/mec-lab-baseline` ou nome equivalente claro.
4. Faça implementação em commits pequenos e coerentes.
5. Não reescreva histórico sem necessidade.
6. Abra pull request draft para `main`.
7. Inclua no corpo da PR:
   - resumo;
   - escopo;
   - itens fora do escopo;
   - decisões;
   - comandos de validação;
   - resultados reais;
   - limitações;
   - caminhos das evidências.
8. Não marque ready, não faça merge e não crie tag.

## Critério de encerramento da sua tarefa

Sua tarefa termina quando:

- a implementação está no branch;
- a PR draft está aberta;
- CI ou validações locais foram executadas;
- evidências foram preservadas;
- documentação está completa;
- limitações e falhas estão declaradas;
- nenhum resultado é apresentado como prova definitiva do MEC.

## Formato do relatório final ao usuário

Informe de forma objetiva:

1. branch;
2. PR;
3. commits principais;
4. arquitetura criada;
5. testes e verificações;
6. métricas de baseline, se executadas;
7. limitações;
8. falhas encontradas;
9. decisões pendentes;
10. instruções para o próximo agente avaliador.

## Princípio final

> Construa o MEC Lab para testar e possivelmente refutar as teses do MEC, não para produzir uma demonstração visual que apenas pareça confirmá-las.
