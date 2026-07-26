# Bloco 1 — Arquitetura, estrutura e documentação

**Data:** 2026-07-26  
**Branch:** `chatgpt/auditoria-producao`  
**Base:** `main` no commit `208605536660c5c4f35151d460cbfdefbc7b6fc8`

## Escopo

Revisão da estrutura do repositório, fontes documentais, status das Sprints,
arquitetura declarada, requisitos e artefatos legados.

## Achados tratados

### A-001 — Requisitos insuficientes — Alta

`docs/REQUISITOS.md` descrevia somente cadastro de propriedades, embora o
sistema possua doze Sprints e vários domínios. O catálogo foi ampliado com
requisitos funcionais, não funcionais, situação e evidência principal.

### A-002 — Status de Sprints divergente — Alta

`03-Sprints/CRONOGRAMA.md` marcava as Sprints 7 a 12 como pendentes, enquanto o
índice operacional e o README as marcavam como concluídas. O cronograma foi
alinhado e `documentos/SPRINTS.md` foi definido como fonte canônica.

### A-003 — Arquitetura móvel contraditória — Média

Um documento histórico declarava React Native, enquanto o produto entregue é
uma PWA React. A arquitetura canônica agora registra a PWA como solução da
versão 1.0 e trata aplicativo nativo como evolução futura.

### A-004 — Protótipo de backend não utilizado — Alta

`backend/app/` continha um protótipo FastAPI/SQLAlchemy sem dependências nos
requirements e sem referências no backend Django. Os arquivos foram removidos
para eliminar ambiguidade arquitetural e código não executável.

### A-005 — Arquivo de comandos Git na raiz — Média

O arquivo `agro` continha comandos para alterar remote, renomear branch e fazer
push. Foi removido para evitar execução ou publicação acidental.

### A-006 — Documentação de versão e contribuição obsoleta — Média

`CHANGELOG.md` e `CONTRIBUTING.md` ainda representavam apenas a Sprint 1. Ambos
foram atualizados para refletir a versão funcional 1.0 e o fluxo de revisão
vigente.

### A-007 — Fontes arquiteturais fragmentadas — Média

`ARCHITECTURE.md` passou a ser a fonte canônica. Documentos históricos foram
reduzidos a índices, evitando decisões conflitantes.

## Arquivos principais alterados

- `README.md`;
- `ARCHITECTURE.md`;
- `ROADMAP.md`;
- `CHANGELOG.md`;
- `CONTRIBUTING.md`;
- `docs/REQUISITOS.md`;
- `docs/SPRINTS.md`;
- `documentos/SPRINTS.md`;
- `03-Sprints/CRONOGRAMA.md`;
- índices históricos de arquitetura.

## Arquivos removidos

- `agro`;
- protótipo em `backend/app/`.

## Validações executadas

- verificação de links Markdown relativos nos arquivos alterados;
- comparação do status das Sprints nos três índices;
- busca por referências ao protótipo FastAPI/SQLAlchemy;
- compilação sintática dos arquivos Python restantes;
- validação de JSON do `frontend/package.json`.

A suíte Django e o build frontend não foram executados neste bloco porque o
ambiente de análise não possuía as dependências instaladas. O código de produto
não foi modificado; as validações completas permanecem obrigatórias nos blocos
correspondentes e na CI.

## Riscos remanescentes

- aliases duplicados de settings e requirements serão avaliados no Bloco 2;
- diretórios documentais ainda possuem páginas curtas e devem evoluir conforme
  os blocos técnicos produzirem evidências;
- a declaração final de prontidão para produção depende dos Blocos 2 a 10.
