# Romaneio de venda e produção de terceiros

Escopo autorizado: romaneio de saída de venda no mesmo componente de impressão das entradas; recebimento manual de produção de terceiros com saldo e futuras saídas separados, contabilizado no estoque físico e excluído da média das propriedades. Branch codex/melhorias-gestao-transferencias-20261003; incremento específico, sem Sprint pendente no índice. Critérios: peso/data da saída, transporte e notas no romaneio; permissões; saldo separado sem alterar ledger próprio/produtividade; capacidade conjunta; reenvios e concorrência sem duplicação; histórico preservado.

## Implementação

Vendas: seção Romaneios de saída no detalhe da venda, um documento por entrega. Reutiliza ComprovanteLancamento com botão Imprimir romaneio e opção de baixar HTML independente. Peso líquido e sacas são da saída individual, não do contrato inteiro. Transporte, destino, notas, classificação, cultura/safra, CAD/PRO, armazém e movimento constam do documento. Canceladas/excluídas explicitadas como histórico; reservas sem entrega não produzem romaneio. Campos não registrados não são inventados. Comprovante existente preservado; impressão exige permissão imprimir e usa texto escapado/CSP. Diálogo nativo de impressão e gravação final do download não confirmados.

Cargas colhidas: opção Produção de terceiros com formulário de recebimento identificado pelo nome do terceiro, cultura/safra, armazém, data, transporte, documento, observações, peso bruto e classificação para apuração dos descontos e líquido. Não cria propriedade, CAD/PRO próprio, talhão, CargaColhida ou posição do ledger próprio. Campo de peso aceita padrão brasileiro (ponto de milhares e vírgula decimal). Saldo por recebimento, retiradas, histórico e estornos com motivo; sem exclusão física ou edição destrutiva. Saídas de terceiros são retiradas do depósito, separadas de vendas próprias/receitas. Permissão de cadastrar controla entrada/retirada; excluir controla estorno; consultar controla consulta. Sem novas concessões de acesso real.

EntradaProducaoTerceiro guarda saldo não negativo limitado ao peso recebido; MovimentoProducaoTerceiro é imutável, com usuário/data, deltas e saldos anterior/posterior. Chave idempotente, hash da intenção e usuário impedem reuso inconsistente. Transações bloqueiam armazém e recebimento para impedir consumo duplicado. Estorno de entrada após retirada é bloqueado até estornar a retirada. Capacidade considera estoque próprio positivo mais saldo de terceiros sob o mesmo bloqueio; negativo próprio não libera espaço ocupado por terceiros. Armazém inativo impede nova movimentação. Recebimentos e movimentos participam do backup Excel administrativo pelo catálogo de modelos de negócio e do backup privado integral.

Painel: Estoque de terceiros e Estoque físico armazenado (próprio + terceiros) nas consultas gerais por safra, respeitando permissões. Consulta de propriedade não atribui saldo de terceiro a propriedade própria. Indicadores de produção e saldos por propriedade continuam próprios. Relatórios de produção/produtividade e médias globais conservam apenas as cargas próprias.

Migration graos0015_producao_terceiros aditiva: dois modelos e restrições, sem alteração de grãos existentes. Aplicada localmente. Serviços backend/frontend saudáveis; frontend reconstruído na porta 5174. Sem dependência nova.

## Validação

- npm --prefix frontend test: componentes, 16 autenticação, 6 rascunhos e usabilidade aprovados. Novos cenários conferem peso da saída diferente do contrato, sacas, destino, notas com zeros, cancelamento e bloqueio sem permissão de imprimir.
- npm --prefix frontend run build: TypeScript/Vite aprovado; imagem Docker frontend construída.
- python manage.py test apps.graos.test_terceiros apps.graos.test_cargas_colhidas apps.graos.test_cargas_concorrencia apps.core apps.accounts.test_user_access apps.relatorios.test_operacionais: 105 casos PostgreSQL aprovados.
- python manage.py test: 560 casos PostgreSQL, 555 aprovados e 5 skips por condições de ambiente. Logs de falha simulada de importação pertencem ao teste de rollback, sem falha da suíte.
- makemigrations --check --dry-run: sem diferenças. Checks Django e git diff --check aprovados.
- Casos de terceiros: entrada/saldo/estoque; relatórios, produção e posições próprias idênticos antes/depois; capacidade compartilhada com carga própria; saída/estornos preservando histórico; saldo insuficiente; reenvio sem duplicação e hash inconsistente rejeitado; duas saídas concorrentes e reenvio concorrente no PostgreSQL; peso zero/negativo e ausência de permissão rejeitados.
- Navegador autenticado: indicadores novos, entrada manual de terceiros, validação inline e layout em 360 px; romaneio individual de saída histórica com situação/quantidade corretas. Nenhum usuário, permissão ou recebimento real criado/alterado para teste. Viewport restaurado. Demonstração de entradas/saídas com persistência feita exclusivamente no banco de testes isolado.

