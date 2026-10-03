# Documentos, Excel e sessão — entrega de 03/10/2026

Escopo autorizado: seis melhorias e botão de backup em Excel. Branch `codex/melhorias-gestao-transferencias-20261003`. Implementação aplicada ao frontend local na porta 5174; sem merge ou publicação em produção.

## Resultado

- Gestão → Backup em Excel: arquivo organizado por tabelas de negócio, índice e metadados de documentos, incluindo históricos. Exclusivo para administradores. Exportação para consulta; recuperação completa continua dependendo do backup de banco e arquivos.
- Relatórios → exportação Excel: todos os resultados dos filtros aplicados, mesmo quando a tela está paginada; respeita consultar/imprimir.
- Documentos privados de cargas, vendas, transferências, financeiro, compras e faturamento. Download autenticado, upload validado até 5 MB, deduplicação por SHA256, limite de 20, exclusão lógica auditada. Conteúdo persistido no banco; migration aditiva `core.0003_anexolancamento` aplicada localmente.
- Aviso de possíveis duplicidades antes de salvar carga nova/editada, nova venda com saída ou novo boleto. Compara data, quantidade e identificação pertinente (placa/nota/destino/descrição); permite continuar após conferência. Regras existentes de idempotência e duplicidade exata continuam vigentes. Entrega dentro de venda existente não ganhou esta conferência adicional.
- Histórico de posição com contexto e filtro por operação. Saldo acumulado continua incluindo movimentos ocultos pelo filtro.
- Percentuais das cargas em formato brasileiro; renovação antecipada de sessão com aviso, preservando formulário e proteções de logout/concorrência.

## Evidência

- Backend no Docker oficial: 552 casos, 512 aprovados e 40 skips; suíte SQLite completa. PostgreSQL: 21 casos direcionados aprovados, repetidos após revisão final dos metadados Excel.
- `npm.cmd --prefix frontend test`: componentes, 16 cenários de autenticação, seis cenários de rascunhos e usabilidade aprovados. `npm.cmd --prefix frontend run build`: TypeScript/Vite aprovados. Imagem Docker reconstruída, serviço frontend saudável.
- Django checks aprovados e `makemigrations --check --dry-run` sem mudanças. Host tem ausência de reportlab e não executa integralmente os testes de PDF; validação completa feita no container com dependências declaradas.
- Navegador autenticado: botão de backup retornou sucesso na geração; renovação manual removeu o aviso sem trocar de tela. Área de documentos exibiu ausência de anexos e ação desabilitada com motivo. Backup sem overflow em 360/768/1366 px; carga/documentos e aviso compacto de saída sem overflow em 360 px. Cancelar saída preservou texto preenchido; texto de teste removido sem salvar. Nenhum documento, usuário, permissão ou lançamento real foi criado/excluído para teste.
- O navegador integrado não retornou caminho de download para o blob. Geração validada pela mensagem da interface e inspeção do XLSX nos testes; gravação em disco pelo navegador não foi confirmada.

## Preservação e limites

Backups completos privados de código, banco e uploads, integridade e restauração isolada aprovadas: `backups/agro-ai-pro-2026-10-03-084453-515315`, `backups/agro-ai-pro-2026-10-03-091151-291740`, `backups/agro-ai-pro-2026-10-03-092039-368274`. Incluem alterações não commitadas. Evidência visual fica no último backup, fora do Git.

Excel não inclui credenciais ou dados privados de favoritos/rascunhos. Limite de 100.000 linhas; não permite restaurar. Documentos exportados apenas como metadados, incluindo data de exclusão. Validação de tipo é básica por assinatura/terminador; não há antivírus nem restauração de anexos pela interface. Detalhes das rotas, formatos e permissões em `docs/api/DOCUMENTOS_EXCEL.md`.
