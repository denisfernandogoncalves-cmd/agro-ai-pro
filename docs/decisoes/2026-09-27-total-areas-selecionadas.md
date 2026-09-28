# Total de areas selecionadas

Pedido: mostrar a soma das areas das propriedades selecionadas na tela e na
impressao. Incremento do modulo Propriedades, sem mudanca de regra de negocio.

O componente frontend/src/components/PropriedadesImpressao.tsx reutiliza
totalDeclarado, calculado sobre as propriedades que atendem a todos os filtros.
Soma os hectares armazenados antes de converter para alqueires paulistas
(1 alqueire = 2,42 ha), com tres casas decimais. O total aparece abaixo da
contagem na tela e no cabecalho impresso; o rodape existente foi preservado.
Selecao vazia mostra zero. Durante carregamento o resumo da tela fica oculto.

Validacao: npm.cmd test e npm.cmd run build aprovados; build Docker aprovado.
Testes em frontend/scripts/test-components.mjs cobrem totais para uma, varias
e nenhuma propriedade, filtros e carregamento, na tela e no HTML de impressao.
Navegador local: seis propriedades = 173,988 alq.; Fazenda Electra selecionada
= 71,917 alq., confirmado tambem no DOM do relatorio de impressao.
Nao foi realizada impressao fisica. Build emite aviso de bundle maior que
500 kB. Nao existe script de lint. Backend e migrations nao foram alterados.

Frontend local atualizado na porta 5174. Branch:
codex/propriedades-impressao-a4-20260921. Alteracoes preexistentes preservadas;
sem commit, push ou merge.

Backup privado de codigo, alteracoes locais, uploads e banco:
D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20260927-085938.
ZIPs e bundle verificados pelo script; hashes no manifesto.json. Banco
validado com pg_restore --list; hash em banco.sha256. Sem restauracao.
