# Favoritos completos — 05/10/2026

Objetivo autorizado: melhorias de usabilidade. Todas as Sprints do índice operacional estão concluídas; este incremento corrige limitações documentadas em cargas/transferências.

Critérios: salvar/restaurar busca, histórico, cultura, safra e propriedade; manter favoritos antigos; isolamento por conta e permissão; confirmação compacta ao excluir favorito; percentuais da simulação de carga em pt-BR. Sem alteração de regra de negócio, dependências ou schema.

Arquivos afetados: serializers de favoritos em core, componentes FiltrosFavoritos/FiltrosRapidos, páginas CargasColhidas/TransferenciasSaldo e testes. API existente e JSON de filtros reutilizados, sem migrations. Favoritos legados sem filtros rápidos restauram campos vazios para evitar misturar a consulta salva com filtros atuais.

Backup inicial: cópia offline íntegra em `backups/agro-ai-pro-2026-10-05-071622-576997`; ensaio de restauração desse formato não suportado. Serviços existentes iniciados e novo dump integral com restauração isolada aprovada em `backups/agro-ai-pro-2026-10-05-071749-774880`, antes das alterações. Dados reais não usados em testes de gravação.

Validação: `npm.cmd --prefix frontend test` e `npm.cmd --prefix frontend run build` aprovados; restauração de favoritos completos/legados verificada por comportamento. `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test apps.core --noinput --verbosity 1`: 42 testes PostgreSQL aprovados; 17 direcionados core/test_evolucao também aprovados. `manage.py check` sem problemas e `makemigrations --check --dry-run` sem mudanças. Diff revisado e `git diff --check` aprovado. Suíte backend completa não repetida por alteração limitada ao módulo core.

Frontend Docker reconstruído e aplicado na porta 5174 após segundo backup verificado `backups/agro-ai-pro-2026-10-05-072035-296731`. Navegador integrado está sem sessão válida; conferência visual autenticada pendente, sem tentar credenciais ou alterar contas. Sem mudanças no banco ou migrations neste incremento; registros existentes preservados. Branch `codex/melhorias-gestao-transferencias-20261003`; atualização do GitHub autorizada na conversa, sem merge/produção.
