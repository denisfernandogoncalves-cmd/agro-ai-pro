# Impressão das cargas: retirar identificação agregada

A solicitação pela imagem refere-se ao bloco “Controle de entrada de produção”, nomes das propriedades e resumo de CAD/PRO, culturas e safras. Esse bloco foi ocultado exclusivamente na impressão das cargas, via `frontend/src/print.css`. Título “Cargas colhidas”, entrada líquida e tabela com registros e totais permanecem.

Backup prévio: `backups/sincronizacao-20261001-105617`, incluindo código dos worktrees, uploads e PostgreSQL. Código e hashes verificados pelo script de backup; dump validado com `pg_restore --list` e SHA-256 registrado.

Validação: build e testes existentes do frontend, revisão de diff e entrega do CSS pelo servidor local. Sem mudanças em dados ou migrations. Prévia visual de impressão não conferida em navegador autenticado. Sem commit, push ou merge.
