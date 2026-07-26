# Auditoria de prontidão para produção

A auditoria é executada por blocos independentes e cumulativos. A conclusão de
uma Sprint funcional não implica aprovação automática de segurança, operação ou
produção.

| Bloco | Escopo | Status |
| --- | --- | --- |
| 1 | Arquitetura, estrutura e documentação | Concluído |
| 2 | Settings, autenticação e segurança | Pendente |
| 3 | Banco de dados, models e migrations | Pendente |
| 4 | APIs e permissões | Pendente |
| 5 | Propriedades, talhões, KML e geoprocessamento | Pendente |
| 6 | Clima, mercado e integrações | Pendente |
| 7 | Financeiro, estoque, produção e máquinas | Pendente |
| 8 | IA, relatórios e dashboard | Pendente |
| 9 | Frontend, TypeScript e PWA | Pendente |
| 10 | Docker, CI/CD, testes e observabilidade | Pendente |

## Regras

- todo achado deve registrar evidência, criticidade, impacto e tratamento;
- riscos críticos e altos precisam ser corrigidos ou formalmente aceitos antes
  da declaração de produção;
- testes não executados devem ser informados, nunca presumidos;
- alterações são feitas em branch e passam por revisão antes do merge.

Relatórios:

- [Bloco 1 — Arquitetura, estrutura e documentação](BLOCO-01-ARQUITETURA.md)
