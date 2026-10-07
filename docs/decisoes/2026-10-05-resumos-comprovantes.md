# Resumos, ordenação e comprovantes — implementação validada

Seis melhorias autorizadas nas telas de cargas, vendas e transferências: período/resumo de filtros, totais dos resultados, ordenação, detalhes recolhíveis, mensagens junto aos campos e comprovante individual imprimível/baixável. Todas as Sprints do índice estão concluídas; incremento de usabilidade na branch atual.

Aceite: resultados/totais obedecem filtros; ordenação não muda registros; histórico não entra nos totais ativos; detalhes não removem informações; campos inválidos impedem envio e apontam erro acessível; comprovante respeita imprimir, preserva texto como texto, informa status e identidade e não substitui nota fiscal. Reutilizar APIs e dados carregados, sem migrations/dependências. Testar ordenação, limites de período, totais, validação e escape do comprovante; frontend/build; revisão responsiva quando houver sessão válida.

Backup inicial integral com restauração isolada aprovada: `backups/agro-ai-pro-2026-10-05-074358-715370`. Dados existentes preservados. Comprovante baixado como HTML independente, para abrir e imprimir/salvar PDF pelo navegador. Não é arquivo fiscal nem confirmação de quitação.

## Resultado e validação

Implementado em Cargas, Vendas e Transferências: filtros de período com resumo, totais de registros ativos, ordenação, análises/histórico recolhíveis, validação nativa acessível junto aos campos e comprovantes individuais. Vendas usa data do contrato para o período; impressão A4 acompanha a mesma consulta. Transferências contam o par débito/crédito uma vez. Não há total monetário: estas APIs de grãos não fornecem preço/valor de venda; nenhuma regra financeira foi inventada. Favoritos de cargas/transferências preservam as datas.

Arquivos principais: componentes ResumoConsulta, FormularioValidado e ComprovanteLancamento; páginas CargasColhidas, TransferenciasSaldo e Vendas; FiltrosRapidos, estilos, API vendas e whitelist core de favoritos. Validações de negócio continuam no servidor; mensagens locais cobrem as restrições declaradas nos campos HTML. Comprovantes exigem permissão de imprimir, escapam texto e usam CSP sem scripts. Download é HTML independente; PDF pode ser salvo pelo diálogo de impressão.

Validação: npm --prefix frontend test (componentes, 16 autenticação, 6 rascunhos e usabilidade), npm --prefix frontend run build (TypeScript/Vite), apps.core (42 testes PostgreSQL), makemigrations --check --dry-run sem diferenças e git diff --check. Novos casos verificam período inclusivo, ordenação numérica sem mutar entrada, total filtrado, mensagens e escape do HTML; favoritos testam persistência de datas e isolamento por usuário.

Conferência autenticada local: cargas 03/10 removidas pelo início 04/10 com totais zerados; filtro Milho sem resultados; aviso obrigatório de Safra ao sair do campo vazio; comprovantes de carga ativa, transferência excluída e venda excluída; vendas com início 02/10 sem registros anteriores e detalhe oculto. Layout observado em 360, 768 e 1366 px; overrides removidos ao terminar. Nenhuma operação real foi registrada/excluída para teste. Acionamento do download observado, mas gravação final no disco do navegador e diálogo nativo de impressão não foram confirmados.

Backup anterior à atualização local: backups/agro-ai-pro-2026-10-05-075736-774495; SHA256/ZIP e restauração isolada aprovados, relatório verificacao-restauracao-20261005-075744-632779.json. Evidência privada: comprovante-carga.jpg. Frontend Docker reconstruído e saudável em 5174. Sem migrations, dependências novas, mudança de dados, merge ou produção.
