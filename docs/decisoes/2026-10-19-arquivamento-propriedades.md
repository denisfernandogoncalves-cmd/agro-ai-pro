# Arquivamento de propriedades e exclusão protegida

Diagnóstico: as exclusões retornavam HTTP 409 por vínculos PROTECT com CAD/PRO, cargas, rateios, lotes, saldos e importações. A mensagem antiga atribuía qualquer bloqueio a talhões. Agora o aviso identifica categorias e quantidades reais dos vínculos e orienta a arquivar.

Após autorização explícita do usuário, incluído arquivamento reversível. Campo `arquivada_em` somente leitura no serializer; ações autenticadas para arquivar/restaurar com transação, lock e idempotência. Arquivar requer permissão excluir; restaurar, editar. Classificação das ações também cobre autenticação JWT. Campo incluído na auditoria.

Lista padrão omite arquivadas; detalhe e vínculos históricos continuam acessíveis. Filtro Mostrar propriedades arquivadas permite consultar e restaurar. Arquivamento não remove cargas, saldos, áreas ou registros relacionados. Exclusão física permanece bloqueada quando houver vínculos protegidos; continua disponível para propriedades sem esses vínculos. Nenhuma propriedade real foi arquivada ou excluída automaticamente durante a implementação.

Migration `propriedades.0010_propriedade_arquivada_em` aplicada localmente. Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-224149`, código/banco/uploads verificados. Treze testes de propriedades/arquivamento aprovados em banco isolado, incluindo preservação de vínculos, listagem, restauração, permissões, campo somente leitura e exclusão protegida. Frontend, autenticação, TypeScript/Vite, migrations e diff aprovados. Frontend local atualizado. Conferência visual no navegador não executada.
