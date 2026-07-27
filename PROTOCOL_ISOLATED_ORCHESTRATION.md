# Protocolo de Orquestração Isolada

## Objetivo

Executar trabalhos complexos em uma única sessão do Hermes sem permitir que o mesmo agente atue simultaneamente como autor, executor, revisor e auditor.

O LLM principal atua somente como orquestrador de fluxo. Todo trabalho substantivo é delegado a subagentes com contexto mínimo, permissões explícitas e artefatos congelados.

## Princípios obrigatórios

1. **Separação de papéis**: nenhum agente pode criar, executar, revisar e aprovar o mesmo artefato.
2. **Mínimo contexto necessário**: cada subagente recebe apenas os arquivos e requisitos necessários ao seu papel.
3. **Congelamento antes da próxima etapa**: dataset, avaliação e resultados recebem commit e hash antes de avançar.
4. **Revisor não corrige**: revisor apenas aponta falhas e devolve relatório estruturado ao executor.
5. **Auditor não corrige**: auditor apenas compara escopo, evidência e implementação e possui poder de veto.
6. **Retorno ao revisor**: toda correção feita pelo executor deve voltar para nova revisão.
7. **Sem adaptação pós-resultado**: queries, gabaritos, datasets, thresholds e critérios não podem ser ajustados depois de qualquer execução avaliativa.
8. **Rastreabilidade**: toda transição de estado registra agente, entrada, saída, commit, hash e veredito.

## Papéis

### Orquestrador

Pode:
- criar subagentes;
- distribuir contexto mínimo;
- controlar a máquina de estados;
- verificar existência de commits e hashes;
- encaminhar relatórios entre papéis.

Não pode:
- escrever dataset;
- escrever gabarito;
- alterar código;
- corrigir achados;
- emitir aprovação técnica própria;
- fornecer respostas esperadas aos subagentes.

### Construtor

Pode:
- criar exclusivamente o artefato definido para construção;
- executar validações estruturais não avaliativas;
- gerar manifesto e hashes.

Não pode:
- acessar queries, gabarito, resultados ou holdouts;
- otimizar conteúdo para mecanismos de retrieval;
- julgar a própria qualidade final.

### Autor da avaliação

Pode:
- ler o artefato congelado;
- criar queries, critérios e gabarito antes da execução;
- gerar hash e commit de congelamento.

Não pode:
- alterar o dataset;
- executar a avaliação antes do congelamento;
- adaptar perguntas após observar resultados.

### Executor

Pode:
- executar scripts e testes congelados;
- implementar ou corrigir código quando autorizado;
- responder aos apontamentos do revisor.

Não pode:
- alterar dataset, avaliação ou critérios congelados;
- aprovar a própria entrega;
- modificar relatório do revisor ou auditor.

### Revisor

Pode:
- analisar diff, código, testes e requisitos pertinentes;
- apontar erro, arquivo, linha, requisito violado e evidência;
- aprovar ou devolver para correção.

Não pode:
- editar código;
- criar commits de correção;
- alterar testes para fazê-los passar;
- emitir aprovação de escopo global.

### Auditor

Pode:
- comparar implementação, escopo, requisitos, histórico, evidências e hashes;
- criar testes reservados;
- verificar contaminação metodológica;
- emitir veredito final.

Não pode:
- corrigir código;
- alterar artefatos avaliados;
- adaptar holdouts após resultados;
- aprovar com evidência incompleta.

## Máquina de estados

1. `WORLD_BUILDING`
2. `DATASET_FROZEN`
3. `EVALUATION_AUTHORING`
4. `EVALUATION_FROZEN`
5. `EXECUTION_RUNNING`
6. `REVIEW_PENDING`
7. `REWORK_REQUIRED`
8. `REVIEW_RECHECK`
9. `AUDIT_PENDING`
10. `APPROVED_FOR_EXPERIMENTAL_USE` ou estado de falha

Nenhuma etapa pode ser pulada.

## Pipeline obrigatório

### Etapa A — Construção

- subagente Construtor cria dataset ou implementação;
- executa apenas validações estruturais permitidas;
- gera manifesto;
- calcula hashes;
- cria commit de congelamento;
- encerra.

### Etapa B — Avaliação independente

- novo subagente, sem histórico do Construtor;
- recebe somente o artefato congelado e a especificação de avaliação;
- cria queries, gabarito e critérios;
- calcula hashes;
- cria commit de congelamento;
- encerra.

### Etapa C — Execução

- novo subagente Executor;
- recebe apenas commits congelados e comandos;
- roda três vezes quando determinismo for requisito;
- produz resultados brutos;
- não edita entradas;
- encaminha para revisão.

### Etapa D — Revisão

- novo subagente Revisor;
- analisa implementação, resultados e requisitos;
- não corrige;
- produz relatório estruturado.

Se houver falhas:
- Orquestrador encaminha somente o relatório ao Executor;
- Executor corrige;
- novo Revisor ou nova instância limpa revisa novamente;
- ciclo continua até aprovação ou limite de rework.

### Etapa E — Auditoria

- novo subagente Auditor;
- recebe commits congelados, relatórios e escopo;
- cria conjunto reservado próprio;
- verifica contaminação, hardcodes e manipulação metodológica;
- emite veredito final;
- não corrige.

## Isolamento técnico mínimo

Cada subagente deve usar:
- conversa nova;
- contexto explícito e mínimo;
- branch ou worktree própria quando houver escrita;
- lista de caminhos permitidos para leitura;
- lista de caminhos permitidos para escrita;
- proibição explícita de ler holdouts ou artefatos de outros papéis;
- saída final estruturada.

## Contrato de saída dos subagentes

Todo subagente deve retornar:
- papel executado;
- entradas recebidas;
- arquivos lidos;
- arquivos escritos;
- comandos executados;
- testes executados;
- commit completo;
- hashes;
- limitações;
- estado final permitido.

## Regras contra contaminação

É proibido:
- incluir vocabulário de queries no dataset para melhorar score;
- alterar query ou gabarito após execução;
- criar testes que apenas confirmem a implementação atual;
- hardcodar IDs esperados para satisfazer gabarito;
- remover testes problemáticos;
- reduzir dificuldade de holdouts;
- usar alegação do executor como evidência suficiente;
- permitir que o orquestrador substitua o julgamento do revisor ou auditor.

## Critério de confiança

Uma entrega só é confiável quando:
- o artefato foi construído sem acesso à avaliação;
- a avaliação foi congelada antes da execução;
- o executor não alterou entradas;
- o revisor não corrigiu;
- correções retornaram para nova revisão;
- o auditor usou evidência independente;
- todos os hashes e commits são reproduzíveis.

## Uso no Experimento Real 02 Limpo

O Experimento 02 Limpo deve ser executado em uma única sessão do Hermes, com GLM-5.2 como orquestrador e subagentes separados para:

1. Construtor do mundo;
2. Autor da avaliação;
3. Executor;
4. Revisor;
5. Executor de rework, se necessário;
6. Revisor de confirmação;
7. Auditor independente.

O orquestrador deve interromper imediatamente se qualquer agente violar isolamento, alterar artefato congelado ou acessar informação não autorizada.
