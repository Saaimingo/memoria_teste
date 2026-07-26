# Especificação Experimental — MEC Lab

## 1. Objetivo

Construir um software mínimo, isolado e reproduzível para testar as teses centrais do MEC antes de sua incorporação ao Harness Cognitivo.

O laboratório deve medir se uma memória estruturada e causal oferece vantagem real sobre:

1. busca textual simples;
2. busca semântica isolada;
3. resumo genérico de conversa;
4. carregamento integral do histórico.

## 2. Hipóteses a testar

### H1 — Tipagem epistemológica

Separar fato, decisão, hipótese, evidência, aprendizado, documento, episódio e checkpoint reduz confusão entre afirmação, prova, inferência e regra vigente.

### H2 — Recuperação por pistas

Pistas incompletas podem recuperar o projeto ou episódio correto sem exigir nome exato nem conversa integral.

### H3 — Explicabilidade

A recuperação pode declarar quais pistas, relações e fontes justificaram o resultado.

### H4 — Memória parcial honesta

O sistema consegue distinguir informação recuperada, inferida, ausente, contraditória ou obsoleta.

### H5 — Reconstrução contextual

Checkpoint, registros atômicos, episódios e documentos relevantes conseguem reconstruir contexto suficiente para retomar trabalho.

### H6 — Eficiência

A cápsula MEC pode consumir menos contexto, tempo e tokens que o histórico bruto, sem reduzir materialmente a qualidade da retomada.

### H7 — Analogia estrutural

Experiências de domínios diferentes podem ser relacionadas por padrões causais equivalentes, sem depender apenas de vocabulário semelhante.

H7 é avançada e não deve bloquear a primeira entrega.

## 3. Fora do escopo inicial

- integração com o Harness Cognitivo principal;
- alteração automática de políticas;
- autoaperfeiçoamento autônomo;
- memória pessoal sensível;
- ingestão de todas as conversas reais;
- interface visual sofisticada;
- operação em nuvem;
- múltiplos agentes autônomos;
- banco vetorial distribuído;
- escala de produção;
- alegações de consciência ou sentimento.

## 4. Unidade comum de memória

Cada registro deve possuir um envelope comum mínimo:

- `id`;
- `type`;
- `content`;
- `project_id` ou escopo;
- `source_refs`;
- `created_at`;
- `valid_from` e `valid_to`, quando aplicável;
- `status`;
- `confidence`;
- `entities`;
- `relations`;
- `version`;
- `supersedes` ou `superseded_by`, quando aplicável;
- `metadata` controlado.

Os campos específicos variam por tipo. Não criar um objeto monolítico com dezenas de campos obrigatórios para todos.

## 5. Tipos de memória

### 5.1 Fato

Afirmação válida em um escopo e tempo, sustentada por fonte ou observação.

Deve preservar:

- afirmação;
- escopo;
- temporalidade;
- fonte;
- evidência associada;
- situação atual: vigente, obsoleto, contradito ou substituído.

### 5.2 Decisão

Escolha autorizada entre alternativas.

Deve preservar:

- decisão;
- autoridade;
- alternativas;
- justificativa;
- consequências esperadas;
- vigência;
- critérios de revogação;
- decisão substituída.

### 5.3 Hipótese

Explicação ou proposta ainda não comprovada.

Deve preservar:

- observação de origem;
- previsão;
- condição de teste;
- critério de confirmação;
- critério de rejeição;
- risco;
- estado do experimento.

### 5.4 Evidência

Artefato ou observação que sustenta ou contradiz uma afirmação.

Deve preservar:

- tipo de evidência;
- localização;
- produtor;
- ambiente;
- timestamp;
- versão ou artefato avaliado;
- hash de integridade quando aplicável;
- afirmações sustentadas ou contraditas;
- limitações.

### 5.5 Aprendizado

Conclusão operacional derivada de um ou mais episódios e evidências.

Deve preservar:

- episódios de origem;
- evidências;
- condições em que funcionou;
- condições em que falhou;
- confiança;
- grau de generalização;
- estado: observado, recorrente, promovido ou normativo.

