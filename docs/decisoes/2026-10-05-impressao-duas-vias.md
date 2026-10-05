# Duas vias na mesma folha A4

05/10/2026. Comprovantes individuais de cargas próprias, compartilhadas/rateadas, entradas de terceiros e romaneios de venda imprimem Via do arquivo e Via do cliente, com os mesmos dados, na mesma e única folha A4. Separação tracejada para corte. Não duplica movimentos ou altera estoque/médias. Relatórios gerais de várias cargas e comprovantes de transferência preservam seu formato.

Componente ComprovanteLancamento recebe duasVias nesses documentos. Folha de 190 × 276 mm, margens de 10 mm, duas vias de 133 mm e separação de 10 mm. Campos curtos em duas colunas; observações/rateios em largura inteira. Fonte adapta de 12 a 9,5 px. A prévia mede transbordamento vertical/horizontal antes de imprimir ou baixar; HTML recebe o tamanho validado. Conteúdo excepcional que ainda não caiba é bloqueado com aviso para revisão, sem ocultar dados nem gerar outra folha. Configurações manuais da impressora podem substituir o A4/margens da aplicação.

Arquivos: frontend/src/components/ComprovanteLancamento.tsx, frontend/src/styles.css, páginas CargasColhidas/ProducaoTerceiros/RomaneioVenda e frontend/scripts/test-components.mjs. Testes frontend aprovados: duplicação completa de dados/observações longas, escape HTML e identificação das vias nos quatro tipos. TypeScript/Vite e Docker aprovados. Verificação DOM de dimensões/transbordamento com observações de aproximadamente 4.000 caracteres e oito propriedades fictícias em carga compartilhada; conferência autenticada de carga existente sem modificar registros. Impressão física e contagem de páginas em PDF nativo não confirmadas; limites A4 foram medidos no navegador.

Backups privados com código/banco/uploads, SHA256/CRC e restauração PostgreSQL isolada aprovados: backups/agro-ai-pro-2026-10-05-124152-448093 e backups/agro-ai-pro-2026-10-05-124658-711850. Novo backup antes da atualização final. Comandos npm --prefix frontend test; npm --prefix frontend run build; docker compose -p agro-ai-pro build frontend; up com FRONTEND_PORT=5174; git diff --check. Ajustes anteriores:567 testes PostgreSQL (562 aprovados, 5 skips), sem mudança backend adicional para impressão.

Branch codex/melhorias-gestao-transferencias-20261003, PR29. Commit/push autorizados, sem merge/produção. Automação única removida porque usuário solicitou execução imediata.


## Refinamento visual solicitado após a conferência

Cabeçalho com identificação da via, campos alinhados com rótulo acima do valor, pesos destacados, tipografia inicial de 15 px e maior separação entre campos. Campos extensos seguem em largura inteira. O ajuste automático usa fonte de 15 até 9,5 px e ativa uma apresentação compacta somente para documentos extensos, preservando a única folha A4. Testes frontend/TypeScript/build aprovados; rateio fictício com oito propriedades e observações de cerca de 4.000 caracteres conferido no DOM sem transbordamento. Backup inicial backups/agro-ai-pro-2026-10-05-130352-766339 com restauração isolada aprovada. Sem migration ou mudança de dados.

Conferência da versão local final: carga #53 em fonte de 13 px, folha com 1.043 px de altura e cada via com 503 px, sem exceder largura ou altura. Evidência privada: backups/duas-vias-layout-melhorado-20261005.png. Backup antes da atualização final: backups/agro-ai-pro-2026-10-05-130810-025227, com hashes/CRC e restauração isolada aprovados. Não foi realizada impressão física.
