# Edição e exclusão de transferências

Uma transferência é identificada pelo ID do movimento `transferencia_saida`. As duas movimentações originais são preservadas. A edição estorna ambas e registra uma nova transferência na mesma transação; a exclusão registra dois estornos. Motivo obrigatório e chave de idempotência protegem a confirmação e o reenvio.

| Método / rota | Permissão | Dados |
| --- | --- | --- |
| PATCH `/api/graos/transferencias/<saida>/` | transferencias / editar | motivo, chave_idempotencia, quantidade_kg, data_movimento, referência/observações e posições de origem/destino |
| DELETE `/api/graos/transferencias/<saida>/` | transferencias / excluir | motivo, chave_idempotencia |
| GET `/api/graos/cargas-colhidas/<id>/previa-exclusao/` | cargas / consultar | somente leitura |

A edição aceita o contrato de criação de transferência: posições oficiais ou adaptadores legados; também aceita posição de origem com propriedade/CAD/PRO de destino sem estoque prévio. `motivo` tem até 500 caracteres e `chave_idempotencia` até 160. Os metadados da correção são definidos pelo servidor. Uma operação bem-sucedida retorna HTTP 200, ID da correção, ação, origens original/nova, motivo e `idempotente`. Mesmo token com outros dados, original encerrado ou saldo insuficiente retornam HTTP 409. Entrada da transferência ou ID inexistente retornam 404; dados inválidos, 400; ação não autorizada, 403.

Os movimentos consultados incluem `estornado` e `correcao_transferencia` (ação, motivo, autor, data e nova origem). O histórico distingue ativas, editadas, excluídas e estornadas. Impressões com histórico somam somente transferências ativas, evitando contar o lançamento original e sua substituição juntos.

A exclusão exige saldo suficiente no destino, inclusive para as reservas. Na edição, a reversão pode gerar saldo negativo transitório dentro da transação; todas as posições envolvidas precisam terminar com físico e disponível não negativos. Uma falha reverte toda a correção. CAD/PRO e posições devem continuar ativos e a capacidade do armazém é validada pelos serviços existentes. Estornos pelos endpoints legados e pela conferência também exigem a permissão de exclusão de transferências; não contornam os acessos por módulo.

## Prévia de exclusão da carga

A consulta retorna `pode_excluir`, efeitos por posição (saldos anterior/posterior, comprometido/disponível), impedimentos e até 20 transferências ativas posteriores nas posições bloqueadas. A lista orienta a conferência; não afirma que cada transferência consome exatamente aquela carga, pois o saldo é compartilhado na mesma posição. A validação transacional do cancelamento permanece definitiva e pode rejeitar uma prévia que ficou desatualizada.

Na interface, o motivo e a confirmação da exclusão aparecem junto à carga; impedimentos e falhas de conexão aparecem no mesmo local. Para a carga #50, a transferência #126/#127 retirou os 15.000 kg de Pedro Carioca e creditou a Fazenda Electra. Confira/exclua primeiro essa transferência pelo fluxo próprio e então solicite novamente a prévia da carga. A implementação não exclui registros reais para testes.

## Cultura em Nova venda

O seletor Cultura aparece também nas vendas comuns. As posições são filtradas por propriedade/CAD/PRO e cultura, sem excluir posições de saldo zero ou negativo. Trocar a cultura limpa a posição anterior. A cultura também define a posição a iniciar e o rateio PARTICULAR. O cadastro e a confirmação continuam sujeitos às validações comerciais existentes.

Migration aditiva: `graos0014_correcaotransferenciasaldo`; não transforma transferências ou cargas existentes.
