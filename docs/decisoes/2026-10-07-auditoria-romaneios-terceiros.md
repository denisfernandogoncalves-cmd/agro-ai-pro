# Auditoria de romaneios, terceiros, fechamentos e conferência

Data: 07/10/2026. Branch: `codex/melhorias-gestao-transferencias-20261003`.
Checkout: `.worktrees/runtime-origin-main`. Objetivo: identificar defeitos e
ordenar melhorias. Não é uma certificação de todos os módulos nem uma entrega
de novas funcionalidades. Alterações locais anteriores preservadas.

## Achados e ações recomendadas

1. **Alta — terceiros distintos são somados pelo nome.** Dois cadastros com
   códigos A e B e nome igual, cada um com saldo de 100 kg, resultaram em uma
   linha de 200 kg no resumo. O extrato e a prévia de pesagem também filtram por
   nome. Evidências: `graos/resumo_terceiros.py:32`,
   `graos/extrato_terceiros.py:31`, `graos/conferencia_pesagem.py:43`.
   Usar o ID do cadastro nos filtros, agrupamentos e formulários; permitir
   vínculo explícito dos registros antigos, sem união automática pelo nome.

2. **Alta — fechamento não protege todos os movimentos.** Uma carga própria
   em período fechado foi aceita com HTTP 201 sem aviso. Uma entrada de Soja
   mudou para Milho com HTTP 200, apesar do fechamento de Milho, pois o aviso
   verifica a classificação anterior. A consulta histórica passa a atribuir
   o movimento antigo ao novo produto por usar os campos atuais da entrada.
   Evidências: `graos/views.py:215`, `graos/terceiros.py:358`,
   `graos/fechamentos.py:17`. Conferir origem e destino, próprios e terceiros,
   sob a mesma transação/trava; definir snapshots de classificação histórica
   e avisar antes de alterações que atinjam fechamentos.

3. **Média — detalhe de pendência gera erro interno.** GET em
   `/api/core/pendencias-conferencia/1/` provoca TypeError: a rota fornece
   `pk`, mas `PendenciasView.get` não aceita o parâmetro. Evidência:
   `graos/pendencias.py:63`. Implementar detalhe com histórico e retorno 404
   para registro inexistente; testar consulta e permissão pela rota real.

4. **Média — reenvio de lançamento confirmado pode ser bloqueado.** Após
   registrar uma entrada e fechar o período, repetir a mesma requisição e
   chave retorna 409, em vez de reconhecer o registro anterior. O aviso ocorre
   antes da verificação de idempotência. Evidência: `graos/terceiros.py:340`.
   Reconhecer o reenvio legítimo sem exigir confirmação de uma nova alteração.

5. **Média — funcionalidades iniciadas ainda não estão disponíveis na tela.**
   Cadastro por código, fechamentos e fila de pendências têm estrutura/API,
   mas não estão integrados ao frontend. Pendências de pesagem são criadas
   apenas no POST de terceiros; cargas próprias, edições e diferenças de
   contagem não alimentam a fila. Comprovantes específicos de retirada ainda
   faltam. Concluir esses fluxos antes de acrescentar mais funcionalidades.

6. **Média — proteção e cobertura de testes precisam melhorar.** A CI usa
   SQLite, que não valida bloqueios PostgreSQL e deixa cenários de concorrência
   ignorados. O histórico da tarefa anterior registra recriação de uma base
   de testes preexistente por `--noinput`. Usar nomes temporários exclusivos,
   restringir limpeza ao ambiente criado pelo próprio teste e adicionar job
   PostgreSQL com concorrência, homônimos, fechamentos e reenvio. Não executar
   testes destrutivos contra bases de testes persistentes desconhecidas.

7. **Média — banco e Redis publicados em todas as interfaces locais.** Docker
   mostra 5432 e 6379 ligados a `0.0.0.0` e IPv6. Isso não comprova acesso pela
   internet: firewall e roteador não foram auditados. Avaliar restringir esses
   serviços à rede Docker ou localhost, mantendo acesso ao aplicativo conforme
   o uso na rede local. Qualquer ajuste deve preservar a configuração aprovada.

8. **Baixa — documentos extensos e consultas com muitos registros.** PDF de
   duas vias rejeita conteúdo extenso e pede reduzir observações, embora Excel
   preserve tudo. Melhorar com continuação de páginas sem pedir alteração do
   registro original. Lista de terceiros carrega todas as entradas/movimentos;
   fechamentos recalculam históricos por item. Paginar no servidor e reduzir
   consultas repetidas quando o volume justificar. As dependências declaradas
   como `latest` devem receber política de atualização e revisão do lock;
   vulnerabilidades de dependências não foram verificadas nesta auditoria.

## Verificações e limites

- Cinco reproduções confirmadas com SQLite em memória e dados sintéticos,
  usando `backups/auditoria_20261007.py`. Quatro passaram na execução conjunta;
  o cenário da carga própria foi reexecutado sozinho após corrigir o fixture.
  Esses testes comprovam falhas existentes; não significam que foram corrigidas.
- `npm test`: componentes, 16 cenários de autenticação, seis de rascunhos e
  usabilidade aprovados. Django `check`: sem problemas. Migrations: nenhuma
  alteração pendente. `scripts/test_verificar_backup.py`: cinco testes aprovados.
- Backend, frontend, PostgreSQL e Redis saudáveis na consulta Docker.
- Backup completo `backups/agro-ai-pro-2026-10-07-103235-864419`: hashes/CRC,
  restauração isolada do PostgreSQL e recuperação conjunta de uploads aprovadas.
- Não foram alterados código funcional, migrations, registros operacionais,
  permissões ou credenciais. Sem commit/push/merge/publicação. Auditoria de
  segurança externa, impressão física e confirmação do download em disco no
  navegador continuam fora das evidências desta revisão.

Ordem sugerida: identidade e integridade dos fechamentos; erros de API e
reenvio; testes de regressão; conclusão das telas e comprovantes; desempenho
e apresentação dos documentos. Não fundir terceiros antigos automaticamente.
# Continuação: correções autorizadas

Problemas reproduzidos e melhorias tratados em
`2026-10-07-correcoes-auditoria.md`, com testes PostgreSQL, build frontend,
backups verificados e limites registrados. Os achados abaixo permanecem como
registro da auditoria anterior às correções.

