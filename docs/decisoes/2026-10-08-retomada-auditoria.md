# Retomada da auditoria e melhorias — 08/10/2026

Checkout: `D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main`.
Branch: `codex/modernizacao-visual-runtime`. Alterações anteriores preservadas.
Esta entrega valida incrementos da auditoria; o escopo geral continua em implementação.

## Critérios e alterações verificadas

- Cobertura das cotas CAD/PRO distingue disponível compartilhado, reserva do próprio contrato, comprometido com outros, cobertura e falta após reserva própria. Não cria reservas nem movimenta estoque. Base: cultura exata conforme cadastro, todas as safras/armazéns. Disponível compartilhado não significa cobertura exclusiva de vários contratos. Cancelamentos e entregas parciais recalculam as reservas. Sem permissão de saldos, os campos de estoque são ocultados pela API.
- Relatórios financeiros: filtros aplicáveis, totais completos, faixas de vencimento e agrupamento por fornecedor/data, com paginação no banco. Homônimos não são unidos pelo nome. PDF/Excel identificam a base; exportações completas respeitam seus limites.
- Relatórios de máquinas: custos disponíveis por hora, manutenção realizada na data de conclusão, abastecimentos e horas até manutenção prevista. Ausência de horas/custos fica explícita; não se presume consumo do motor nem custos ausentes.
- Operações: comparação de insumos por produto/lote/unidade e movimento real, com documento de origem. Custo ausente não vira zero. Área realizada separada e duração planejada não existem no modelo atual e não foram inventadas.
- Importações: exportação privada de conferência com linhas originais/normalizadas, erros e avisos, filtro de status e consulta consistente, sem confirmar lote. Limite de 100.000 linhas. Nginx admite multipart de planilhas de até 10 MB na rota específica.
- Validação numérica finita e precisão nas liquidações/manutenções; referência de datas compatível com 29/02. Edição financeira recebe controle otimista opcional e lock, com resposta 409 para versão antiga; clientes legados sem timestamp continuam compatíveis.
- Contratos: inativação exige versão/justificativa e registra histórico; referências antigas exatas de CAD/PRO inativo são preservadas em alterações de outros campos.
- Interface: matriz de permissões salvas sem alterar acessos; dashboard com navegação lateral e quadros existentes de mercado/clima reintegrados; correção da exportação de TabelaRelatorio que impedia os testes do frontend.
- Clima/Mercado: fonte, instante de registro e idade do dado sem limite obrigatório inventado. Falhas de atualização manual mostram horário da tentativa nesta sessão e preservam a última consulta válida. Troca de propriedade limpa a previsão anterior e descarta resposta de atualização de outra propriedade. Não se consulta serviço externo automaticamente. Falhas de atualização não são um histórico persistido.

Arquivos principais: backend/apps/vendas/gestao_contratos.py e test_gestao_contratos.py; backend/apps/relatorios/{selectors,agrupamento_financeiro,excel,pdf,serializers,tests}.py; backend/apps/core/{valores,edicao_concorrente}.py; backend/apps/financeiro/{serializers,services,views}.py; backend/apps/maquinas/services.py; backend/apps/importacoes/views.py; docker/nginx/default.conf; scripts/test_backend_isolado.py; frontend/src/pages/{Clima, Mercado, Relatorios, CadastrosAgricolas}; frontend/src/components/{MatrizPermissoes,ExportacaoConferenciaImportacoes}; frontend/src/utils/datas.ts; frontend/src/App.tsx.

## Evidências

