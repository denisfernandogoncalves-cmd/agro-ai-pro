# Motoristas, apelidos e seleção do transporte

Escopo: cadastro independente de motorista com nome, apelido opcional e situação;
reutilização do cadastro de caminhões e seleção independente de placa/motorista
nas cargas próprias e na conferência de fretes pendentes. Critérios: persistência
do apelido, edição protegida contra versão antiga, seleção dos ativos, preservação
dos textos históricos, acesso de consulta para Cargas sem liberar escrita.

Implementado na árvore operacional `.worktrees/runtime-origin-main`, branch
`codex/modernizacao-visual-runtime`, preservando alterações anteriores.

- API `/api/transportes/motoristas/`: GET/POST; detalhe GET/PATCH, com
  `versao_correcao_original` para editar. Campos `nome`, `apelido`, `ativo`.
  Exclusão física indisponível; inativação mantém o histórico.
- Migration `transportes.0007_motorista` aditiva: tabela independente e cópia dos
  nomes já presentes em caminhões, lançamentos e remunerações; apelidos em branco.
  Aplicada localmente. Nomes/placas históricos das cargas não são substituídos.
- Interface em Transportes → Motoristas e caminhões; seleção em Cargas e
  Conferir cargas e vendas. Apelido aparece ao lado do nome, mantendo o nome
  completo gravado nos documentos. Cadastros inativos deixam de ser oferecidos
  para novas escolhas; valor histórico atual permanece disponível na edição.
- Frete mantém a exigência de remuneração cadastrada no mesmo mês e placa;
  selecionar cadastros não cria salário, receita ou comissão automaticamente.
  Corrigir a placa existente da viagem continua sendo edição da origem.

Arquivos: `backend/apps/transportes/{models,motoristas,urls,test_motoristas}.py`,
`backend/apps/transportes/migrations/0007_motorista.py`,
`backend/apps/accounts/access.py`, `frontend/src/api/transportes.ts`,
`frontend/src/components/SelecionarTransporte.tsx`,
`frontend/src/pages/Transportes/{CadastroMotoristas,TransportesPage,ConferenciaFretes}.tsx`,
`frontend/src/pages/CargasColhidas/CargasColhidasPage.tsx`.

Backups privados com ZIP CRC, leitura integral do dump e hashes SHA256:
`backups/agro-ai-pro-2026-10-14-231604-514825` (antes das alterações) e
`backups/agro-ai-pro-2026-10-14-232053-900326` (antes da migration), dentro da árvore operacional.

Validações: quatro testes de motoristas aprovados após ajuste da fixture de
permissões; oito testes de fretes aprovados na execução inicial. Testes em SQLite
isolado via `manage.py test ... --settings=config.settings.test --noinput`.
`docker compose -p agro-ai-pro build frontend`: suíte frontend completa e
TypeScript/Vite aprovados. `manage.py check` aprovado. Migration aplicada no
PostgreSQL local após backup. Frontend local 5174 atualizado.
Build/test nativos Windows falharam por bloqueio no dist e resolução SSR do React;
validação concluída pelo Docker oficial, sem mudar dependências ou ferramentas.
Conferência visual autenticada não executada. Sem commit, push, merge ou produção.
