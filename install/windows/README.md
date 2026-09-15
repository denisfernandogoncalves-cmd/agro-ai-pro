# Instalador Windows para testes

Correção de 08/09/2026: a instalação interativa encontrou falha de carregamento
do módulo Microsoft.PowerShell.Security ao chamar Get-Acl. O script passou
a aplicar permissões pela API .NET Framework, inclusive nas retomadas. O
launcher também remove PSModulePath herdado do processo filho para evitar
misturar módulos de versões diferentes do PowerShell.
O teste de leitura e aplicação da ACL passou na pasta da instalação afetada;
o script foi atualizado após backup ZIP validado por CRC e SHA-256 em
`backups/instalacao-20260908-132054/`. A retomada criou o atalho da porta 5184.
A conclusão depende da preparação Docker e criação interativa do usuário.
Novo pacote compilado: `install/output/20260908-100047-199597/AGRO-AI-PRO-Teste-Setup.exe`.

Retomada da entrega iniciada em 07/09/2026. O executável empacota o código
atual do checkout, incluindo alterações ainda não commitadas. Requer Docker
Desktop em execução com containers Linux e internet na primeira instalação.
Não requer Python, Node ou Git instalados no computador de destino.

## Uso

1. Abra `AGRO-AI-PRO-Teste-Setup.exe` e pressione ENTER para instalar.
2. Aguarde o download e a compilação das imagens.
3. Crie o usuário de acesso quando solicitado; a senha não aparece ao digitar.
4. O navegador abre o sistema. Nas próximas vezes use o atalho
   `AGRO-AI-PRO Teste <porta>` na área de trabalho, com o Docker iniciado.

Cada execução do instalador cria uma instalação separada em
`%LOCALAPPDATA%/AGRO-AI-PRO/Teste-<data>-<id>`, um projeto Docker exclusivo,
credenciais locais aleatórias e volumes próprios de PostgreSQL e uploads.
A porta inicial é 5183; portas ocupadas são puladas. Não copia o banco,
uploads nem o `.env` do desenvolvimento. A aplicação fica acessível apenas
na interface local do computador.

Se faltar Docker, a instalação e o atalho são preservados para tentar de novo.
Reabrir o atalho inicia os containers existentes sem reconstruir imagens nem
executar migrations. Esta versão não oferece atualização ou desinstalação de
dados. Não remova volumes se quiser preservar cadastros de teste.

O pacote é uma versão local de desenvolvimento, sem assinatura digital; não
é um instalador de produção nem uma distribuição offline. A instalação
interativa completa e o comportamento em outro computador ainda precisam
ser verificados pelo usuário.

## Compilação

Na raiz do checkout, execute `python install/windows/build.py` no Windows com
o compilador .NET Framework em `%WINDIR%/Microsoft.NET/Framework64/v4.0.30319`.
O resultado fica em uma nova pasta com data em `install/output/`, ignorada
pelo Git. `SHA256.txt` identifica o executável; o payload inclui manifesto
SHA-256 dos arquivos. `--extract <pasta-nova>` valida a extração sem instalar.

## Escopo e aceite

Arquivos: `Installer.cs`, `build.py`, `common.ps1`, `install.ps1`, `start.ps1`,
`compose.yaml` e exclusão de `install/output/` no `.gitignore`.
Critérios: compilar EXE, extrair sem sobrescrever destino, conferir hashes,
excluir dados locais, subir banco isolado, aplicar migrations, obter saúde
da API e da interface e reabrir os containers sem migração automática.

Backup anterior às alterações: `backups/retomada-2026-09-08-070231-162949/`.
Código, banco PostgreSQL e uploads preservados; leitura integral do backup,
CRC dos ZIPs e hashes registrados no `manifesto.json` privado.

Não foram criadas migrations nem alterados os dados do aplicativo existente.
Sem commit, push ou merge nesta tarefa.

## Validação em 08/09/2026

- `python install/windows/build.py`: EXE compilado, 459264 bytes.
- EXE `--extract`: extração aprovada e 348 hashes SHA-256 conferidos.
- Parser PowerShell: os três scripts sem erros de sintaxe.
- `docker compose build`: backend e frontend empacotados compilados.
- `migrate --noinput`: todas as migrations aplicadas no PostgreSQL vazio.
- `check` e `makemigrations --check --dry-run`: sem erros ou alterações.
- `test --settings=config.settings.test --noinput`: 366 testes, 36 ignorados
  pela configuração SQLite, sem falhas. Executados dentro da imagem do pacote.
- `npm test`: 40 testes de componentes e 13 de autenticação aprovados.
- `up --wait`, `stop` e `start --wait`: quatro serviços saudáveis.
- Interface HTTP 200 e `/api/health/` com `status=ok`, inclusive após reabertura.
- `git diff --check`: aprovado.

Artefato: `install/output/20260908-070258-963372/AGRO-AI-PRO-Teste-Setup.exe`.
SHA-256: `a5dcb38c9857798562e83cc5b4db1a7da18105ab893d217f4ddacc99ae2b7db0`.
O projeto `agro-exe-validation-20260908` foi usado para validação na porta
5193, com volumes separados. O fluxo interativo de criação de usuário e
atalho não foi executado automaticamente; o teste cobriu extração, conteúdo,
compilação, migrations, serviços, saúde e reabertura.
