# Auditoria técnica e melhorias — AGRO-AI-PRO — 07/10/2026

Checkout: .worktrees/runtime-origin-main; branch codex/melhorias-gestao-transferencias-20261003.
Escopo: revisão dos módulos e componentes compartilhados, suíte geral em PostgreSQL
isolado, frontend, dependências, migrations e navegação local. É auditoria técnica
por código/testes e amostragem visual; não é pentest, auditoria contábil certificada
ou certificação de todos os fluxos manuais. Sem alterar registros operacionais.

## Achados prioritários

| Prioridade | Evidência | Consequência | Proposta |
|---|---|---|---|
| Alta | maquinas/services.py concluir_manutencao converte custo diretamente com Decimal e chama save sem full_clean; views captura somente ValueError | Custo negativo pode escapar do validador do modelo; entradas decimais inválidas podem gerar falha interna | Serializer específico na ação, números finitos, limites de precisão e validação antes de alterar horímetro |
| Alta | financeiro/services.py liquidar_lancamento compara Decimal antes de conferir is_finite; views não trata InvalidOperation/ValidationError Django | NaN/infinito ou precisão excessiva enviados diretamente à API podem gerar erro interno | Validar com serializer da ação e respostas 400 consistentes |
| Média | financeiro/serializers.py usa localdate().replace(year=year-10) | Em 29/02, o ano de referência pode não ter esse dia e a validação pode falhar | Cálculo de referência compatível com ano bissexto e teste com data congelada |
| Média | importacoes/services.py permite 10 MB; docker/nginx/default.conf limita o corpo a 6m | Planilha válida entre 6 e 10 MB pode ser recusada pela interface com HTTP 413 | Alinhar limite por rota, considerando multipart, e mensagem clara |
| Média | relatorios/selectors.py _pagina calcula len da lista inteira; _financeiro materializa tudo; financeiro/maquinas/estoque/cadpro sem paginação explícita | Tempo e memória crescem com o histórico mesmo ao pedir uma página | Paginação no banco, agregações separadas e contratos de API compatíveis |
| Média | vendas/gestao_contratos.py valida novamente cotas/agenda antigas com CADPro ativo=True mesmo em PATCH de outro campo | Inativar um CAD/PRO vinculado pode impedir editar somente alerta/preço | Preservar referências antigas exatas e exigir ativo só para vínculos novos |
| Média | vendas/views.py ContratoComercialViewSet.destroy apenas grava ativo=False | Inativação não acompanha o controle de versão usado na edição | Versão e justificativa para inativação, transação e histórico coerente |
| Média | financeiro/producao/maquinas possuem edição comum sem versão otimista; transições importantes têm locks, mas telas antigas podem sobrescrever campos | Dois usuários podem editar o mesmo cadastro com dados antigos | Ampliar aviso de alteração simultânea e resposta 409 preservando rascunho |
| Melhoria | Relatórios mantém filtros de CAD/PRO/cultura/transporte visíveis em seção financeira, mas esses campos não filtram títulos | Usuário pode interpretar filtro inaplicável como efetivo | Mostrar apenas filtros aplicáveis à seção e listar sua base explicitamente |

Os achados de validação acima derivam do código, ainda sem testes novos de reprodução
específica. A suíte existente não garante cobertura desses cenários. Priorizar a
reprodução isolada antes de correções. Não executar chamadas inválidas na base real.

## Cobertura por módulo e próximos incrementos úteis

