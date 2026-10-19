# Apelidos somente na seleção do faturamento — 19/10/2026

Em Faturamento de insumos, a seleção mostra nome oficial seguido de apelidos manuais/históricos, sem repetir valores idênticos. A busca também considera os apelidos. Arquivo alterado: `frontend/src/pages/Estoque/FaturamentoInsumos.tsx`.

O formulário de seleção permanece `nao-imprimir`. RelatorioFaturamento continua usando somente `item.propriedade_nome`; backend mantém `propriedade_nome = propriedade.nome` e o PDF usa esse campo oficial. Nenhum apelido foi incluído no payload, resumo, histórico de faturamentos ou gerador de PDF. Sem migrations.

Backup verificado: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-081716`. Testes frontend existentes (inclusive relatório de faturamento), TypeScript/Vite e build Docker aprovados; diff revisado. Interface atualizada na porta 5174. Não foi confirmado faturamento real nem gerado novo PDF durante esta alteração.

Branch operacional `codex/modernizacao-visual-runtime`. Alterações anteriores preservadas; sem commit, push ou merge.
