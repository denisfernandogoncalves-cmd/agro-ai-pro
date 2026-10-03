# Instalador de teste para outro computador — 29/09/2026

Pedido: gerar EXE para instalação e teste em outro computador. Reutilizada a
estrutura `install/windows`, preservando Django, React e PostgreSQL em Docker.
Não houve alteração funcional nem criação de migrations nesta tarefa.

Origem: branch `codex/propriedades-impressao-a4-20260921`, commit
`4ca5bac361cce71423fd9fefd675ab6d46e03f76`, incluindo as alterações locais de
faturamento de insumos e sua migration 0005 já presentes no início da tarefa.
A pasta principal permanece em `feature/importacoes-confirmacao-v1`.
As Sprints existentes não foram reclassificadas por este empacotamento.

## Preservação e artefato

Backup privado verificado antes da geração:
`backups/agro-ai-pro-2026-09-29-080110-824650` neste checkout. Contém código,
uploads, estado Git, diff e banco físico PostgreSQL parado; 7.945 entradas do
banco lidas, ZIPs verificados e SHA-256 registrados em `manifesto.json`.

Executável: `install/output/20260929-080144-424785/AGRO-AI-PRO-Teste-Setup.exe`.
Tamanho: 539.648 bytes. SHA-256:
`75433b40b0014cb0c3ac2622718f447b03dff47e60a1d83a329d9a40d8edf12a`.
Contém 383 arquivos verificados contra o manifesto após extração pelo EXE.
Dados atuais, uploads e `.env` de desenvolvimento não são distribuídos.

## Uso e limites

Copiar apenas o EXE e o LEIA-ME da pasta de saída para o outro computador.
Requer Windows, Docker Desktop iniciado com containers Linux e internet na
primeira instalação. Python, Node e Git são executados/dispensados pela estrutura
Docker, sem instalação desses programas no Windows de destino.
O EXE não instala o Docker Desktop e não é um pacote offline.

Abrir o EXE, pressionar ENTER, aguardar a preparação e criar o usuário solicitado.
Cada instalação cria banco vazio, credenciais próprias e volumes separados em
um projeto Docker exclusivo. O atalho na área de trabalho permite reabrir o
sistema no navegador com o Docker ativo. O executável não possui assinatura digital.

## Validações

- `python install/windows/build.py`: compilação aprovada.
- EXE `--extract`: aprovado; 383 hashes conferidos e scripts PowerShell analisados
  pelo parser sem erros.
- `npm.cmd test`: componentes e 13 cenários de autenticação aprovados.
- `docker compose -p agro-exe-validation-20260929 build`: backend/frontend aprovados;
  build frontend reaproveitado do cache Docker correspondente ao conteúdo.
- `run --rm --no-deps backend python backend/manage.py migrate --noinput`:
  todas as migrations aplicadas no PostgreSQL vazio e isolado.
- `exec backend python backend/manage.py makemigrations --check --dry-run`:
  nenhuma alteração detectada.
- `run --rm --no-deps -w /app/backend backend python manage.py test
  --settings=config.settings.test --noinput`: 443 testes, 404 aprovados,
  37 ignorados e duas falhas. A primeira tentativa sem `-w` descobriu zero
  testes e foi descartada como evidência de validação.
- `up -d --wait`, `stop`, `start --wait`: quatro serviços saudáveis;
  interface HTTP 200 e API `status=ok`, inclusive após reabertura.

Falhas preexistentes: `CompraEstoqueTests.test_lista_busca_e_imutabilidade` e
`EstoqueApiTests.test_movimentos_sao_imutaveis` esperam HTTP 405 ao excluir,
mas recebem HTTP 204. O código atual possui exclusão explícita. Não alteramos
a regra de negócio nem os testes para encobrir a divergência; ela exige revisão
funcional separada. O pacote é entregue para testes com essa limitação conhecida,
sem aprovação integral da suíte. Não existe script lint no frontend.

A criação interativa de usuário/atalho e a instalação física em outro computador
permanecem para verificação no destino. Os serviços de validação foram parados ao
final, com volumes preservados. Nenhum dado do ambiente original foi alterado.
Sem commit, push ou merge.
