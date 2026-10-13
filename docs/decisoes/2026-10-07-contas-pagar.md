# Relatório de contas a pagar — 07/10/2026

Implementado em Relatórios → Gestão rural → Contas a pagar no checkout runtime-origin-main.
Reutiliza a consulta financeira e as exportações PDF/Excel. Filtra tipo pagar no
servidor; preserva status pendente/liquidado/cancelado, filtros de propriedade,
proprietário, safra e período por vencimento. Paginação existente de 25 registros.
Sem migração, criação de lançamentos ou pagamentos automáticos. Valores em R$.
Backup verificado: backups/agro-ai-pro-2026-10-07-214100-338447.
Frontend npm test/TypeScript/build aprovados; serviço 5174 saudável.
17 testes existentes de relatórios aprovados e teste específico aprovado após
corrigir a expectativa do rótulo para Conta a pagar. Teste verifica exclusão das
contas a receber, datas, status, paginação e ausência de alterações nos registros.
Resumo por fornecedor, agenda e total pendente ainda são sugestões adicionais.
