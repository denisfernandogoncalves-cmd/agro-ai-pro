# Central de gestão — melhorias autorizadas sem executável

Implementado em 07/10/2026 no checkout `.worktrees/runtime-origin-main`, branch
`codex/melhorias-gestao-transferencias-20261003`. Product Owner autorizou as melhorias
propostas, exceto EXE. Sem dependências novas, migrations ou dados reclassificados.

## Critérios atendidos

- Gestão → Relatórios → Central de gestão reúne romaneios próprios, entradas de
  terceiros, retiradas, transferências de terceiros, entregas de vendas e anexos.
  Busca por número/nome, tipo/período e paginação de 25 registros no servidor.
  Origens distinguem números iguais; pessoas não são unidas por nome. PDF/Excel
  reutilizam rotas e permissões existentes; anexos exigem consulta na origem.
  Histórico cancelado permanece acessível; situação de terceiros exige conferir
  estornos no histórico. Transferência exige consulta nas duas áreas.
- Diagnóstico autenticado: conexão, banco por `SELECT 1`, versão da interface/API/
  Django e data da verificação. Backup somente para administrador, reutilizando
  evidências existentes, sem divulgar credenciais, caminhos ou erros internos.
- Checklist temporário de cinco etapas: estoque/origem, contagem física, contratos/
  entregas, pendências e financeiro. Atalhos respeitam acessos; fechamento abre
  Cargas colhidas → Terceiros → Fechamentos de período. Não é fechamento oficial,
  não bloqueia lançamentos automaticamente e não inventa prazos. Safra informada
  vai aos relatórios; confira os filtros nos demais módulos.
- Conferência financeira somente leitura: títulos liquidados com diferença de
  valor. Totais a menor/a maior abrangem toda consulta sem compensação entre eles.
  Período usa data da liquidação. Não gera dívida, crédito ou ajuste automático,
  não concilia extratos bancários externos nem interpreta anexos de comprovantes.
- Prévia de importação existente ampliada com filtro servidor de linhas válidas,
  erros/advertências. Alterar filtro remove aceite; elegibilidade usa o lote inteiro.
- Ajuda contextual em propriedades, talhões, cargas, saldos, transferências, vendas,
  financeiro, estoque, operações, máquinas, importações e relatórios.
- Guia de rede local com IPv4 privado validado, endereço e comando copiáveis para
  `scripts/start-rede-local.ps1`. Não executa comandos no navegador, não abre firewall
  e não altera regras de acesso existentes.

Transferência recebida de terceiros continua apenas estoque externo, sem produção
colhida, área, média ou produtividade. Sem alteração operacional pelos testes.

## Preservação

Backup inicial: `backups/agro-ai-pro-2026-10-07-155027-643716`.
Backup antes da atualização local: `backups/agro-ai-pro-2026-10-07-161108-661224`.
Código incluindo alterações locais, banco e uploads preservados; hashes, integridade
e restauração isolada aprovados. Manifestos/provas privados ignorados pelo Git.
Falha de acesso Docker no sandbox no segundo backup resolvida com execução autorizada.

## Validação e limites

- PostgreSQL isolado: `scripts/test_backend_isolado.py apps.core.test_central_gestao
  apps.core.tests apps.importacoes.tests`: 44 testes aprovados. Incluem paginação,
  permissões de origem/impressão, diagnóstico e diferenças financeiras.
- `npm test`, TypeScript/Vite e build Docker aprovados. Frontend atualizado na
  porta 5174, saudável. Django check aprovado, migrations sem mudanças e diff limpo.
- Aplicação autenticada: 28 documentos em duas páginas; busca `#57` com um resultado;
  banco/backup em dia; financeiro sem divergências; atalho abre Terceiros.
  PDF respondeu HTTP 200; Excel solicitado sem erro. Evento de download do navegador
  integrado não retornou caminho; gravação final em disco não confirmada por essa API.
- Acesso a partir de outro computador e impressão física não ensaiados. Informar IP
  do servidor e conferir firewall privado se houver bloqueio.
- Sem commit, push, merge ou produção nesta tarefa. Trabalho anterior preservado.
