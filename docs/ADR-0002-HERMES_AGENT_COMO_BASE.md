# ADR-0002 — Hermes Agent como Base Operacional do Harness Cognitivo

**Status:** Aceita em princípio; implementação condicionada a spike técnico e criação formal do fork  
**Data:** 2026-07-27  
**Decisor:** Saimon  
**Escopo:** Harness Cognitivo principal

## 1. Contexto

O Harness Cognitivo precisa de capacidades operacionais comuns a qualquer agente moderno:

- loop de agente;
- resolução de provedores e modelos;
- credenciais;
- streaming;
- chamadas de ferramentas;
- terminal;
- sessões persistentes;
- compressão de contexto;
- cron;
- gateway;
- interface Desktop;
- voz;
- plugins;
- perfis;
- integrações externas.

Reconstruir essas capacidades do zero consumiria tempo significativo sem produzir diferenciação real para o projeto.

O diferencial do Harness Cognitivo está principalmente em:

- MEC;
- memória em camadas;
- perfil pessoal evolutivo;
- recuperação contextual profunda;
- decisões vigentes e históricas;
- memória causal;
- consolidação de experiências;
- governança cognitiva;
- rastreabilidade;
- auditoria;
- custos por etapa;
- aprendizagem a partir de falhas.

## 2. Decisão

O Harness Cognitivo adotará um **fork controlado e fino** do repositório oficial `NousResearch/hermes-agent` como fundação operacional.

A estratégia não é copiar o Hermes e modificar indiscriminadamente o núcleo. A estratégia é:

1. manter o repositório oficial como remoto `upstream`;
2. criar um fork próprio com identidade e distribuição próprias;
3. reduzir alterações diretas no núcleo ao mínimo necessário;
4. implementar capacidades cognitivas como plugins, providers, hooks e módulos separados;
5. preservar a possibilidade de incorporar atualizações do upstream;
6. registrar toda divergência inevitável do núcleo em ADR próprio.

## 3. Base jurídica

O repositório oficial do Hermes Agent está licenciado sob MIT.

A licença permite usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e vender cópias do software, desde que o aviso de copyright e a permissão da licença sejam preservados em cópias ou partes substanciais.

Requisitos para o fork:

- preservar o arquivo `LICENSE` original;
- preservar o aviso de copyright da Nous Research;
- documentar claramente as modificações próprias;
- não sugerir endosso oficial da Nous Research;
- revisar dependências e assets que possam possuir licenças próprias.

## 4. Fundamentação técnica

A arquitetura oficial do Hermes já separa:

- pontos de entrada;
- loop principal do agente;
- construção de prompt;
- resolução de provedores;
- ferramentas;
- persistência de sessões;
- gateway;
- cron;
- plugins;
- memória;
- mecanismos de contexto;
- Desktop.

O sistema de plugins possui fontes de descoberta para usuário, projeto e pacotes Python. Existem tipos especializados para:

- memory providers;
- context engines.

A arquitetura de Desktop usa o mesmo núcleo, configuração, sessões, chaves, skills e memória das demais interfaces. Isso permite reutilizar uma base operacional consolidada em vez de manter implementações paralelas.

## 5. Estratégia de integração do MEC

O MEC R4.1 deve ser integrado inicialmente como um **Memory Provider Plugin**.

Responsabilidades previstas do provider MEC:

- inicializar banco por perfil;
- executar prefetch antes da chamada ao modelo;
- retornar contexto recuperado com fontes e estados;
- persistir turnos quando autorizado;
- capturar eventos antes da compressão;
- consolidar memória no encerramento da sessão;
- disponibilizar ferramentas próprias de busca, confirmação e escrita;
- respeitar isolamento entre perfis;
- usar caminhos derivados de `hermes_home`;
- nunca bloquear o turno principal com processamento pesado.

Métodos de integração a avaliar no spike:

- `initialize()`;
- `get_tool_schemas()`;
- `handle_tool_call()`;
- `system_prompt_block()`;
- `prefetch()`;
- `queue_prefetch()`;
- `sync_turn()`;
- `on_session_end()`;
- `on_pre_compress()`;
- `on_memory_write()`;
- `shutdown()`.

O Hermes aceita somente um memory provider externo ativo por vez. O plugin MEC deverá, portanto, substituir ou absorver as responsabilidades de qualquer provider externo concorrente quando estiver selecionado.

## 6. Arquitetura de memória prevista

A integração deve operar em camadas:

### Memória quente

Perfil compacto do usuário e preferências vigentes, carregados em toda sessão.

### Memória de sessão

Objetivo atual, contexto temporário, esclarecimentos, decisões recentes e estado de execução.

### Memória operacional

Projetos, código, arquivos, commits, protocolos, equipamentos, clientes, incidentes e documentos armazenados pelo MEC.

### Memória profunda

Episódios, decisões antigas, relações, causalidade, evidências e histórico recuperados sob demanda.

O banco do MEC permanece responsável pela memória rica. O prompt deve receber apenas uma cápsula compacta e suficiente.

## 7. Regra de localização para Português do Brasil

O fork adotará localização nativa `pt-BR` para a experiência humana.

Princípio:

> Traduzir a experiência humana; preservar a linguagem técnica.

Deve ser traduzido:

- menus;
- títulos;
- botões;
- descrições;
- ajuda;
- avisos;
- notificações;
- estados operacionais;
- mensagens explicativas de erro;
- aprovações;
- narração por áudio;
- respostas do LLM, quando o usuário não pedir outro idioma.