## Backups privados

Inicial: backups/agro-ai-pro-2026-10-05-085339-872739, restauração verificacao-restauracao-20261005-085348-391778.json.
Antes da migration: backups/agro-ai-pro-2026-10-05-090003-518908, restauração verificacao-restauracao-20261005-090011-327651.json.
Antes da atualização frontend: backups/agro-ai-pro-2026-10-05-090949-510938, restauração verificacao-restauracao-20261005-090956-509582.json. SHA256/CRC e restauração isolada aprovados; código, banco e uploads preservados. Evidências privadas romaneio-venda.jpg e terceiros-celular.jpg nessa pasta.

Arquivos: graos/models, services, urls, terceiros, test_terceiros e migration0015; accounts/access; core/auditoria e painel; frontend API terceiros, ProducaoTerceiros, RomaneioVenda, CargasColhidas, Vendas, Painel, ComprovanteLancamento e testes de usabilidade. Sem merge/produção.


## Ajustes solicitados em 05/10/2026

Terceiros: identificação de novas entradas somente pelo nome, sem solicitar propriedade de origem ou CAD/PRO. Campos históricos conservados no banco. Novas entradas informam peso bruto, umidade, impureza, avariados e PH; a mesma função calcular_peso_liquido das cargas próprias apura descontos, peso líquido e regra aplicada. Prévia autenticada /api/graos/terceiros/previa/ não grava movimentos. API calcula o líquido, ignorando tentativa de enviar líquido manual; capacidade e saldo usam somente o líquido. Migration graos0016 aditiva e nullable preserva registros anteriores sem presumir medições desconhecidas. Formulário em três colunas no computador, duas em telas intermediárias e uma no celular.

Vendas: novos campos peso_bruto_kg, tara_kg, umidade_percentual, avariados_percentual, quebrados_percentual e ph nas entregas. Líquido = bruto menos tara; qualidade apenas demonstrativa, sem desconto. Frontend calcula, serializer apura novamente e serviço confere consistência; tara negativa, tara igual/superior ao bruto e percentuais fora de 0 a 100 são rejeitados. API mantém compatibilidade com integrações anteriores sem pesagem. Migration vendas0009 aditiva e nullable, sem recalcular vendas antigas. Campos constam do romaneio. Edição de entregas novas conserva pesagem e qualidade e exige líquido consistente. Rateio PARTICULAR distribui tara proporcionalmente e conserva totais; reservas e saídas continuam pelo líquido. Rascunho privado aceita novos campos na whitelist sem relaxar isolamento entre contas. Filtros podem ser expandidos/recolhidos mantendo valores; transporte/notas e pesagem possuem blocos separados e responsivos.

Validação dos ajustes: 85 testes PostgreSQL de vendas/terceiros aprovados; suíte frontend e build TypeScript/Vite aprovados, incluindo cálculo com tara zero, decimal brasileiro e ausência de desconto de qualidade. Prévia de terceiros comparada com o mesmo cálculo das cargas próprias, inclusive PH, sem gravar estoque. Teste rejeita alteração manual do líquido e umidade fora da tabela. Comparação inicial de snapshot corrigida para comparar valores numéricos, pois Decimal normaliza casas decimais.

Backups adicionais com SHA256/ZIP e restauração isolada aprovada: backups/agro-ai-pro-2026-10-05-092146-602642, backups/agro-ai-pro-2026-10-05-092640-850583, backups/agro-ai-pro-2026-10-05-092934-351249 e backups/agro-ai-pro-2026-10-05-093559-564709. Relatórios de restauração ficam dentro das respectivas pastas privadas. Alterações locais preservadas; nenhuma entrada, venda, usuário ou permissão real criada para teste funcional.

Validação final: suíte completa PostgreSQL 563 casos, 558 aprovados e 5 skips. Últimos ajustes de whitelist/rateio: 21 testes core/conferência e particular aprovados. Frontend/test/build/imagem Docker aprovados. Migrations consistentes. Backup final backups/agro-ai-pro-2026-10-05-094520-596333, restauração verificacao-restauracao-20261005-094528-479823.json. No navegador: 1.000 kg bruto menos 200 kg tara = 800 kg líquido, sem desconto com umidade 20%.

Teste adicional de pesagem PARTICULAR aprovado: soma de bruto 50,001 kg, tara 0,001 kg e líquido 50 kg preservada em duas propriedades, com qualidade sem descontos. Último backup privado: backups/agro-ai-pro-2026-10-05-095022-062400; restauração verificacao-restauracao-20261005-095029-663322.json aprovada.
