# Motoristas excluídos e distribuição do cabeçalho — 15/10/2026

Solicitação agendada para 12h15, com correção expressa do Product Owner:
distribuir informações do faturamento na largura disponível, sem ampliar fontes.

## Resultado

Cadastro de motoristas apresenta Excluir motorista para os ativos. A confirmação
explica que a ação inativa o cadastro e preserva registros anteriores. Inativos
ficam em Motoristas excluídos / inativos, seção recolhível inicialmente fechada,
com contagem e opção Reativar motorista. A edição existente continua disponível.

DELETE `/api/transportes/motoristas/{id}/` passa a executar exclusão lógica,
com `versao_correcao_original` obrigatória e bloqueio transacional. Exige
permissão excluir; permissão editar não autoriza DELETE. Versão obsoleta retorna
409. A resposta traz o motorista preservado com ativo=false e versão atual.
Reativação reutiliza PATCH versionado e permissão editar. Sem mudança de schema.
Nenhum motorista real foi excluído, inativado ou reativado automaticamente.

Faturamento mantém o título e usa três colunas em duas linhas:
empresa / embalagens / data; produto / quantidade e dosagem / safra.
Na tela, a grade vira uma coluna em telas pequenas; impressão mantém a grade.
PDF usa os mesmos grupos, com fontes existentes: título 17 pt, informações 9 pt.
Empresa e total recebem negrito e fundo discreto no PDF, sem aumento de fonte.
Tabela, coordenadas, totais, snapshot, sugestão/editabilidade de embalagens e
rodapé continuam preservados. Textos são escapados e nomes longos quebram linha.

## Validação

- Backup privado `backups/visual-20261015-121534`: código, uploads, banco,
  diff, integridade ZIP, catálogo pg_restore e SHA-256 verificados.
- PostgreSQL exclusivo: `scripts/test_backend_isolado.py
  apps.transportes.test_motoristas apps.estoque.test_faturamento` — 29 aprovados.
- PDF: `apps.estoque.test_faturamento_cabecalho` — dois aprovados, verificando
  alinhamento em três colunas, fontes, limites A4, conteúdo e nomes longos.
- Frontend: npm test e npm run build aprovados na imagem Docker. Casos de
  renderização verificam separação dos ativos/inativos, seção fechada, ações e
  informações do cabeçalho; suíte de embalagens editáveis preservada.
- Django check e makemigrations --check --dry-run aprovados; sem migrations.
- PDF fictício em `backups/revisao-cabecalho-20261015`: renderizado com pypdfium2
  e PNG inspecionado, uma página A4 paisagem, sem corte ou sobreposição.
- Frontend local 5174 atualizado, HTTP 200; backend saudável; diff sem erros.

Arquivos: backend/apps/transportes/{motoristas.py,test_motoristas.py};
backend/apps/estoque/{faturamento_pdf.py,test_faturamento_cabecalho.py};
frontend/src/api/transportes.ts, pages/Transportes/CadastroMotoristas.tsx,
pages/Estoque/FaturamentoInsumos.tsx, styles.css e scripts/test-components.mjs.

Sem alterações operacionais reais, commit, push, merge ou produção. Não houve
teste visual autenticado da tela; PDF demonstrativo foi conferido visualmente.
Agendamento único desativado após a conclusão.
