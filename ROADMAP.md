# Roadmap do AGRO-AI-PRO

## Produto funcional 1.0

As Sprints 1 a 12 do escopo funcional estão registradas como concluídas no
índice canônico `documentos/SPRINTS.md`. Essa conclusão indica entrega do
escopo planejado, não certificação automática de prontidão para produção.

- [x] infraestrutura, propriedades, talhões e geoprocessamento;
- [x] previsão climática por propriedade;
- [x] mercado e clima no Corn Belt;
- [x] financeiro;
- [x] estoque e insumos;
- [x] operações;
- [x] máquinas;
- [x] relatórios e dashboards;
- [x] inteligência artificial e automação;
- [x] PWA instalável.

## Auditoria de prontidão para produção

O hardening é acompanhado separadamente em `docs/auditoria/`:

- [x] Bloco 1 — arquitetura, estrutura e documentação;
- [ ] Bloco 2 — settings, autenticação e segurança;
- [ ] Bloco 3 — banco de dados, models e migrations;
- [ ] Bloco 4 — APIs e permissões;
- [ ] Bloco 5 — propriedades, talhões, KML e geoprocessamento;
- [ ] Bloco 6 — clima, mercado e integrações externas;
- [ ] Bloco 7 — financeiro, estoque, produção e máquinas;
- [ ] Bloco 8 — IA, relatórios e dashboard;
- [ ] Bloco 9 — frontend, TypeScript e PWA;
- [ ] Bloco 10 — Docker, CI/CD, testes e observabilidade.

## Critério para declarar produção

A versão somente deve ser classificada como pronta para produção depois de:

1. resolver riscos críticos e altos identificados pela auditoria;
2. executar as validações de backend, frontend e Docker aplicáveis;
3. documentar riscos aceitos e limitações conhecidas;
4. validar backup, restauração, observabilidade e operação segura;
5. aprovar uma Pull Request de release sem falhas impeditivas na CI.

Evoluções posteriores, como aplicativo móvel nativo, integrações pagas e
recursos avançados de IA, devem entrar no backlog antes da implementação.
