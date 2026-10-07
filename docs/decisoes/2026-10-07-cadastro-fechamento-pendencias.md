# Cadastro de terceiros, fechamentos, retiradas, pendências e recuperação

Cinco melhorias autorizadas em 07/10/2026. Acrescentado pelo Product Owner:
downloads PDF/Excel de todos os romaneios de entrada, inclusive cargas próprias.
Backup anterior: `backups/agro-ai-pro-2026-10-07-094436-448844`, hashes/CRC e
restauração isolada aprovados. Preservar mudanças anteriores e dados reais.

Aceite: cadastro com código único e nome não único; vínculo explícito dos
recebimentos antigos, sem presumir identidade pelo nome. Resumos/extratos
podem filtrar o cadastro. Fechamentos por armazém/produto/safra e intervalo
registram saldo e avisam alterações. Comprovantes de retiradas têm dados do
movimento, assinatura e duas vias. Pendências têm responsável, situação e
histórico. Verificação semanal existente passa a ensaiar uploads junto ao banco.
Downloads próprios devem gerar PDF real e Excel .xlsx, respeitando impressão.

Reutilizar models, autorização, confirmações e exportadores existentes.
Migrations aditivas; nenhuma união automática de pessoas ou ajuste de saldo.
Testes isolados de identidade/homônimos, saldo, fechamentos, permissões,
exportação, recuperação e frontend. O conjunto de cinco melhorias continua
concluído após a auditoria: telas e integração de identidade, fechamentos,
pendências e comprovantes de retirada validados. Evidências e limites em
`2026-10-07-correcoes-auditoria.md`. A estrutura aditiva graos0021 foi
aplicada sem vincular automaticamente recebimentos antigos.

## Pedido adicional: PDF ou Excel do romaneio — concluído

Comprovantes de cargas próprias/compartilhadas e a lista de romaneios agora
usam endpoints autenticados `/api/graos/cargas-colhidas/{id}/pdf/` e
`/api/graos/cargas-colhidas/{id}/excel/`. O componente compartilhado oferece
**Baixar PDF** e **Baixar Excel (.xlsx)** também para os terceiros e vendas.
Excel usa o formato moderno .xlsx; o download próprio antes gerava HTML.
Reutilizados os exportadores de duas vias, sem alterar dados da carga.

Dois testes próprios verificam assinatura PDF, conteúdo Excel, ausência de
fórmulas e permissão de impressão. Testes relacionados de terceiros,
pesagem, extrato e contagem passaram em SQLite (43 testes, quatro skips
de concorrência). Frontend/testes/TypeScript/build e imagem Docker aprovados.
Conferência autenticada do romaneio #57 confirma os dois botões; a captura
automática do evento de download no navegador não retornou um caminho.
O mesmo exportador gerou os arquivos para conferência local: PDF renderizado
em uma A4, duas vias sem corte, e Excel com os dados da carga compartilhada.

Backup adicional antes de graos0021:
`backups/agro-ai-pro-2026-10-07-100116-905353`, com SHA256, CRC, restauração
isolada do banco, extração isolada dos uploads e conferência das referências
do banco restaurado. A automação semanal existente foi atualizada para
registrar as contagens e falhar quando faltarem arquivos referenciados.
Nenhum commit, push ou merge realizado.

Validação final: 46 testes aprovados em PostgreSQL, incluindo quatro testes
de concorrência. Usada uma base temporária exclusiva `test_romaneios_*`
pelo runner em `backups/test_download_isolado.py`, para não reutilizar bases
de testes preexistentes. A primeira tentativa com `manage.py test --noinput`
iniciou a recriação da base preexistente `test_agro_ai_pro` e foi interrompida;
seu conteúdo anterior de teste não foi preservado por esse comando. O banco
operacional não foi alvo dessa operação. As verificações finais usaram
somente uma nova base exclusiva. `makemigrations --check --dry-run` sem alterações
pendentes e `git diff --check` aprovado. Cinco testes do verificador de backup
aprovados. O botão de Excel também foi acionado na tela autenticada sem erro.