- Backup inicial lógico: `backups/agro-ai-pro-2026-10-08-072032-003983`, hashes/ZIP/dump aprovados, restauração isolada aprovada. Cópia física anterior preservada; esse formato não é compatível com o ensaio lógico.
- Backup pré-atualização: `backups/agro-ai-pro-2026-10-08-084130-883684`, restauração isolada aprovada.
- `docker compose -p agro-ai-pro run --rm --no-deps backend python scripts/test_backend_isolado.py`: 688 casos, 683 aprovados e 5 skips, zero falhas, 384,895 s. Inclui o teste inicial da reserva própria. O log de falha simulada da importação faz parte do teste aprovado de rollback.
- Após acrescentar dois testes de reservas alheias/cancelamento/permissões: `... scripts/test_backend_isolado.py apps.vendas.test_gestao_contratos`: 13 aprovados, 5,242 s. Não é necessário repetir a suíte completa por adição isolada de testes.
- `... python backend/manage.py check`: sem problemas. `... makemigrations --check --dry-run`: No changes detected. Nenhuma nova migration nesta retomada.
- Frontend: testes de componentes, 16 cenários de autenticação, 6 de rascunhos, usabilidade, TypeScript e Vite aprovados nos builds de contratos e clima/mercado. Testes da idade incluem ausência, data inválida, futuro e limites de minuto/hora/dia.
- `git diff --check`: sem erros, somente avisos LF/CRLF de arquivos anteriores.

## Pendências do escopo geral

Paginação das listas operacionais de todos os módulos; concorrência nas demais edições; conferência de áreas declaradas/calculadas/vinculadas; investigação contínua das diferenças de estoque; obrigações e divergências consolidadas por comprador; renegociação financeira com origem; sugestão de lote por validade com confirmação; mapeamento de colunas; histórico persistente de falhas de atualização; mapa e áreas por cultura no dashboard. Recursos previamente existentes devem ser auditados/reutilizados antes de implementações adicionais. A matriz mostra configuração salva, não prévia de formulário ainda não salvo. Não implementar política nova de acesso por propriedade por suposição.

Transferências externas continuam estoque e não aumentam produção, área ou produtividade. Sem reclassificação histórica, dados fictícios operacionais, EXE, custos novos, commit, push, merge ou publicação em produção.


## Aplicação e conferência final

Backup imediatamente anterior à última atualização: `backups/agro-ai-pro-2026-10-08-085415-132954`; seis arquivos íntegros e restauração isolada aprovada. Builds finais incluíram os refinamentos simultâneos do dashboard, preservados; componentes/testes/TypeScript/Vite aprovados. A integração de QuadrosPainel agora fica no próprio PainelPage, sem duplicar o componente no App.

`FRONTEND_PORT=5174 docker compose -p agro-ai-pro up -d --no-deps --wait --wait-timeout 60 frontend`: aplicado localmente e saudável. Backend/PostgreSQL/Redis saudáveis e `/api/health/` retornou status ok. Nenhuma migration adicional nem operação real de negócio efetuada.

Navegador autenticado: dashboard, Mercado, troca de propriedade no Clima e Contas a pagar conferidos. Mercado/Clima a 360 px: documento 345 px, sem extravasamento. Contas a pagar mostrou busca, status, agrupamento, faixas e estado vazio reais, sem CAD/PRO/cultura inaplicáveis. Nenhum título fictício criado; conteúdo monetário validado no banco isolado.

A revisão visual encontrou previsões históricas misturadas ao período atual. Corrigido: Clima mostra somente hoje até hoje+6 dias por padrão, e oferece inclusão explícita das previsões históricas. Na propriedade SAGRILO, a consulta final mostrou 08/10 a 13/10 disponíveis para a janela até 14/10, sem inventar previsão faltante; o histórico de setembro reapareceu apenas com a opção selecionada. Corn Belt identifica intervalo e número de datas registrados; não chama qualquer acúmulo histórico de sete dias. Não houve atualização externa de previsões/cotações nos testes. Horário e idade referem-se ao registro local; data de referência da cotação permanece separada.

Capturas privadas: `backups/validacao-20261008/dashboard.jpg` (primeiro dashboard validado antes dos refinamentos simultâneos finais) e `clima-celular.jpg` (separação atual/histórico). Viewport restaurado após a conferência. Impressão física, download em disco e simulação manual de falha de fornecedor não executados nesta retomada.
