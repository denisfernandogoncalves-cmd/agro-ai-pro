# Romaneios de entrada e paleta azul petróleo

## Escopo autorizado

As cargas colhidas próprias, compartilhadas e de terceiros usam a mesma grade dos romaneios de venda: identificação, pesagem, qualidade, transporte, observações e assinaturas. A primeira via é do cliente e a segunda do arquivo, na mesma folha A4. As entradas apresentam descontos em percentual e kg, sem preço ou total em reais. A interface usa a paleta escolhida pelo usuário: azul petróleo, branco e cinza claro.

## Implementação

- `ComprovanteLancamento.tsx` compartilha a definição dos campos entre a prévia React e o HTML, distinguindo ENTRADA de SAÍDA. Campos exclusivos do arquivo não são acrescentados às entradas.
- Os helpers de Cargas Colhidas e Terceiros preservam pesos totais, descontos, propriedades/CAD/PRO, situação e rastreabilidade. Conforme orientação adicional, a identificação da propriedade/CAD/PRO não traz o peso rateado; os dados do rateio permanecem no registro. Motorista aparece antes da placa em entradas/vendas, incluindo PDF e Excel de vendas. PH aparece somente no trigo. Informações antigas ausentes continuam identificadas como não informadas; tara não registrada não é presumida como zero.
- O ajuste de fonte e o bloqueio de transbordamento A4 existentes continuam ativos, sem truncar textos. Vendas mantêm o valor negociado somente na via do arquivo.
- O tema de tela substitui o bloqueio global de cores por seletores de superfícies, navegação e estados. Azul petróleo `#164e63`, fundo `#f3f5f7`, cartões brancos, texto `#1f2933` e texto secundário `#52616b`. Contraste branco/azul: 9,11:1; grafite/branco: 14,76:1; secundário/painel: 5,69:1. Impressos mantêm seus estilos próprios.
- Transferência de líquido de terceiros para propriedade/CAD/PRO: transação atômica, bloqueios na ordem CAD/PRO → armazém → entrada → posição, versão e idempotência por usuário/intenção. O débito do terceiro precede o ajuste positivo no ledger, mantendo a ocupação do silo. O crédito não é produção; relatórios e médias permanecem iguais. Estorno restitui ambos os saldos somente se houver saldo livre no destino. Permissões de cargas e transferências são exigidas conjuntamente; a reversão genérica do crédito fica bloqueada.
- Migration `graos0018_transferencia_terceiros` aditiva aplicada localmente após backup verificado. Movimentos anteriores conservados, com vínculo opcional. Nenhum registro operacional ou usuário real foi criado, editado ou excluído nos testes.

## Backups e verificações

- Backup anterior às alterações: `backups/agro-ai-pro-2026-10-05-230051-453693`, restauração isolada aprovada no relatório `verificacao-restauracao-20261005-230101-470260.json`.
- Na retomada, os serviços locais estavam desligados. A cópia física `backups/agro-ai-pro-2026-10-06-072607-774709` passou por hashes/CRC, mas o verificador exige dump lógico para o ensaio de restauração. Depois de iniciar PostgreSQL/Redis existentes, foi gerado novo backup completo: `backups/agro-ai-pro-2026-10-06-072723-649778`, com SHA256, ZIP CRC e restauração isolada aprovados em `verificacao-restauracao-20261006-072737-607788.json`. As cópias anteriores foram preservadas.
- `npm.cmd --prefix frontend test`: quatro conjuntos aprovados, incluindo entradas simples/compartilhadas, terceiros legados, descontos, PH, cancelamento, duas vias sem valores monetários e escape de textos.
- `tsc.cmd --noEmit -p frontend/tsconfig.json`: aprovado.
- `docker compose -p agro-ai-pro build frontend`: TypeScript e Vite aprovados.
- `git diff --check`: aprovado.

## Validação da transferência e conferência visual

- Backup anterior ao novo escopo: `backups/agro-ai-pro-2026-10-06-124944-745906`, relatório `verificacao-restauracao-20261006-124958-126475.json`. Antes das operações de ambiente: `backups/agro-ai-pro-2026-10-06-125826-286647`, relatório `verificacao-restauracao-20261006-125834-369541.json`. Antes da migration/atualização local: `backups/agro-ai-pro-2026-10-06-130118-351283`, relatório `verificacao-restauracao-20261006-130126-584043.json`. SHA256/CRC e restauração PostgreSQL isolada aprovados.
- 82 testes de terceiros, ledger, correções de transferências e alterações/downloads de vendas aprovados em PostgreSQL 17 temporário, sem rede, portas ou volumes da aplicação. Incluem concorrência, reenvio, conservação dos saldos, capacidade, relatório de produtividade, permissões e estorno com reservas. O contêiner foi removido somente após conferir sua etiqueta de validação.
- Após reforçar a permissão do reenvio de estorno, os 13 cenários de terceiros foram verificados em SQLite isolado. Os dois casos afetados pelo ajuste final dos testes foram reexecutados e aprovados, incluindo reenvio negado depois de revogar a permissão.
- Frontend (quatro scripts), TypeScript, build Vite/Docker, Django check e consistência de migrations aprovados. Corrigida a serialização UUID no hash da transferência durante os testes.
- Página temporária fictícia conferiu troca de propriedade limpando CAD/PRO anterior, opções vinculadas, limite de saldo, decimal pt-BR (`200,5`), confirmação simulada, proteção de alterações e ocultação da ação sem permissão. Sem acesso ao banco real; página, aba e servidor temporários removidos.
- Aplicativo autenticado conferido após atualização na porta 5174. Romaneios de entrada compartilhada e de terceiros: duas vias completas, cliente primeiro, arquivo segundo, sem valores monetários; dimensões de cada via 718 × 503 px e scroll correspondente, sem transbordamento. Identificação CAD/PRO sem kg e motorista antes da placa confirmados. Responsividade 360/768/1366 px sem rolagem horizontal; override do navegador restaurado. Tema observado: cabeçalho RGB(22,78,99), fundo RGB(243,245,247).
- Evidência visual privada: `backups/romaneio-entrada-20261006.jpg` (não enviada ao Git). Impressão física/diálogo nativo e download final em disco não executados; PDF de vendas validado em teste como uma página A4 com duas vias.

Validações locais concluídas. Atualização autorizada na branch `codex/melhorias-gestao-transferencias-20261003` e PR 29, com descrição anterior preservada. Sem merge ou publicação em produção.
