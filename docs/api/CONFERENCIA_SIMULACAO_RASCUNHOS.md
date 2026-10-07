# Conferência, simulação, rascunhos e relatórios salvos

## Endpoints autenticados

| Método e rota | Permissão | Comportamento |
|---|---|---|
| GET `/api/core/conferencia/{posição}/?pagina=1` | Produção e saldos / consultar | Totais de todo o ledger, diferenças do saldo registrado, movimentos em páginas de 25 com saldo acumulado e orientação de correção. |
| POST `/api/core/conferencia/movimentos/{movimento}/estornar/` | Produção e saldos / excluir | Motivo obrigatório (observacoes até 2000 caracteres), chave_idempotencia obrigatória; original preservado. |
| POST `/api/core/simular-venda/` | Vendas / consultar | posição ou nova_posicao, quantidade_kg positiva, tipo saida/rascunho. Retorna saldo antes/depois sem criar posição ou venda. |
| GET/PUT/DELETE `/api/core/rascunhos/{contexto}/` | Contexto / cadastrar | Um rascunho por usuário/contexto; dados restritos aos campos dos formulários de vendas e produção-saldos. |
| POST `/api/core/favoritos/` | Contexto / consultar | Relatórios aceitam configuracao com colunas, orientacao retrato/paisagem e densidade normal/compacta, além dos filtros. |

Rascunhos não guardam credenciais, arquivos ou permissões. A API nunca aceita selecionar outro usuário. O formulário pergunta se deve restaurar ou descartar antes de sobrescrever um rascunho existente. Alterações são gravadas após um segundo, com envio da edição pendente ao sair do módulo; não há garantia de salvar a última edição se o navegador/processo for encerrado abruptamente ou a rede falhar. A fila preserva a ordem entre salvamento e limpeza e interrompe escritas quando muda a geração da sessão. Sucesso no lançamento limpa o rascunho; recuperar o formulário não cria operação.

Na conferência, ajustes/estornos já compõem entradas e saídas: não devem ser somados novamente. As páginas usam a soma anterior como baseline e não limitam os totais aos 30 movimentos recentes da tela antiga. A consulta aponta divergências sem chamar reconciliar_posicao, que altera dados.

O estorno direto respeita regras do serviço existente, impedindo desfazer isoladamente movimentações de cargas e vendas. A tela orienta a correção pelo lançamento correspondente. Transferências exigem tratar as duas posições pelo fluxo próprio; não há botão de estorno individual na conferência.

A conciliação nesta versão é uma comparação visual com saldo do extrato informado manualmente, para a empresa identificada pelo operador (inclusive C.Vale). Aceita formato brasileiro com três decimais e valores negativos; não importa arquivos bancários/cooperativos, não integra empresas e não altera ou grava o saldo do extrato. O saldo comparado é o atual; confira se o extrato tem o mesmo fechamento e as mesmas dimensões. A data identifica o extrato e não reconstrói automaticamente uma posição histórica.

Na venda PARTICULAR, a prévia inclui os saldos físicos de cada propriedade e os inclui no hash de confirmação. Mudanças nas áreas, dimensões ou saldos invalidam a prévia; um conflito atualiza a simulação na interface, exigindo nova conferência. As saídas comuns mostram uma fotografia indicativa do saldo: o lançamento continua sujeito às regras e transações de venda existentes. Rascunhos comerciais não movimentam estoque. A simulação de faturamento de insumos existente permanece sem baixa até confirmar.

Os relatórios favoritos guardam filtros, colunas da tabela de produção por propriedade e preferências de impressão; colunas de outras seções seguem seus esquemas existentes. Configurações inválidas são rejeitadas. A migration core0002 é aditiva e não transforma faturamentos ou vendas existentes.

## Backup verificado

Executar no checkout ativo:

```powershell
D:/PROJETOS/AGRO-AI-PRO/.venv/Scripts/python.exe scripts/backup_verificado.py
```

Cria uma pasta privada ignorada por Git com código atual, diff/estado Git, uploads, dump PostgreSQL custom e manifesto de hashes. Em seguida valida SHA256/CRC e restaura o dump integral em PostgreSQL 17 efêmero, sem rede, portas ou volumes da aplicação. O PGDATA usa tmpfs; somente o contêiner identificado pela etiqueta agro.backup.validation e pelo nome gerado é removido. Nunca restaura sobre o banco operacional nem apaga cópias antigas. Um JSON datado registra a prova da restauração. Falha em qualquer passo é reportada, sem marcar a cópia como restaurável. Cópias físicas offline requerem procedimento próprio e não são aceitas neste ensaio.

Verificação semanal agendada no Codex: domingos, 06h00, America/Sao_Paulo. Requer computador/Codex e Docker disponíveis; indisponibilidade gera falha para análise. Não há limpeza automática de backups nem envio externo das cópias.
