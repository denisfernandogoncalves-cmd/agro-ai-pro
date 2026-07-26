# Requisitos do AGRO-AI-PRO

Este documento é o catálogo funcional e não funcional de alto nível da versão
1.0. Os detalhes e evidências de implementação ficam nos documentos de Sprint,
na documentação da API e nos testes automatizados.

## Convenções

- `RF`: requisito funcional.
- `RNF`: requisito não funcional.
- **Implementado:** existe no escopo funcional da versão 1.0.
- **Em auditoria:** existe, mas sua prontidão para produção ainda está sendo
  verificada em `docs/auditoria/`.

## Requisitos funcionais

| ID | Requisito | Situação | Evidência principal |
| --- | --- | --- | --- |
| RF-001 | Autenticar usuários e proteger a API por JWT. | Implementado / em auditoria | `backend/apps/accounts/`, Sprint 1 |
| RF-002 | Cadastrar, consultar, alterar e excluir propriedades rurais respeitando vínculos protegidos. | Implementado | `backend/apps/propriedades/`, Sprint 1 |
| RF-003 | Importar e validar perímetros KML de propriedades e talhões. | Implementado / em auditoria | Propriedades, Talhões e Sprint 3 |
| RF-004 | Gerenciar talhões, cultura, safra, área, produtividade e histórico agronômico. | Implementado | `backend/apps/talhoes/`, Sprint 2 |
| RF-005 | Exibir geometrias em mapa e calcular área geodésica aproximada. | Implementado | Sprint 3 e frontend de mapas |
| RF-006 | Consultar e persistir previsão climática por propriedade com fallback de dados. | Implementado / em auditoria | `backend/apps/clima/`, Sprint 4 |
| RF-007 | Acompanhar soja, milho, trigo, Brent, regiões do Corn Belt e notícias cadastradas. | Implementado / em auditoria | `backend/apps/mercado/`, Sprint 5 |
| RF-008 | Controlar contas a pagar e receber, categorias, parceiros, liquidação e fluxo de caixa. | Implementado / em auditoria | `backend/apps/financeiro/`, Sprint 6 |
| RF-009 | Controlar produtos, locais, lotes, entradas, saídas, saldos, validade e estoque mínimo. | Implementado / em auditoria | `backend/apps/estoque/`, Sprint 7 |
| RF-010 | Planejar operações agrícolas e baixar insumos usados de forma transacional. | Implementado / em auditoria | `backend/apps/producao/`, Sprint 8 |
| RF-011 | Controlar máquinas, horímetro, abastecimentos, manutenções e uso em operações. | Implementado / em auditoria | `backend/apps/maquinas/`, Sprint 9 |
| RF-012 | Consolidar indicadores gerenciais e relatórios por propriedade e safra. | Implementado / em auditoria | dashboard, relatórios e Sprint 10 |
| RF-013 | Gerar insights explicáveis com dados internos do sistema. | Implementado / em auditoria | `backend/apps/ai/`, Sprint 11 |
| RF-014 | Disponibilizar interface web responsiva e instalável como PWA. | Implementado / em auditoria | `frontend/`, Sprint 12 |
| RF-015 | Permitir filtros, busca, ordenação e paginação nos recursos aplicáveis. | Implementado / em auditoria | API e documentos de módulo |

## Requisitos não funcionais

| ID | Requisito | Situação |
| --- | --- | --- |
| RNF-001 | Segredos e credenciais devem ser fornecidos por variáveis de ambiente. | Em auditoria |
| RNF-002 | Produção deve operar com `DEBUG=False`, hosts e origens explicitamente permitidos. | Em auditoria |
| RNF-003 | A API deve aplicar autenticação e autorização por padrão e permissões específicas quando necessário. | Em auditoria |
| RNF-004 | Uploads devem limitar tamanho, extensão, MIME e conteúdo, sem confiar no nome do arquivo. | Em auditoria |
| RNF-005 | Operações financeiras, de estoque e de produção devem preservar integridade e atomicidade. | Em auditoria |
| RNF-006 | Listagens devem evitar consultas N+1 e usar paginação em volumes relevantes. | Em auditoria |
| RNF-007 | O sistema deve possuir logs suficientes para diagnóstico sem expor segredos ou dados sensíveis. | Em auditoria |
| RNF-008 | Backend, frontend e Docker devem possuir validações automatizadas reproduzíveis. | Em auditoria |
| RNF-009 | A interface deve ser responsiva, acessível e tratar estados de carregamento, vazio e erro. | Em auditoria |
| RNF-010 | Integrações externas devem usar timeout, tratamento de falha e cache ou fallback quando aplicável. | Em auditoria |
| RNF-011 | Banco e arquivos persistentes devem possuir estratégia documentada de backup e restauração. | Em auditoria |
| RNF-012 | Mudanças relevantes devem ser rastreáveis por branch, Pull Request, testes e changelog. | Implementado / em auditoria |

## Regras de rastreabilidade

1. Uma Sprint concluída prova entrega de escopo, não prontidão automática para
   produção.
2. Requisitos novos devem receber identificador antes de serem implementados.
3. Correções que alterem contrato ou regra de negócio devem atualizar requisito,
   teste e documentação da API correspondentes.
4. Pendências de hardening são acompanhadas em `docs/auditoria/` e no roadmap.
