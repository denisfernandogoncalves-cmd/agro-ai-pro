# Instalador Windows de testes — 08/10/2026

Entrega solicitada: um instalador EXE, sem Docker nem instalações manuais de
Python, Node ou banco, com janela própria e dados compartilhados na rede local.
O programa usa a interface React existente dentro de uma janela WebView2;
não exige abrir o navegador. Internamente mantém a API Django para reutilizar
as regras e permissões atuais.

## Uso

1. Execute `dist-windows/AGRO-AI-PRO-Testes-Setup.exe` no Windows 10/11 x64.
   A instalação pede permissão de administrador para os componentes incluídos
   e a regra de firewall, restrita à rede privada e à sub-rede local.
2. Abra o atalho **AGRO-AI-PRO Testes**.
3. No computador que manterá os dados, escolha **Sim** e crie uma senha de
   pelo menos 10 caracteres. Entre com usuário `admin` e a senha criada.
4. Nos demais computadores, instale o mesmo EXE, escolha **Não** e informe
   o IPv4 do computador dos dados. Entre com um usuário cadastrado no AGRO.
5. Mantenha o AGRO aberto no computador dos dados durante o uso dos demais.

Este pacote inicia com banco vazio de testes. Não contém o banco, uploads,
credenciais ou configurações privadas do aplicativo atual.
Inclui um modelo PostgreSQL vazio, verificado sem login nem senha. A primeira
abertura copia o modelo para o perfil local e gera credenciais próprias.
Os dados ficam em `%LOCALAPPDATA%\AGRO-AI-PRO-Testes`, separados do programa.
Desinstalar o aplicativo não remove esses dados. O perfil pertence ao usuário
Windows que abriu o aplicativo; use o mesmo usuário no computador dos dados.

O PostgreSQL incluído escuta somente em `127.0.0.1:18766`. O processo do AGRO
atende às janelas locais e da rede na porta `18765`. O fechamento da janela
principal encerra o atendimento e o banco de forma controlada.
Não há publicação na internet nem serviço Windows nesta versão de testes.

## Preservação e limites

- Antes das mudanças: backups completos verificados em
  `backups/visual-20261008-113306` e `backups/visual-20261008-130846`.
- Antes das migrations em banco já utilizado: dump PostgreSQL, ZIP de uploads,
  configuração privada, verificação do catálogo/CRC e SHA-256 em
  `AGRO-AI-PRO-Testes/backups`.
- Os backups locais desse pacote não têm ensaio de restauração e não alimentam
  o indicador de backup do ambiente Docker. Não tratar esse indicador como
  validação do backup desktop. Não há restauração automática.
- A comunicação de testes na rede usa HTTP interno, sem TLS; use apenas uma
  rede privada confiável. Não expor a porta no roteador.
- Clima, cotações e mapas externos continuam dependendo da internet.
- O EXE de testes não possui assinatura digital própria.
- Validação em outro computador físico e Windows limpo permanece necessária.

## Construção

Branch dos arquivos de empacotamento: `codex/modernizacao-visual`.
Fonte da versão funcional: `.worktrees/runtime-origin-main`, branch
`codex/modernizacao-visual-runtime`, incluindo suas alterações locais preservadas.
Nenhum arquivo dessa fonte foi modificado por esta tarefa. As duas configurações
desktop são aplicadas apenas na cópia preparada para empacotamento.
Para outra fonte completa, defina `AGRO_PACKAGE_SOURCE`.

As dependências da versão funcional estão em seu `backend/requirements/base.txt`;
as ferramentas adicionais estão em `packaging/windows/requirements.txt`.
O pacote inclui Python 3.14 x64 com caminhos de módulos isolados, suas bibliotecas
e dependências. O iniciador C# usa o .NET Framework do Windows e executa esse
runtime sem console visível. Não usa o Python instalado no computador destino.
O firewall permite somente `runtime/python.exe`, na porta local 18765 e rede privada.
Os instaladores oficiais Microsoft e Inno Setup tiveram assinatura Authenticode
verificada. O PostgreSQL veio do arquivo binário oficial da EDB. Hashes dos
componentes ficam em `dist-windows/componentes-sha256.json`.

Compile a interface da fonte selecionada com `VITE_API_URL=/api`, TypeScript
`--noEmit -p tsconfig.json` e Vite `--configLoader runner build`, usando
`D:/PROJETOS/AGRO-AI-PRO/.packaging/frontend-runtime` como `outDir`.
Coloque PostgreSQL extraído em `.packaging/postgres/pgsql`, os instaladores em
`.packaging/downloads` e o compilador em `.packaging/inno`.

```powershell
.venv/Scripts/python.exe packaging/windows/build.py --stage-only
.venv/Scripts/python.exe packaging/windows/smoke_test.py
.venv/Scripts/python.exe packaging/windows/build.py
.venv/Scripts/python.exe packaging/windows/validate_exe.py
.packaging/inno/ISCC.exe packaging/windows/installer.iss
```

## Validação

- TypeScript e build Vite da versão funcional: aprovados.
- Check Django e `makemigrations --check --dry-run`: aprovados.
- Banco isolado: login, renovação JWT, rejeição sem autenticação, criação e
  consulta de propriedade, reinício, persistência e backup: aprovados.
- Evidências de integração: `.packaging/qa-c283e747` (fluxo final),
  `.packaging/qa-e3bbeffd` e `.packaging/qa-63dbe7ae`.
- `npm test`: bloqueado por erro preexistente de execução React/Vite,
  `ReferenceError: module is not defined`. Não houve alteração do frontend.
- Pacote com runtime incluído: banco, migrations, API, interface e janela
  WebView2/React aprovados em `.packaging/frozen-qa-5020b969`.
- Iniciador final, confirmação da conclusão da configuração offline,
  encerramento do banco e ausência de erros no log: aprovados em
  `.packaging/frozen-qa-e0d17303`.
- Runtime isolado: todos os caminhos de importação ficam dentro do pacote;
  nenhuma dependência do Python instalado no computador.
- Compilação final Inno Setup: aprovada. Hash SHA-256 do instalador disponível
  em `dist-windows/AGRO-AI-PRO-Testes-Setup.exe.sha256`.
- Preservação: 1.014 arquivos de código/documentação preexistentes conferidos
  contra os dois backups, sem divergências.
- Nenhuma migration nova, commit, push ou merge nesta tarefa.

## Arquivos desta entrega

- `.gitignore`: exclui componentes temporários e binários do Git.
- `backend/config/settings/desktop.py` e `backend/config/desktop_urls.py`:
  configuração isolada, APIs existentes e interface empacotada.
- `packaging/windows/Launcher.cs` e `launcher.py`: iniciador e janela própria,
  configuração local, compartilhamento, PostgreSQL e backups.
- `packaging/windows/build.py`, `installer.iss` e `requirements.txt`: montagem
  do runtime e do instalador com componentes incluídos.
- `packaging/windows/smoke_test.py` e `validate_exe.py`: validação funcional em
  perfis novos e separados dos dados atuais.
