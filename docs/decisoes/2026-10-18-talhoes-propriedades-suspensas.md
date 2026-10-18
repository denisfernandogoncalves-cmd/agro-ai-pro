# Talhões: seleção suspensa de propriedades

Na branch `codex/modernizacao-visual-runtime`, o formulário de grupos de colheita
passa a adicionar propriedades por uma lista suspensa. Apenas as escolhidas
aparecem abaixo, com CAD/PRO obrigatório e ação de remover do formulário.
Propriedades já escolhidas não aparecem novamente na lista. Edição, cancelamento
e payload existente foram preservados; nenhuma migration ou alteração histórica.

Arquivo: `frontend/src/pages/Talhoes/GruposPropriedadesPanel.tsx`.
Backup validado de código, banco e uploads:
`D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-10-18-085514-460349`,
com manifesto SHA256, CRC dos ZIPs e leitura integral do dump.

Validação: npm test aprovado; Docker frontend executou testes, TypeScript e
build Vite com sucesso. Bloqueio inicial de escrita resolvido pelo usuário;
teste local com conexão bloqueada pelo sandbox passou na execução autorizada.
Build local anterior bloqueado por permissões em dist; build Docker aprovado.
Conferência visual autenticada não realizada. Sem commit, push ou merge.

## Novo talhão no início

A pedido do usuário, `TalhoesPage.tsx` apresenta cadastro/consulta antes dos
grupos de colheita. Apenas a ordem dos blocos mudou. Backup completo validado:
`D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-10-18-095527-604193`.
Testes frontend, TypeScript, build Docker e revisão do diff aprovados.
