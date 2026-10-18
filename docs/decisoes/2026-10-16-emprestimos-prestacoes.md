# Empréstimos de motoristas e cálculo de prestações — 16/10/2026

## Entrega e critérios atendidos

- Transportes → **Empréstimos dos motoristas**: cadastro exato por ID do motorista, nome original preservado, principal, data, vencimento previsto, motivo, usuário e data de criação. Consulta paginada de 30 registros e filtro por motorista.
- Juros do motorista opcionais, **percentual único sobre o principal**, informado antes do cadastro; zero significa sem juros. Não há juros mensais, mora ou capitalização automática. Total arredondado a centavos.
- Pagamentos parciais ou totais com data real, valor, observação/comprovante textual e usuário. Data futura é previsão no vencimento, não pagamento confirmado. Saldo = principal + juros acordados − pagamentos não estornados.
- Pagamento externo reduz a dívida sem alterar holerite. Desconto em holerite exige escolha explícita da remuneração por ID/placa/competência, correspondência exata com o nome original e data dentro da competência. Não atribui históricos automaticamente.
- Holerite identifica **Empréstimo pago**, empréstimo, data e valor; mantém bruto e mostra líquido. Um pagamento não é repetido entre placas. O limite de desconto é o valor da remuneração especificamente selecionada.
- Conta a pagar da remuneração integrada acompanha o líquido, sem criar outro título. Desconto que zera o líquido cancela o título pendente, preservando-o; o estorno explícito pode reabri-lo somente quando zerado pelos descontos. Título liquidado ou cancelado por outro motivo bloqueia alterações. Não liquida nem paga títulos automaticamente.
- Estorno com justificativa preserva pagamento, autor, data e motivo; recompõe dívida, holerite e título pendente na mesma transação. Reenvio não duplica estorno.
- Empréstimos e pagamentos não têm edição/exclusão destrutiva pela API. Remuneração vinculada preserva motorista, placa e competência, inclusive após estorno; não pode ser reduzida abaixo dos descontos ativos.
- Bloqueios PostgreSQL serializam pagamentos e descontos. Chaves UUID impedem duplicação de cadastro/pagamento; payload diferente na mesma chave retorna conflito. Permissões existentes de Transportes/Financeiro são respeitadas.

## Calculadora financeira

Disponível na aba própria **Financeiro → Cálculo de prestações**, com prévia de impressão/PDF acrescentada posteriormente: [aba e impressão](2026-10-16-aba-prestacoes-impressao.md). Usa a planilha privada `D:/Dropbox/PRESTAÇÃO CASE.xlsx` apenas como referência de cálculo, sem modificá-la ou copiá-la para o repositório.

- Compra, entrada em reais, taxa efetiva anual, quantidade de parcelas com amortização, liberação, primeiro vencimento e periodicidade mensal/semestral/anual.
- Carência explícita em vencimentos iniciais que pagam apenas juros, antes das parcelas com amortização. Não infere carência por prazo.
- Amortização constante, juros sobre saldo inicial pelo fator `(1 + taxa/100)^(dias/365) − 1`, com dias corridos reais, inclusive ano bissexto. Vencimentos preservam dia original e limitam ao último dia do mês quando necessário.
- Valores arredondados por parcela; resíduo no principal final, saldo nunca negativo. Média é informativa e considera todos os vencimentos, **não é prestação fixa**. Até 360 vencimentos por simulação, incluindo carência, como limite técnico.
- Referência C6:C11: compra R$ 565.000, entrada 20% (R$ 113.000), 10% anuais, cinco parcelas anuais, liberação 16/10/2026 e primeiro vencimento 16/10/2027. Resultado: financiado R$ 452.000, juros R$ 135.703,88, prestações R$ 587.703,88 e total com entrada R$ 700.703,88. O nome da aba `7,5` não substitui a taxa de 10% efetivamente registrada na célula C9.
- Não inclui tarifas, seguros, CET, ajustes de dias úteis ou criação de lançamentos. A concessão do empréstimo e pagamentos externos não geram movimentos bancários automaticamente; o controle da dívida é separado. Não reclassifica dados anteriores.

## Validação e ambiente

- Checkout Docker: `.worktrees/runtime-origin-main`, branch `codex/modernizacao-visual-runtime`; alterações anteriores preservadas, sem commit/push/merge/produção.
- Backups privados completos e verificados, com hashes e restauração em base isolada: `backups/agro-ai-pro-2026-10-16-131223-512262` (antes da edição), `backups/agro-ai-pro-2026-10-16-131927-875993` (antes da migration) e `backups/agro-ai-pro-2026-10-16-132429-879988` (antes da atualização final).
- Migration aditiva `transportes.0010_emprestimomotorista_pagamentoemprestimo_and_more` aplicada. `makemigrations --check --dry-run`: sem alterações pendentes; system check sem problemas.
- `docker compose -p agro-ai-pro exec -T backend python scripts/test_backend_isolado.py apps.transportes apps.financeiro`: **139 testes, aprovados, 1 ignorado** por ausência da antiga planilha privada `/tmp/transportes-reference.xlsx`. Os testes novos foram executados, incluindo concorrência PostgreSQL, permissões, idempotência, juros, pagamentos, estorno, holerite, integração financeira, arredondamento, carência e referência da planilha.
- Docker frontend: `npm test`, TypeScript e Vite aprovados. Build Windows bloqueado por permissão existente de arquivo em `frontend/dist`; build completo executado com sucesso no Docker, sem apagar a pasta local.
- Interface autenticada conferida em desktop e 360 × 800, com formulários e simulação real da referência. Página sem extravasamento horizontal: 1265/1265 px desktop e 345/345 px celular. Evidências privadas em `C:/Users/DENIS/.codex/visualizations/2026/10/07/01a1161b-d4ff-7dc0-aad5-aafa0a65dae7/emprestimos-20261016`.
- Frontend e backend locais saudáveis; `/api/ready/` pela porta 5174 retorna `{"status":"ok"}`. Nenhum empréstimo ou pagamento fictício foi criado no banco operacional. Formulário de pagamento e estorno validado por testes isolados, sem transacionar dados reais na conferência visual.
