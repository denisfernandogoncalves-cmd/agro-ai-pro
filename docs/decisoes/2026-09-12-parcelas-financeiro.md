# Cadastro simplificado com parcelas

Branch codex/grupos-propriedades-colheita, checkout runtime-origin-main.
O usuário pediu remover categoria, parceiro, centro de custo, propriedade e
safra do formulário e confirmou que quantidade significa dividir um valor total.

Critérios atendidos em código e testes: campos removidos da tela, recebedor
digitado ou sugerido, prévia mensal, soma exata em centavos, categoria opcional,
gravação atômica, replay idempotente, preservação de vínculos antigos e relatórios.
Vencimentos mensais foram comunicados antes da implementação. Boletos bancários
não são emitidos; várias parcelas não reutilizam o código do boleto original.

Arquivos principais:
- backend/apps/financeiro/models.py, serializers.py, views.py, parcelamentos.py;
- backend/apps/financeiro/test_parcelamentos.py e migration 0003;
- backend/apps/relatorios/selectors.py (categoria opcional e recebedor);
- frontend/src/api/financeiro.ts;
- frontend/src/pages/Financeiro/FinanceiroPage.tsx, LeitorCodigoFinanceiro.tsx e ParcelasPreview.tsx;
- frontend/scripts/test-components.mjs e docs/api/FINANCEIRO.md.

Backups completos verificados (dump lido integralmente, ZIP CRC e SHA-256):
- backups/agro-ai-pro-2026-09-12-073020-255236, antes das alterações;
- backups/agro-ai-pro-2026-09-12-121123-395171, antes da migration/atualização.

Validações:
- manage.py test apps.financeiro apps.relatorios --settings=config.settings.test --noinput: 55 aprovados.
- docker compose -p agro-ai-pro exec -T -e POSTGRES_DB=parcelas_20260912_1211 -w /app/backend backend python manage.py test apps.financeiro apps.relatorios --keepdb --noinput: 55 aprovados; banco de teste preservado.
- npm.cmd test: testes de componentes e 13 cenários de autenticação aprovados.
- npm.cmd run build: aprovado, aviso preexistente de bundle > 500 kB.
- makemigrations --check --dry-run: nenhuma mudança pendente.
- git -c core.safecrlf=false diff --check: aprovado.
- migrate financeiro --plan: somente financeiro.0003; migrate financeiro aplicado com sucesso.

Sem script de lint. Automação do navegador falhou antes de abrir a sessão
(failed to write kernel assets); conferência visual interativa e leitor USB
dependem de teste pelo usuário. A prévia foi validada por testes de cálculo e
renderização; nenhum título real foi cadastrado durante os testes.
Sem commit, push ou merge. Não foram removidos dados ou cadastros antigos.

Atualização concluída: build Docker e recriação somente do frontend na porta
5174 aprovados. Página retornou HTTP 200; API health retornou status ok.
`manage.py check` no container passou; `showmigrations financeiro` confirmou
0001, 0002 e 0003 aplicadas. Revisão final de diff sem erros de whitespace.
