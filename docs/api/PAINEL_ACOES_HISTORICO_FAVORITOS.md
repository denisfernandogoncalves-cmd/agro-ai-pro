# Painel, permissões por ação, histórico e favoritos

Todos os endpoints exigem JWT e retornam respostas privadas sem armazenamento em cache.

## Painel

GET /api/core/painel/?propriedade=ID&safra=2026. Parâmetros opcionais; propriedade numérica e safra com até 20 caracteres. Retorna gerado_em, resumo, saldos, alertas, limite_por_tipo (50) e limite_saldos (200). Resumo contém somente indicadores dos módulos com ação consultar. Cada alerta identifica tipo, título, módulo, registro_id, filtros e nível. Apenas leitura; dados de módulos não permitidos não entram nos totais ou avisos.

Produção filtrada por propriedade considera sua parcela da carga compartilhada. Estoque mínimo soma os saldos dos lotes do produto, incluindo produtos ativos sem lote quando a consulta é geral. Financeiro considera compromissos pendentes e diferencia atraso dos próximos sete dias. Saldos negativos e possíveis duplicatas apenas recomendam revisão.

## Ações

GET /api/auth/me/ e GET /api/auth/users/ incluem permissoes, mapa modulo: [consultar,cadastrar,editar,excluir,imprimir]. Administrador configura via POST/PATCH /api/auth/users/ com modulos e permissoes. Chaves devem pertencer aos módulos selecionados; outras ações exigem consultar. Lista vazia não concede ações. Campo legado null mantém as ações existentes; administrador tem todas as ações.

GET/HEAD/OPTIONS de consulta exigem consultar; PDFs/rotas de impressão exigem imprimir. POST de criação e registros de movimentação exigem cadastrar; PATCH/PUT e transições de estado exigem editar; DELETE/cancelamentos/estornos exigem excluir. Prévias sem escrita exigem consultar. Confirmar faturamento de insumos é cadastro com baixa, portanto exige cadastrar. Permissões dos catálogos compartilhados conservam as dependências documentadas no código, sem autorizar escrita por mera consulta.

## Favoritos

GET/POST /api/core/favoritos/; GET aceita contexto. POST: {contexto,nome,filtros}. DELETE /api/core/favoritos/ID/. Contextos: relatorios, financeiro, cargas, producao-saldos, vendas. Filtros somente com nomes e valores escalares permitidos pela consulta; nome até 80 caracteres, limite 100 por usuário, nome único por usuário/contexto. Listagem e exclusão limitadas ao dono; outro usuário recebe 404. Salvamento requer consultar o módulo e é preferência pessoal, não lançamento de negócio.

## Histórico

GET /api/core/historico/?modulo=propriedades&registro_id=ID&acao=editar&usuario_nome=NOME&page=1&por_pagina=25. Somente administradores; página padrão 25, máximo 100. Retorna count/next/previous/results com id, usuario_nome, modulo, entidade, registro_id, acao, alteracoes e criado_em. Cada campo contém antes/depois dos valores realmente persistidos. Registros não possuem rotas de alteração ou exclusão.

Campos permitidos e cobertura em apps/core/auditoria.py. Sem senhas, tokens, arquivos, dados bancários ou observações livres. Histórico aditivo da data de implantação, sem reconstrução de SQL externo, scripts ou atualizações em massa. Transações revertidas não conservam seus registros de auditoria.

Validação e limites completos: ../decisoes/2026-10-02-painel-alertas-acoes-historico.md.
