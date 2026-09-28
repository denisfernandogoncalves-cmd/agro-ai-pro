# Financeiro — filtros por situação, período e recebedor

Implementado em 22/09/2026, incremento da Sprint 6.

## Uso e critérios atendidos

- Selecionar contas a pagar/pagas e a situação pendente ou liquidada.
- Filtrar intervalo inclusivo de vencimento ou pagamento/recebimento, com limites opcionais.
- Selecionar parceiro; no runtime da porta 5174, buscar também nome parcial do recebedor digitado no boleto.
- Aplicar e limpar filtros atualiza lista e totais em conjunto, inclusive busca textual.
- Cartão Pagos e lançamentos liquidados usam valor efetivamente liquidado.
- Datas inválidas ou intervalos invertidos retornam HTTP 400. Sem mudança de models ou migrations.

## API e arquivos

GET /api/financeiro/lancamentos/ e /api/financeiro/lancamentos/resumo/:
`tipo`, `status`, `search`, `parceiro`, `vencimento_inicio`, `vencimento_fim`,
`liquidacao_inicio`, `liquidacao_fim`. Datas AAAA-MM-DD. Autenticação preservada.
No runtime, `recebedor` busca em recebedor_nome e parceiro__nome.

Alterados backend/apps/financeiro/{views,tests}.py, frontend/src/api/financeiro.ts,
frontend/src/pages/Financeiro/FinanceiroPage.tsx e frontend/src/styles.css.
No runtime, ajustado frontend/scripts/test-components.mjs para restringir a
validação de campos retirados ao formulário de cadastro, preservando testes existentes.

## Ambiente e validações

Workspace inicial: feature/importacoes-confirmacao-v1. Build e 28 testes frontend
aprovados; 16 testes financeiros aprovados com apps isolados. A validação global
nessa branch tem falha preexistente: cadpro não instalado nas settings apesar das
dependências de migrations de graos. Não alterado por estar fora do escopo.

O endereço solicitado 127.0.0.1:5174 usa .worktrees/runtime-origin-main,
branch codex/propriedades-impressao-a4-20260921. Alterações adaptadas à versão
existente de boletos, sem substituir funcionalidades nem alterações de impressão.

Nesse runtime:
- manage.py test apps.financeiro --settings=config.settings.test: 41 aprovados.
- manage.py makemigrations --check --dry-run --settings=config.settings.test: sem alterações.
- npm.cmd test: 44 testes de componentes e 13 de autenticação aprovados.
- npm.cmd run build e docker compose -p agro-ai-pro build frontend: aprovados.
- Não existe script lint. Build mantém aviso de bundle maior que 500 kB.
- Serviços locais saudáveis; /api/health/ responde 200 pela porta 5174.
- Navegador: filtro de pagos, nome parcial e intervalo de pagamento retornou
  somente o lançamento correspondente; Limpar filtros restaurou lista e totais.
- Inicialização do backend confirmou ausência de migrations pendentes.

## Preservação e Git

Backup privado: backups/financeiro-filtros-20260922-070627, no workspace principal.
Contém código/uploads de ambas as cópias, inclusive alterações não commitadas do
runtime, PostgreSQL copiado parado, manifestos e SHA-256. ZIPs validados.
Sem commit, push ou merge. Sem alteração de dados financeiros existentes.
