# Substituição do CAD/PRO na propriedade

Causa: ao informar um novo número em Propriedades, o serviço criava/reativava o novo vínculo mas não desativava os anteriores, apesar de documentar vínculo atual único. A lista exibindo todos os vínculos ativos continuava mostrando o número antigo, e o formulário selecionava o primeiro ao editar.

Serviço agora bloqueia a propriedade durante a transação e deixa somente o vínculo escolhido ativo. Vínculos anteriores são inativados, sem exclusão; CAD/PRO oficial compartilhado e vínculos de outras propriedades permanecem inalterados. Trocas repetidas são idempotentes e números anteriores podem ser novamente selecionados, reutilizando o mesmo vínculo. Salvamento por modelo preserva auditoria da inativação.

Após backup e testes, aplicada correção pontual à Fazenda Electra, mantendo 9542825895 como atual e o vínculo 1 inativo para histórico. Verificação transacional confirmou IDs de todos os registros relacionados preservados. Nenhum grupo não excluído utilizava o vínculo antigo. Não houve correção em massa nem alteração de cargas, saldos ou impressões históricas.

Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-225203`, código, banco e uploads verificados. Vinte e três testes de propriedades/CAD/PRO aprovados em banco isolado, incluindo cenário de dois vínculos ativos, preservação da outra propriedade, grupos com vínculo anterior, GET/PATCH, repetição e reversão. Diff conferido. Sem mudanças frontend ou migrations.

## Última alteração como cadastro atual

A pedido do usuário, conferidas todas as propriedades com mais de um vínculo ativo. Restava somente o Sítio Bom Jesus (Electra): CAD/PRO 9542825895 atualizado em 19/10/2026 às 22:38 (Brasília), anterior 1 de setembro. Após backup `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-225607`, reutilizado o serviço já corrigido/testado para manter o último como atual. Transação conferiu todos os IDs dos registros relacionados antes/depois; nenhum grupo não excluído dependia do vínculo antigo. Restaram zero propriedades com múltiplos vínculos ativos. Anteriores mantidos inativos no histórico; nenhuma exclusão, mudança de saldos ou restauração. Regra das futuras alterações permanece no serviço de cadastro, validado pelos 23 testes anteriores; nenhuma nova alteração de código nesta revisão.
