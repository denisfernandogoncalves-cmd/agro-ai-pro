# Busca, filtros, prévias e confirmações — 03/10/2026

Escopo autorizado: seis melhorias de usabilidade, preservando os registros existentes.

## Implementação

- Cargas: busca por número, inclusive `#52`/`Carga #52`, preservando a busca por CAD/PRO, placa e demais textos. Transferências: busca pelo número da movimentação de saída ou entrada e identificação no histórico.
- Cargas e transferências: filtros combinados de cultura, safra e propriedade, contagem e resumo dos filtros ativos, com ação de limpar. Cargas compartilhadas consideram todas as propriedades participantes; transferências consideram origem e destino.
- Edição: comparação da quantidade anterior/nova e simulação dos saldos nas transferências e nos lançamentos de vendas. Na carga, a comparação é do crédito líquido da carga, não do saldo final da posição. A API continua validando as operações antes de gravar.
- Proteção contra perda de alterações nos formulários de propriedades, cargas, transferências, usuários, faturamento, vendas e créditos de produção. Troca de módulo e saída solicitam decisão; recarregamento usa o aviso próprio do navegador. Filtros não contam como edição. Formulários de outros módulos não foram abrangidos neste incremento.
- Avisos próximos às ações bloqueadas nos fluxos ajustados explicam campos pendentes, processamento, restrições e prévias necessárias. Ações sem autorização continuam ocultas.
- Confirmações compactas compartilhadas com Cancelar como foco inicial, Escape e tratamento da desmontagem. Aplicadas a vendas, transferências, usuários e faturamento; exclusão de cargas conserva a conferência específica compacta. O aviso de saída passou a usar esse componente, evitando a confirmação JavaScript bloqueante na navegação interna.

## Validação e limites

`npm.cmd --prefix frontend test` e `npm.cmd --prefix frontend run build` aprovados, incluindo os testes novos em `frontend/scripts/test-usabilidade.mjs`, 14 cenários de autenticação e os cenários de rascunhos. Cobertura dos cálculos de saldo/reserva, propriedades compartilhadas, busca numérica, permissões, registro/limpeza de alterações e aviso de saída. Imagem Docker do frontend reconstruída e serviço local saudável em 5174.

Conferência visual em 1366 px: filtros aplicados à carga #52, edição inicialmente limpa, prévia de transferência de 100 kg e confirmação compacta cancelada. Nenhuma transferência, exclusão, usuário ou permissão real foi alterada para testar. Um aviso JavaScript da versão anterior bloqueou os cliques do navegador integrado; a validação visual final do novo aviso de saída e das larguras menores permanece pendente. Os testes automatizados da proteção passaram após a substituição.

Favoritos de cargas continuam guardando busca e histórico; os três novos filtros rápidos não são persistidos como favoritos neste incremento. Não há alteração de backend, schema ou migration. As suítes backend aprovadas no incremento anterior não foram repetidas localmente para estas mudanças de frontend; CI permanece a verificação adicional.

Backups privados completos e verificados, incluindo código não commitado, banco, uploads e prova de restauração isolada: `backups/agro-ai-pro-2026-10-03-075828-992250`, `backups/agro-ai-pro-2026-10-03-081538-909208` e `backups/agro-ai-pro-2026-10-03-082449-640079`. Evidências visuais no segundo backup: `filtros-cargas.png` e `confirmacao-transferencia.png`. Backups e imagens não devem ser publicados no Git.

GitHub autorizado nesta conversa; merge e publicação em produção não autorizados.

Atualização de validação: em 03/10, no incremento de documentos/Excel, o aviso interno de saída foi conferido em 360 px sem overflow; Cancelar preservou o preenchimento. Carga e documentos também conferidos em 360 px. O bloqueio anterior do navegador foi superado. Evidências adicionais: `2026-10-03-documentos-excel.md`.
