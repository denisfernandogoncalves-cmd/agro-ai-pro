# Busca do menu web — 10/10/2026

Checkout: runtime-origin-main. Branch: codex/modernizacao-visual-runtime.
Destino: versão web local http://127.0.0.1:5174/.

Escopo: busca sem acentos e sem distinção de maiúsculas, espaços externos
ignorados; grupos sem resultados ocultos; contagem incluindo Dashboard;
mensagem sem resultados; botão Limpar busca; Escape limpa o campo antes de
fechar o menu; títulos dos ícones no menu recolhido. Permissões preservadas.

Arquivos: frontend/src/components/NavegacaoModulos.tsx,
frontend/src/styles.css e frontend/scripts/test-components.mjs.
Sem dependências, backend ou migrations adicionais.

Backup completo verificado: backups/agro-ai-pro-2026-10-10-130916-153463.
Código incluindo alterações locais, uploads e PostgreSQL; CRC dos ZIPs,
leitura integral do dump e hashes SHA-256 registrados no manifesto.

Validação: docker compose -p agro-ai-pro build frontend, com npm test e
npm run build aprovados (componentes, 16 cenários de autenticação, seis de
rascunhos, usabilidade, TypeScript e Vite). Um teste detectou botão oculto
renderizado sem sessão; corrigido removendo o bloco duplicado e revalidado.
Build exigiu acesso ao cache Docker fora do sandbox.
Frontend atualizado com FRONTEND_PORT=5174 e compose up --no-deps --wait.
Navegador autenticado: talhoes encontrou Talhões e ocultou outros grupos;
zzzz exibiu ausência de resultados; Limpar busca restaurou o campo vazio.
Verificação visual desktop do menu recolhido e impressão física não realizada.
Nenhuma mutação de dados operacionais. Sem commit, push ou merge.

## Navegação por teclado no menu móvel — 10/10/2026

Backup completo verificado: backups/agro-ai-pro-2026-10-10-132251-899938.
Alteração localizada em NavegacaoModulos.tsx: foco na busca ao abrir;
Tab/Shift+Tab percorrem os controles visíveis dentro do menu móvel;
Escape e fechamento pelo fundo devolvem foco ao botão Menu.
Sem mudanças de dados, dependências ou migrations.

npm test e npm run build aprovados no build Docker. Frontend 5174 atualizado
com --no-deps --wait e saudável. Conferência autenticada em 396 x 800:
busca recebeu foco; Shift+Tab foi ao último item Backup em Excel;
Tab retornou à busca; Escape fechou e focou Menu. Viewport restaurado.
git diff --check aprovado. Sem commit, push ou merge.
