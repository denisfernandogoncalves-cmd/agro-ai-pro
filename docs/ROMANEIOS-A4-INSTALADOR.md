# Romaneios A4 no aplicativo instalado — 09/10/2026

## Numeração sem cerquilha — 09/10/2026

Após confirmação de uso do navegador em 5174, a fonte runtime e o frontend
Docker desse endereço também foram atualizados. Seis testes PostgreSQL,
testes/build frontend e HTTP do build novo aprovados; backup
`backups/visual-20261009-094922`. Registro em
`.worktrees/runtime-origin-main/docs/decisoes/2026-10-09-romaneios-sem-cerquilha.md`.

O pacote de desenvolvimento apresenta os números dos romaneios sem `#` nas
listas de entrada/saída, títulos, campo Romaneio, prévia, impressão e downloads
PDF/Excel. IDs e sequências do banco permanecem iguais. Identificadores de vendas
e de outros movimentos mantêm sua apresentação existente.
O ajuste ocorre somente nas cópias de montagem, por
`packaging/windows/prepare_frontend.py` e `packaging/windows/build.py`;
a fonte operacional `.worktrees/runtime-origin-main` permanece preservada.

Backup verificado: `backups/visual-20261009-092956`, código, uploads e banco,
com manifesto, hashes, CRC do ZIP e catálogo PostgreSQL. TypeScript, build Vite,
montagem do EXE e dois testes Django de PDF/Excel e permissões aprovados em banco
SQLite de memória. Leitura de dependência inicialmente bloqueada pelo sandbox;
o mesmo teste passou com permissão de execução. Revisão das substituições e
`git diff --check` aprovados. Nenhuma migration ou mudança de dados.

Saída atualizada: `dist-windows/AGRO-AI-PRO-Standalone` (usar a pasta completa).
O instalador anterior e o aplicativo instalado ainda não foram atualizados.
Sem commit, push ou merge.

Modelo de impressão com margens de 7 mm, área de 196 × 282 mm e duas vias
com 137 mm de altura. Fonte dos romaneios proporcional à fonte adaptativa:
14,96 px no tamanho inicial, antes 11 px fixos. Redução automática e bloqueio
de transbordamento preservados. Não altera pesos, cálculos, dados nem migrations.
O botão Baixar PDF continua usando o exportador anterior; o ajuste desta entrega
é aplicado à prévia e ao botão Imprimir, inclusive salvar PDF pela impressão.

Fonte protegida preservada: .worktrees/runtime-origin-main.
Modelo atualizado: packaging/windows/overlays/ComprovanteLancamento.tsx.
Para reproduzir, copie o frontend dessa fonte para .packaging/frontend-romaneios,
excluindo node_modules/dist, vincule as dependências existentes e substitua
src/components/ComprovanteLancamento.tsx pelo overlay. Compile com VITE_API_URL=/api,
TypeScript --noEmit -p tsconfig.json e Vite --configLoader runner build
--outDir D:/PROJETOS/AGRO-AI-PRO/.packaging/frontend-runtime.
Execute packaging/windows/build.py e Inno Setup com
/FAGRO-AI-PRO-Testes-Romaneios-Setup packaging/windows/installer.iss.

Backup de código, alterações locais, banco e uploads com ZIP/CRC, catálogo
PostgreSQL e SHA-256: backups/visual-20261009-080349.
TypeScript, Vite, construção do pacote e compilação Inno aprovados.
Testes de componentes bloqueados por problema preexistente de React/Vite:
ReferenceError: module is not defined. Validação do executável em perfil isolado
bloqueada pela porta PostgreSQL 18766 já ocupada; nenhum processo existente
foi encerrado. Impressão física e conferência visual final pendentes.

Instalador: dist-windows/AGRO-AI-PRO-Testes-Romaneios-Setup.exe, com SHA-256 adjacente.
Feche o aplicativo antes de executar o instalador na mesma pasta de instalação.
Dados ficam no perfil local separado dos arquivos do programa.
Não houve instalação sobre o aplicativo do usuário, commit, push ou merge.
