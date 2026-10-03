# Painel, alertas, ações, histórico e favoritos — entrega de 02/10/2026

## Resultado e autorização

Melhorias autorizadas pelo Product Owner após a auditoria, retomadas às 12h15 de 02/10/2026. Aplicadas no ambiente local http://127.0.0.1:5174/. Nenhuma publicação em produção.

- Painel inicial com produção líquida, saldos, vendas/entregas, contas e estoque mínimo, respeitando os módulos consultáveis da conta. Filtros por propriedade e safra.
- Avisos de saldo negativo, estoque mínimo/validade, vencimentos, cadastros incompletos e possíveis duplicatas. Apenas conferência, sem exclusão ou correção automática. Atalhos abrem consultas com filtros e identificação do registro.
- Ações consultar/cadastrar/editar/excluir/imprimir configuráveis por módulo em Usuários. Aplicação na API, formulários, navegação e botões. Administradores mantêm acesso completo; permissões reais atuais preservadas até edição explícita.
- Histórico administrativo com usuário, horário, entidade e diferenças dos campos persistidos. Sem senhas/tokens, dados bancários, arquivos ou observações livres. Sem edição/exclusão pela API. Captura novas operações desde a migration aplicada nesta data, sem inventar registros anteriores.
- Páginas e mapa carregados com React.lazy/Suspense. JavaScript inicial final aproximadamente 210 KB (66 KB gzip); módulos separados em arquivos próprios.
- Filtros favoritos privados por conta em Relatórios, Financeiro, Cargas, Produção e saldos e Vendas, incluindo os critérios comerciais disponíveis em cada consulta.
- Embalagens a enviar preenchidas por teto(litros sugeridos/conteúdo), com edição manual preservada e botão Usar sugestão para retornar ao automático. Exemplo conferido: Electra, 72 alq., 0,2 l/alq., 14,4 l, galão de 5 l = 3 embalagens. Recálculo de área/dosagem/conteúdo e preservação do valor manual conferidos sem registrar envio real.

## Branch, preservação e banco

Checkout D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main; branch codex/propriedades-impressao-a4-20260921. Trabalho anterior e alterações não commitadas preservados. Não foi criado usuário real nem alterado acesso real para teste.

Backups privados e ignorados pelo Git:
- backups/sincronizacao-20261002-073041: estado antes da implementação, 13 worktrees, uploads e banco, hashes e integridade verificados.
- backups/sincronizacao-20261002-122537: retomada, 13 worktrees, uploads, bundle/ZIPs verificados; postgres.dump restaurável listado (637 entradas), manifesto SHA-256. A tentativa restrita de backup encontrou ownership Git em outro checkout; corrigida com a execução autorizada do mesmo script. Backup anterior incompleto preservado, sem sobrescrita.

Migrations aditivas accounts.0002_acessousuario_permissoes e core.0001_initial aplicadas localmente. A primeira acrescenta JSON nullable para compatibilidade; a segunda acrescenta favoritos e registros de auditoria. Nenhuma regravação de lançamentos antigos.

## Arquivos principais

Backend: apps/accounts/{models,access,users}.py, accounts/migrations/0002; apps/core/{models,painel,auditoria,serializers,views,urls,apps,middleware,test_evolucao}.py, core/migrations/0001; config/settings/base.py.

Frontend: App.tsx, api/usuarios.ts; components/{AcoesContext,FiltrosFavoritos,NavegacaoModulos,PainelFormulario,ImprimirA4}; pages/Painel/PainelPage.tsx, pages/Historico/HistoricoPage.tsx, pages/Usuarios/UsuariosPage.tsx; consultas de Financeiro/Relatórios/Cargas/Produção/Vendas/Estoque; botões de ação dos módulos; pages/Estoque/{FaturamentoInsumos,embalagensFaturamento}; styles.css e print.css. Testes scripts/test-components.mjs e test-auth.mjs.

Documentação: este relatório, docs/api/PAINEL_ACOES_HISTORICO_FAVORITOS.md, índice API e docs/SPRINTS.md. Nenhum arquivo removido.

## Validação

Comandos executados no checkout runtime (Django pelo serviço backend, /app/backend):
- python manage.py check: sem problemas.
- python manage.py makemigrations --check --dry-run: nenhuma mudança pendente.
- python manage.py migrate --noinput: migrations aditivas aplicadas; conferência final com migrate --check.
- python manage.py test --noinput: PostgreSQL, 515 testes, aprovado, 5 ignorados. A primeira execução revelou um fixture sem atributo path; corrigido com acesso defensivo, sem mascarar os testes de rollback.
- python manage.py test apps.core.test_evolucao apps.accounts --noinput: versão final do histórico, 53 testes aprovados, incluindo somente campos realmente persistidos, isolamento dos favoritos, regras de acesso e estoque mínimo somado entre lotes.
- python manage.py test --settings=config.settings.test --noinput: versão final, 516 testes, aprovado, 39 ignorados por requisitos específicos de banco/concorrência.
- npm.cmd test: componentes/cálculo, guardas de ações e 14 cenários comportamentais de autenticação aprovados. Harness de SSR atualizado para módulos sob demanda; testes específicos usam o contexto de permissões real.
- npm.cmd run build e docker compose -p agro-ai-pro build frontend: TypeScript e produção aprovados.
- Docker frontend recriado na porta 5174, saudável. git diff --check aprovado.

Conferência autenticada no navegador: painel com 11 indicadores, avisos, consulta filtrada do aviso, favoritos, configuração de cinco ações por módulo sem salvar acessos reais, histórico já contendo mudanças feitas pelo usuário. Viewports 360/768/1366 px sem extravasamento da página; tabelas largas têm rolagem própria. O teste visual revelou uma disputa entre consulta inicial e filtros do aviso; corrigida e revalidada com resultado de uma propriedade/cultura/safra.

Capturas privadas no backup de retomada: embalagens-3.png, painel-final.png, painel-360-final.png. Viewport restaurado após testes. Campo de embalagens vazio em recuperação de envio pendente era tratado como edição manual; agora somente valores preenchidos recuperados bloqueiam o automático. Normalização decimal aceita vírgula no helper; cálculo decimal exato evita arredondamento binário indevido.

## Limites e riscos

Alertas mostram até 50 por tipo; saldos até 200 combinações; abrir o módulo para consulta integral. Estoque mínimo usa o saldo do contexto filtrado e o mínimo cadastrado por produto; comparar a abrangência da consulta ao interpretar o aviso. Nenhum alerta presume que duplicidade ou saldo negativo seja necessariamente erro.

Histórico acompanha saves/deletes de entidades de negócio e campos permitidos via requisições autenticadas; alterações externas por SQL, scripts, atualizações em massa e campos técnicos não são reconstruídas. Atualizações de mercado/clima e credenciais não geram histórico de dados sensíveis. Registros anteriores conservam sua classificação original. Permissão de imprimir controla botões e PDFs do aplicativo e o fluxo de impressão da tela, sem pretender impedir captura do conteúdo já consultável no navegador.

Favoritos têm limite de 100 por conta e nome único por consulta. A recuperação de envio pendente mantém a proteção contra repetição de baixa. Ajustes manuais de embalagens conservam a possibilidade de quantidade fracionária já existente; o automático sempre fornece número inteiro para cima.

## Conclusão e Git

Critérios de aceite atendidos e atualização local validada. Sem pendência necessária para este escopo. Contas e lançamentos reais não foram usados para testes de escrita. Commit: não realizado. Push: não realizado. Merge: não realizado.
