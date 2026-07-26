# Changelog

As mudanças relevantes do projeto são registradas neste arquivo. O formato é
inspirado em Keep a Changelog e as versões seguem versionamento semântico quando
uma release é publicada.

## Não publicado

### Alterado

- consolidada a documentação arquitetural e a distinção entre escopo funcional
  concluído e prontidão para produção;
- alinhados roadmap, cronograma e índice de Sprints;
- ampliados os requisitos funcionais e não funcionais rastreáveis;
- atualizado o fluxo de contribuição e revisão.

### Removido

- protótipo FastAPI/SQLAlchemy não referenciado pelo backend Django;
- arquivo de comandos Git `agro`, que poderia alterar remote, branch e publicar
  código acidentalmente.

## 1.0.0 — 2026-07-25

### Adicionado

- conclusão funcional das Sprints 1 a 12;
- backend Django REST Framework, frontend React/TypeScript e PWA;
- módulos de propriedades, talhões, clima, mercado, financeiro, estoque,
  operações, máquinas, relatórios e IA;
- ambiente Docker e testes automatizados do projeto.

### Corrigido

- isolamento dos indicadores de estoque por propriedade e safra;
- alertas do assistente gerencial e validação de filtros;
- consultas repetidas na posição de estoque;
- renovação automática de sessão JWT no frontend.
