# Fornecedor nos lotes e leitura ampliada

Branch: codex/grupos-propriedades-colheita, checkout runtime-origin-main.

Novo lote seleciona produto agrícola e fornecedor do cadastro central.
Depósito opcional, vínculos históricos preservados. API rejeita produto
inativo, fornecedor inativo ou somente cliente e duplicidade por
produto/fornecedor/código sem depósito. Posição, movimentações e relatórios
tratam depósito nulo. Relatórios filtrados pela propriedade do depósito
não incluem lotes sem depósito.

Leitura financeira ampliada com linha digitável reconstruída, formato,
moeda/referência, fator de vencimento, identificador do emissor e campo livre.
Descrição sugerida preserva texto preenchido. Dados específicos do banco
não são inferidos sem interpretação homologada.

## Arquivos

Estoque: models, serializers, services, views, admin, migration 0002,
test_fornecedores.py, frontend/src/api/estoque.ts e EstoquePage.tsx.
Relatórios: selectors.py. Financeiro: codigos.py, test_codigos.py,
frontend/src/api/financeiro.ts e LeitorCodigoFinanceiro.tsx.
Testes de descrição em frontend/scripts/test-components.mjs.
Contratos atualizados em docs/api/ESTOQUE.md e docs/api/FINANCEIRO.md.

## Backups e banco

Backups completos em backups/agro-ai-pro-2026-09-11-071859-606374 e
backups/agro-ai-pro-2026-09-11-165231-805158: código não commitado, uploads,
dump PostgreSQL, verificação integral e SHA-256 nos manifestos.
Migration de Estoque 0002 aplicada. Nenhuma restauração ou exclusão de
banco existente nesta entrega.

## Validações

- manage.py test apps.estoque apps.relatorios --settings=config.settings.test --noinput: 40 aprovados.
- Mesmos módulos em PostgreSQL com POSTGRES_DB=fornecedor_lotes_20260911_0724 --keepdb --noinput: 40 aprovados; banco de teste preservado.
- manage.py test apps.financeiro apps.estoque apps.relatorios --settings=config.settings.test --noinput: 66 aprovados.
- npm.cmd test e npm.cmd run build: aprovados; aviso de bundle acima de 500 kB.
- makemigrations --check --dry-run: nenhuma migration faltante.
- git -c core.safecrlf=false diff --check: aprovado.

Sem script de lint. Navegador automatizado falhou na inicialização
(kernel assets); validação visual e leitor USB físico pendentes.
Sem commit, push ou merge.
