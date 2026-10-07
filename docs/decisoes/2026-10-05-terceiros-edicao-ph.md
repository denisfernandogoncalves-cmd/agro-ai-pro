# Entradas de terceiros, PH por cultura e acesso a Nova venda

Data: 05/10/2026.

## Comportamento

- Nova venda aparece imediatamente após o título da tela, antes dos filtros e totais. O formulário continua recolhível, preservando seus campos e rascunhos.
- Entradas de terceiros têm ações Editar entrada e Excluir entrada, controladas pelas permissões cargas.editar e cargas.excluir.
- Edição recalcula descontos e peso líquido no servidor; ajusta o saldo somente pela diferença do líquido. Nome, data, qualidade, transporte e observações podem ser corrigidos. Exige motivo e versão atual.
- Exclusão é estorno da entrada atual: mantém o registro e todos os movimentos, retirando seu saldo do estoque físico. Retiradas ativas precisam ser estornadas antes. Não apaga dados.
- Mudança de armazém exige estorno e novo registro. Cultura/safra não podem mudar enquanto houver retiradas ativas; o novo líquido nunca pode ficar abaixo do que já foi retirado.
- Versão incrementada em edições, saídas e estornos protege contra formulários desatualizados. Bloqueios de armazém/entrada mantêm capacidade e saldo; a mesma chave de reenvio não duplica movimentos.
- Histórico imutável registra motivo, autor, saldos e snapshots antes/depois da edição. Estoque de terceiros permanece separado e não entra na média de produção própria.
- PH aparece e é utilizado somente para Trigo nas cargas próprias, terceiros e vendas/romaneios. Milho e Soja ignoram PH no cálculo e novos registros não armazenam a medição. Valores históricos não recebem limpeza retroativa. Qualidade de vendas continua apenas demonstrativa, sem desconto.
- PH mínimo e Desconto por ponto de PH foram retirados do formulário de terceiros. Configurações históricas de trigo são preservadas ao editar; novas entradas mantêm os padrões do cálculo.

## API e migração

PATCH /api/graos/terceiros/entradas/{id}/ recebe os dados completos do formulário, versao e motivo. DELETE no mesmo endereço recebe versao, motivo e data_movimento. Ambas exigem Idempotency-Key; exclusão retorna o registro preservado com saldo zerado.

Migration graos0017 adiciona versão da entrada, snapshots dos movimentos e tipo edicao. Aplicada localmente; nenhuma entrada operacional foi editada/excluída para testes.

## Preservação e verificações

Backup privado antes da migração/atualização: backups/agro-ai-pro-2026-10-05-100912-095887. Código atual, banco e uploads incluídos, hashes/CRC verificados e restauração PostgreSQL isolada aprovada em verificacao-restauracao-20261005-100921-363057.json.

Comandos: manage.py migrate --noinput; manage.py makemigrations --check --dry-run; manage.py test --noinput; npm --prefix frontend test; docker compose build frontend; git diff --check.

114 testes direcionados aprovados: edições com/sem retirada, rejeição de versão antiga, permissões, reenvio, exclusão após estornos e PH somente em trigo. Frontend, TypeScript/build Docker e consistência de migrations aprovados. Suíte completa PostgreSQL aprovada: 567 casos, 562 aprovados e 5 ignorados. Conferência autenticada confirmou Nova venda antes dos filtros, edição preenchida, confirmação compacta de exclusão, PH visível somente para trigo e responsividade em 360/1366 px. Nenhum registro real foi alterado para testar.

Não houve merge ou publicação em produção. Atualização local na porta 5174 e branch de trabalho do PR 29.
