# Proteção de transportes, relatórios e preparação de integração

## Escopo autorizado e resultado

Três melhorias autorizadas pelo Product Owner em 14/10/2026: completar a
proteção de edição em transportes, reduzir a materialização dos relatórios de
grãos e preparar a integração da versão operacional com a principal.

Critérios atendidos: edições sem versão rejeitadas (400), edições obsoletas
rejeitadas (409) sem sobrescrita, criação preservada, totais e filtros mantidos,
paginação dos detalhes no banco e integração ensaiada sem conflitos com testes
em banco exclusivo. Nenhuma migration nova ou ajuste de dados operacionais.

## Transportes

`core/correcoes.py` reutiliza o hash do snapshot dos campos persistidos para
proteger PUT/PATCH de caminhões, lançamentos e remunerações, sob transação e
bloqueio de linha. Evita adicionar timestamps ou alterar o esquema existente.
Serializers retornam `versao_correcao`; o cliente envia
`versao_correcao_original` obtida ao abrir o registro. Conflitos preservam o
formulário e mostram a mensagem do servidor. Fretes conservam sua proteção
anterior. A ação específica de desvincular motorista mantém sua comparação
de motorista original.

Consumidores externos de PUT/PATCH desses três recursos precisam obter e enviar
a versão. POST não exige versão. A proteção cobre esses endpoints; não constitui
garantia de controle de versão para SQL direto ou todos os scripts externos.

## Relatórios

`relatorios/selectors.py` usa agregação SQL para produção ativa, reservas abertas,
vendas e entregas. Os IDs de posições são subconsulta. Saldos, produção, reservas,
vendas, entregas, movimentações e rastreabilidade contam e recortam o queryset
antes de serializar os detalhes. Motoristas só são calculados quando solicitados.
Filtros, ordenação, formato de resposta e totais globais foram preservados.

Limites: posições para subtotais e produtividade/rateios continuam materializadas;
não se afirma memória constante para todo o relatório. Não houve teste de carga
nem medição de ganho percentual. Os testes verificam totais entre páginas,
conteúdo da primeira página, página vazia e limite de serializações.

## Integração preparada

Origem operacional: `codex/modernizacao-visual-runtime`, commit-base `6e77e35`,
incluindo alterações locais anteriores preservadas e as mudanças desta tarefa.
Base principal: `main`, `ab578d3`.

Árvore isolada: `.worktrees/integracao-melhorias-20261014`, branch
`codex/integracao-melhorias-20261014`. Merge com `--no-commit --no-ff` ensaiado
sem conflitos; 800 arquivos de código/documentação foram copiados da origem e
comparados por SHA-256 antes da inclusão deste relatório. O manifesto está no
backup privado. Nenhum .env, banco, upload, backup ou node_modules foi copiado.

A branch isolada está intencionalmente com merge em andamento, alterações locais
e novos arquivos ainda sem commit. É uma preparação revisável; não é uma entrega
commitada. `main` e o checkpoint antigo não foram alterados. Commit, push e
conclusão do merge em main não foram executados. A suíte completa foi executada
diretamente sobre o código dessa árvore por container descartável.

## Preservação

Backups privados ignorados pelo Git, anteriores às alterações:

- operacional: `backups/visual-20261014-144210`;
- checkpoint: `backups/visual-20261014-144214-546372`.

Ambos contêm código/uploads ZIP, patch e dump PostgreSQL; ZIP verificado por
leitura/CRC e dump por catálogo `pg_restore --list`, hashes em `manifesto.json`.
O primeiro também contém `integracao-hashes.json`. As tentativas anteriores
interrompidas por falta de acesso ao Docker foram preservadas e não são backups
completos. Nenhuma restauração foi realizada.

## Verificações

- `docker compose exec -T backend python /app/scripts/test_backend_isolado.py
  apps.transportes apps.relatorios`: 67 testes, OK, um skip, 25,554 s.
  O teste anterior de desvinculação foi atualizado para o contrato de versão.
- `docker compose -p agro-ai-pro run --rm --no-deps -v
  D:/PROJETOS/AGRO-AI-PRO/.worktrees/integracao-melhorias-20261014:/app backend
  python /app/scripts/test_backend_isolado.py apps`: 807 testes, OK, seis skips,
  405,525 s; banco exclusivo criado e removido pelo runner.
- `docker compose -p agro-ai-pro build frontend`: testes frontend, TypeScript e
  Vite aprovados com Node 22 e dependências do lockfile.
- Django `check`: sem problemas; `makemigrations --check --dry-run`: sem mudanças.
- `git diff --check`: aprovado nas duas árvores, configuração usual do projeto.
- Frontend local atualizado com `up -d --no-deps --wait`, porta 5174, saudável.

A execução direta com Node 24 no Windows apresentou erro de SSR CommonJS/ESM;
build local também esbarrou em permissão de arquivo em dist. A validação oficial
Docker passou; não foram alteradas dependências para contornar o ambiente local.
Não existe script lint no package.json. Conferência visual autenticada integral,
impressão física e testes de carga não foram realizados.