| Área revisada | Recursos existentes a preservar | Melhorias propostas |
|---|---|---|
| Propriedades, talhões e CAD/PRO | Vínculo por código, geometria, histórico, validações de área | Conferência conjunta área declarada/calculada/áreas vinculadas com origem e divergência; sem recálculo automático |
| Cargas e terceiros | Descontos, duas vias, transferências externas, estorno e versões | Pesagem com limites opcionais por operação; evolução de qualidade com base comparável e campos ausentes explícitos |
| Produção, armazém e transferências | Ledger, saldos físico/comprometido, contagens e conferência diária | Roteiro de investigação da diferença mostrando documentos causadores e continuidade entre datas; sem ajuste automático |
| Vendas e contratos | Cotas, alertas, agenda, histórico e conferência comprador | Cobertura explicando também reservas vinculadas ao próprio contrato; visão consolidada de obrigações e divergências por comprador |
| Financeiro e acertos | Liquidação, parcelas, leitura de boleto, comprovantes e vínculos manuais | Contas a pagar com totais pendente/vencido/a vencer, faixas de atraso, fornecedor e agenda; renegociação com referência ao título original sem apagar histórico |
| Insumos e faturamento | Estoque mínimo, validade, lotes e rastreabilidade | Custo de consumo por talhão/safra com documento de origem; sugestão de lote por validade, exigindo confirmação |
| Operações agrícolas | Planejado, execução, insumos e custos | Comparar quantidade, área, duração e custo planejados/realizados sem misturar unidades |
| Máquinas | Horímetro, abastecimentos, manutenção e custos | Custo por hora com componentes disponíveis; combustível por período; manutenção por horas restantes, sem inventar intervalos |
| Importações | Preview, hash, erros, advertências, confirmação atômica | Mapa de colunas e catálogo de erros exportável; indicação exata das linhas não confirmadas e limite de upload coerente |
| Clima e mercado | Fonte identificada, timeout e falhas tratadas | Mostrar idade do dado e falha da última atualização junto ao último valor; fonte e unidade explícitas |
| Assistente e painel | Regras determinísticas e evidências | Acesso direto aos registros que motivam cada alerta e distinção entre regra, cálculo e estimativa |
| Usuários, histórico, backups e exportações | Permissões por ação, anexos privados, auditoria e restauração isolada | Matriz de permissões legível; revisão de acesso por propriedade/CAD caso adotada pelo PO; exportação com status/base monetária e indicação de ausência de dados |
| Interface compartilhada | Abas acessíveis, filtros favoritos, proteção de rascunhos | Busca na navegação; filtros específicos por seção; resumo fixo sem ocultar ações; testes de teclado e celular em fluxos financeiros |

A revisão de permissões por propriedade seria mudança de política, não correção
automática: o comportamento atual usa módulos e ações. Não ampliar nem restringir
acessos operacionais por suposição. Transferências externas continuam estoque e
nunca somam produção, área ou produtividade.

## Verificações

- Backup de código/banco/uploads com hashes e restauração isolada aprovado:
  backups/agro-ai-pro-2026-10-07-214100-338447.
- npm test, TypeScript e build Docker aprovados; backend/frontend/PostgreSQL/Redis
  saudáveis. Sem alterações de dependências.
- npm audit consultado com certificados confiáveis do sistema: zero
  vulnerabilidades reportadas nas dependências frontend nesta consulta. A primeira
  tentativa teve erro de certificado; corrigido usando --use-system-ca, sem desligar TLS.
- makemigrations --check --dry-run: No changes detected.
- git diff --check sem erros; avisos LF/CRLF em arquivos anteriores preservados.
- Aba Contas a pagar conferida autenticada na aplicação, com estado vazio correto,
  filtros e exportações existentes; nenhum título fictício criado.
- Suíte geral: scripts/test_backend_isolado.py apps executou 673 casos em
  PostgreSQL isolado: 668 aprovados, 5 ignorados, zero falhas; duração 360,284 s.
  O log de falha simulada da importação é parte de teste de rollback aprovado.

## Execução dos testes

O runner sem argumentos encontrou zero testes e retornou sucesso; nesta auditoria
foi usado o rótulo explícito apps para descobrir 673 casos. Recomenda-se falhar
quando a descoberta for vazia ou definir esse rótulo como padrão para evitar uma
validação aparentemente aprovada sem executar testes.

## Limites

Não houve teste de carga, pentest, impressão física ou visita manual a cada campo
de todas as telas. PDF/Excel reutilizados na aba nova; download físico específico
não ensaiado. Dependências Python não receberam consulta externa de vulnerabilidades
nesta rodada. Não houve commit/push/merge/publicação. As propostas deste relatório
não significam que todas as melhorias agendadas anteriores foram concluídas.
