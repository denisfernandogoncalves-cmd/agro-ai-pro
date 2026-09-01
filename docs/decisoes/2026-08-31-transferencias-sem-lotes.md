# Transferências por posição oficial, sem seleção de lotes

Solicitação do Product Owner em 31/08/2026: remover os campos **Lote de origem**
e **Lote de destino** e tornar visíveis as informações inseridas nas
transferências.

## Decisão

A interface e o contrato preferencial da API usam `posicao_origem` e
`posicao_destino`. A posição contém propriedade produtora, CAD/PRO, cultura,
safra, classificação e armazenagem e continua sendo a fonte oficial do saldo.

O modelo histórico de movimentações ainda exige lote. Para preservar migrations,
rastreabilidade e integrações existentes, a API resolve de forma determinística
o primeiro lote operacional ativo que corresponde exatamente à posição. Esse
lote é apenas adaptador interno e não é escolhido nem exibido no formulário.
O contrato legado por lotes permanece aceito para compatibilidade.

## Resultado

- o formulário mostra somente origem, destino, quantidade, data, referência e
  observações;
- origem exige saldo disponível positivo;
- destino exige cultura, safra e classificação iguais e posição diferente;
- o histórico mostra data, origem e destino completos, produto/safra,
  classificação, quantidade, documento, observações, usuário e data do registro;
- débito e crédito continuam atômicos, idempotentes e conservam o saldo total;
- nenhuma migration ou reescrita de dados foi necessária.

Backup anterior às alterações:
`backups/retomada-2026-08-31-215508-012689/`.