### 5.6 Episódio

Contêiner causal de uma experiência operacional delimitada.

Estrutura mínima:

> estado inicial → objetivo → plano → ações → observações → desvios → correções → resultado → consequências → aprendizado

### 5.7 Checkpoint

Projeção verificável do estado de um projeto em determinado momento.

Deve preservar:

- estado atual;
- última ação concluída;
- decisões vigentes;
- pendências;
- bloqueios;
- artefatos e versões;
- próxima ação permitida;
- riscos conhecidos;
- referências para aprofundamento.

### 5.8 Documento

Artefato composto que organiza múltiplos registros e pode ser normativo, informativo ou evidencial.

O documento não é a menor unidade da memória.

## 6. Níveis de organização

### Nível 1 — Registros atômicos

- fato;
- decisão;
- hipótese;
- evidência;
- aprendizado.

### Nível 2 — Estruturas de experiência

- episódio;
- checkpoint.

### Nível 3 — Artefatos compostos

- documento;
- conversa;
- código;
- relatório;
- log;
- anexo.

## 7. Relações mínimas do grafo

A primeira versão deve suportar relações tipadas como:

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

Relações devem ser consultáveis e explicáveis.

## 8. Recuperação por camadas

Ordem preferencial:

1. checkpoint;
2. registros atômicos;
3. episódios;
4. documentos;
5. fontes brutas.

A fonte bruta não deve ser carregada por padrão.

## 9. Fluxo de recuperação por pistas

1. receber consulta livre;
2. extrair pistas explícitas;
3. gerar candidatos;
4. pontuar candidatos por texto, semântica, entidades, relações, temporalidade e estado;
5. produzir explicação de ranking;
6. declarar conflitos e lacunas;
7. permitir confirmação do candidato;
8. montar cápsula contextual;
9. registrar quais memórias foram usadas.

## 10. Saída obrigatória da recuperação

A resposta deve separar claramente:

- `retrieved_facts`;
- `retrieved_decisions`;
- `retrieved_hypotheses`;
- `retrieved_evidence`;
- `inferences`;
- `conflicts`;
- `missing_information`;
- `candidate_scores`;
- `explanation`;
- `source_ids`.

Nunca misturar inferência com memória recuperada.

## 11. Estratégias comparadas

O laboratório deve oferecer, ao menos:

1. busca lexical;
2. busca semântica;
3. busca híbrida MEC.

A busca híbrida deve permitir ablação: desligar semântica, relações, temporalidade ou tipagem para medir contribuição de cada elemento.

## 12. Persistência inicial

Preferência para primeira versão:

- Python 3.12;
- SQLite;
- Pydantic;
- camada de repositório explícita;
- índice textual local;
- embeddings opcionais e desacoplados;
- execução offline por padrão.

Não introduzir infraestrutura pesada sem evidência de necessidade.

## 13. Interface

A primeira versão pode ser CLI.

Comandos mínimos:

- inicializar banco;
- carregar dataset;
- criar registro;
- criar episódio;
- criar checkpoint;
- relacionar registros;
- buscar por pistas;
- reconstruir cápsula;
- explicar recuperação;
- executar suíte de avaliação;
- exportar relatório.

## 14. Guardrails

- proibir invenção de fontes;
- exigir ID de origem para afirmação recuperada;
- marcar inferências;
- preservar histórico de substituição;
- não apagar evidência silenciosamente;
- manter dataset de avaliação separado do dataset de desenvolvimento;
- não alterar casos esperados para fazer testes passarem;
- registrar configuração, versão e seed;
- permitir repetição do experimento.

## 15. Critério de conclusão do protótipo

O protótipo está pronto para avaliação quando:

- todos os tipos mínimos estão validados;
- relações são persistidas e consultadas;
- as três estratégias de busca funcionam;
- cápsulas são reconstruídas;
- explicações apontam fontes reais;
- conflitos e ausência são declarados;
- testes automatizados passam;
- dataset e resultados são reproduzíveis;
- nenhum serviço pago é obrigatório para executar a linha de base.