Deve permanecer na forma técnica original:

- código;
- nomes de classes, funções e variáveis;
- comandos;
- flags;
- caminhos;
- nomes de arquivos;
- branches;
- commits;
- APIs;
- endpoints;
- JSON;
- nomes de modelos e provedores;
- stack traces;
- valores de configuração;
- saídas técnicas originais.

Mensagens híbridas traduzem somente a parte humana. Exemplo:

`Failed to run pytest` → `Falha ao executar pytest`

A tradução deve usar o sistema nativo de internacionalização do Desktop, com fallback para inglês e teste automático de cobertura de chaves.

## 8. Política de mudanças no núcleo

Uma mudança direta no núcleo do Hermes só poderá ocorrer quando:

- não existir extensão oficial adequada;
- a mudança for necessária para uma capacidade essencial;
- houver teste automatizado;
- houver documentação da divergência;
- o impacto sobre atualizações do upstream estiver registrado;
- não for possível resolver por plugin, hook, provider, context engine ou API pública.

Preferência de implementação:

1. configuração;
2. plugin;
3. memory provider;
4. context engine;
5. hook;
6. ferramenta;
7. painel Desktop separado;
8. alteração mínima no núcleo.

## 9. Estratégia de upstream

O fork deve manter:

- `origin`: repositório do Harness Cognitivo;
- `upstream`: `NousResearch/hermes-agent`;
- branch protegida para base sincronizada;
- branches próprias para capacidades cognitivas;
- changelog de divergências;
- rotina periódica de comparação com upstream;
- testes de regressão após cada atualização.

Atualizações do upstream não devem ser mescladas diretamente na distribuição sem:

- leitura do changelog;
- execução da suíte original;
- execução da suíte cognitiva;
- verificação de migrações de configuração e banco;
- validação do Desktop e do pacote `pt-BR`.

## 10. O que será reutilizado

Pretende-se reutilizar, quando tecnicamente adequado:

- providers;
- autenticação e credenciais;
- catálogo de modelos;
- streaming;
- loop do agente;
- tools e backends;
- sessões;
- gateway;
- cron;
- Desktop;
- voz;
- plugins;
- perfis;
- notificações;
- integrações e MCP;
- observabilidade das ações.

## 11. O que permanecerá próprio

Permanecem capacidades próprias do Harness Cognitivo:

- MEC e sua evolução;
- memória pessoal progressiva;
- cápsula contextual;
- decisão vigente e histórica;
- recuperação assistida;
- causalidade;
- avaliação de autoridade da fonte;
- aprendizagem operacional;
- governança reforçada;
- auditoria cognitiva;
- custos e orçamento por etapa;
- coordenação de agentes aprimorada;
- painéis cognitivos;
- regras de consolidação e esquecimento;
- políticas de segurança específicas do produto.

## 12. Riscos

### Divergência excessiva do upstream

Mitigação: fork fino, plugins e ADRs para alterações de núcleo.

### Dependência arquitetural

Mitigação: manter MEC e lógica cognitiva desacoplados por contratos próprios.

### Atualização quebrar plugins

Mitigação: suíte de compatibilidade e versão mínima suportada do upstream.

### Mudança de licença futura

Mitigação: congelar e registrar o commit-base sob a licença vigente; revisar novas versões antes de incorporar.

### Tradução quebrar layout

Mitigação: tradução seletiva, testes visuais e preservação de termos técnicos curtos.

### Memória do Hermes conflitar com MEC

Mitigação: selecionar um único provider externo, definir fonte de verdade e migrar responsabilidades explicitamente.

## 13. Spike técnico obrigatório

Antes de declarar o fork como base definitiva, executar uma prova curta:

1. criar o fork;
2. configurar `upstream`;
3. registrar o commit-base;
4. instalar o ambiente de desenvolvimento;
5. executar a suíte oficial relevante;
6. iniciar o Desktop a partir do source checkout;
7. localizar a infraestrutura de `i18n`;
8. adicionar um locale mínimo `pt-BR`;
9. criar um Memory Provider MEC mínimo;
10. abrir um banco MEC R4.1;
11. executar `prefetch()` com consulta real;
12. inserir a cápsula no contexto;
13. chamar um modelo já configurado;
14. confirmar fontes e estado de memória na resposta;
15. medir arquivos do núcleo modificados.

## 14. Critérios de aceitação do spike

O spike será aprovado se:

- o Desktop iniciar pelo fork;
- um provedor real continuar funcional;
- o locale `pt-BR` aparecer no seletor;
- a tradução não alterar identificadores técnicos;
- o plugin MEC carregar sem patch invasivo;
- uma memória confirmada chegar ao agente;
- `MEMORY_NOT_FOUND` não for apresentado como lembrança;
- as fontes forem preservadas;
- sessões e perfis continuarem isolados;
- a quantidade de mudanças no núcleo permanecer pequena e justificada;
- a atualização futura via `upstream` continuar viável.

## 15. Consequência

O próximo desenvolvimento do Harness Cognitivo não será um gateway de provedores criado do zero.

A sequência passa a ser:

1. consolidar o MEC R4.1;
2. criar o fork controlado do Hermes;
3. localizar o Desktop para `pt-BR`;
4. mapear a arquitetura visual e funcional;
5. integrar um Memory Provider MEC mínimo;
6. validar o circuito real com um modelo;
7. retomar as demais fases do Harness sobre essa fundação.
