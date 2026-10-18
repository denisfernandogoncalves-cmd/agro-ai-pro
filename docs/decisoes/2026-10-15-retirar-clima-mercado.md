# Retirada de Clima e Mercado do programa

Solicitação explícita do Product Owner em 15/10/2026. Aplicada na branch
operacional `codex/modernizacao-visual-runtime`, servida na porta 5174.

## Resultado

- Clima e Mercado retirados do menu, catálogo de módulos e edição de permissões.
- Acessos antigos são filtrados na resposta de usuário, sem modificar configurações
  históricas no banco. A interface bloqueia esses destinos inclusive para administrador.
- Rotas `/api/clima/` e `/api/mercado/` retiradas da configuração pública: 404.
- Removidos o carregamento das páginas e os quadros de clima/cotações do painel;
  não há consultas automáticas desses quadros.
- Seções de clima/mercado retiradas de Relatórios; filtros antigos retornam 400.
- Assistente deixa de gerar alertas climáticos do módulo retirado.
- Tabelas, registros históricos, migrations e arquivos legados preservados.
  Os apps Django permanecem registrados para manter o histórico de migrations;
  isso não republica suas rotas. Nenhuma migration nova ou exclusão de dados.

## Arquivos

Frontend: `App.tsx`, `api/usuarios.ts`, `components/gruposModulos.ts`,
`components/AcoesContext.tsx`, `components/IdentidadeModulo.tsx`,
`pages/Painel/PainelPage.tsx`, `pages/Relatorios/RelatoriosPage.tsx` e
`scripts/test-components.mjs`.

Backend: `config/urls.py`, `apps/accounts/access.py`,
`apps/accounts/test_modulos_retirados.py`, `apps/accounts/test_user_access.py`,
`apps/ai/services.py`, `apps/relatorios/serializers.py`,
`apps/relatorios/selectors.py` e `apps/relatorios/tests.py`.

## Preservação e validação

- Backup completo privado, hashes/integridade e restauração isolada aprovados:
  `backups/agro-ai-pro-2026-10-15-224838-791529`.
- Suíte PostgreSQL isolada de 35 casos: novas verificações de módulos retirados,
  usuários/permissões, relatórios e assistente. Duas expectativas antigas, dentro
  do teste de recursos principais, ainda esperavam Clima/Mercado ativos; ajustado
  o catálogo de recursos do teste. Reteste dos nove casos de ModuleAccessTests
  aprovado. Demais casos já aprovados não foram repetidos.
- Novos testes confirmam 404 inclusive para administrador, recusa das seções de
  relatório e filtragem dos acessos antigos sem alterar o registro persistido.
- Frontend completo: testes, TypeScript e build Docker aprovados, 256 módulos.
- `manage.py check` aprovado; `makemigrations --check --dry-run` sem diferenças;
  revisão de diff sem erros de whitespace.
- Conferência visual com API simulada: menu, painel e relatórios sem os dois
  módulos, mesmo com permissões antigas; nenhuma requisição automática a eles.
- Frontend local atualizado preservando a porta 5174. Conferência HTTP real:
  Clima=404, Mercado=404, `/api/ready/`=`{"status": "ok"}`.

Sem commit, push, merge ou publicação em produção. Demais módulos preservados.
