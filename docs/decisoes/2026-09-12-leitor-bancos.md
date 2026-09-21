# Nome do banco e dados do código pelo leitor

Branch: codex/grupos-propriedades-colheita, checkout runtime-origin-main.
Pedido: extrair os dados automaticamente usando somente leitor, sem PDF/OCR
nem integração bancária. Aceite: nome do banco por catálogo oficial, campos
Itaú reconhecidos com dígitos internos válidos, fallback para desconhecidos,
resumo visível após aplicar e preservação de parceiro/descrição manuais.

Arquivos: financeiro/codigos.py, bancos_str.json e test_codigos.py;
frontend/src/api/financeiro.ts, pages/Financeiro/LeitorCodigoFinanceiro.tsx,
FinanceiroPage.tsx, scripts/test-components.mjs e docs/api/FINANCEIRO.md.

Backup anterior às alterações:
backups/agro-ai-pro-2026-09-12-070925-186384, código, uploads, dump PostgreSQL,
leitura integral do dump, CRC dos ZIPs e SHA-256 no manifesto.

Validações:
- manage.py test apps.financeiro --settings=config.settings.test --noinput: 28 testes aprovados.
- npm.cmd test: testes de componentes e 13 cenários de autenticação aprovados.
- npm.cmd run build: aprovado; aviso preexistente de bundle acima de 500 kB.
- manage.py makemigrations --check --dry-run --settings=config.settings.test: sem mudanças.
- git -c core.safecrlf=false diff --check: aprovado.

Sem migrations novas. Sem script de lint. Não foi usada informação de boleto
real nos testes. A leitura com USB físico permanece dependente de conferência
do usuário. O banco informado pelo catálogo não é o nome do recebedor;
titularidade, CPF/CNPJ completo e pagamento não são inferidos. Suporte de
campo livre específico limitado às carteiras Itaú documentadas no contrato.
Sem commit, push ou merge. Alterações preexistentes preservadas.

Atualização local: backup adicional verificado em
backups/agro-ai-pro-2026-09-12-071304-533563 antes do build Docker.
`docker compose -p agro-ai-pro build frontend` e `up -d --no-deps frontend`
com FRONTEND_PORT=5174 concluídos. Página retornou HTTP 200 e /api/health/
retornou status ok. `manage.py check` no backend ativo não apontou problemas;
leitura de código sintético no container retornou Banco do Brasil S.A.
Conferência visual interativa não executada nesta entrega; testes de renderização
estática verificaram o resumo de banco, agência, linha e limite do recebedor.
