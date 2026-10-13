# EXE, rede e trabalho offline — incremento de desenvolvimento

Direção confirmada pelo Product Owner em 09/10/2026: manter o EXE, compartilhar
dados entre computadores e celulares, cadastrar/editar sem conexão e sincronizar
depois. O prompt de reformulação visual foi cancelado.

## Implementado neste incremento

- Fila persistente em IndexedDB, separada por conta e servidor, sem armazenar
  senhas na fila. Primeiro acesso e preparação exigem conexão.
- Cadastro offline de cargas e edição de lançamentos locais ainda não enviados.
- Correção offline de uma carga existente cuja versão foi baixada previamente.
- Reenvio da mesma operação após perda de resposta sem duplicar a carga.
- Aplicação das permissões e validações de negócio atuais no servidor, com
  gravação do recibo e da carga na mesma transação.
- Bloqueio de correções quando a versão do servidor mudou. O lançamento local
  permanece preservado para conferência; não há sobrescrita automática.
- Tentativa de sincronização ao reconectar e a cada 30 segundos com a tela aberta.
- EXE cliente serve a interface local mesmo com o computador central desligado.
  Dados oficiais e saldos só mudam após confirmação do servidor.
- Referências e autorização offline vencem em sete dias. Preparar novamente
  renova esse prazo; lançamentos pendentes não são apagados.

Os demais módulos continuam exigindo conexão. Este incremento não representa
a conclusão do trabalho offline de todo o sistema.

## Montagem e preservação da fonte funcional

A fonte completa do aplicativo está em `.worktrees/runtime-origin-main`, que
permanece preservada. Os ajustes são aplicados em uma cópia de montagem:

```powershell
.venv/Scripts/python.exe packaging/windows/prepare_frontend.py
.venv/Scripts/python.exe packaging/windows/build.py
```

Saída: `dist-windows/AGRO-AI-PRO-Standalone/AGRO-AI-PRO.exe`. Pacote de
desenvolvimento, sem instalação ou atualização automática do aplicativo em uso.
Não distribuir apenas o arquivo EXE: ele utiliza os arquivos da pasta completa.
O instalador anterior de romaneios não contém este incremento offline.

A migration `offline.0001_initial` cria somente os recibos de sincronização.
Não foi aplicada ao banco do aplicativo instalado. O launcher mantém backup de
banco, uploads e configuração antes de migrations em um perfil já utilizado.
Backup da tarefa: `backups/visual-20261009-085642`, com manifesto e hashes;
a fonte funcional também foi preservada em backups anteriores desta sessão.

## Verificações

- Nove testes Django aprovados em banco SQLite de memória: idempotência,
  permissões, autenticação, conta incorreta, conflitos, correção e rollback.
- `makemigrations offline --check --dry-run`: sem mudanças pendentes.
- `node frontend/scripts/test-offline.mjs`: aprovado.
- Cinco testes do proxy local aprovados: interface sem servidor, autenticação,
  caminho inválido, redirecionamento e endereço recusado.
- TypeScript e build Vite da interface funcional: aprovados.
- Chrome com dados sintéticos: preparar aparelho, cadastrar, editar, recarregar
  offline, persistência real em IndexedDB, reenvio sem duplicação, troca de conta
  e largura de 390 pixels aprovados. Capturas em `.packaging/offline-*.png`.
- Runtime incluído no pacote: janela WebView2 e React abrem sem servidor
  conectado, em perfil fictício e porta separados do aplicativo instalado.

Limitações da validação: concorrência no PostgreSQL ainda exige ensaio dedicado;
o teste de componentes legado apresentou incompatibilidade entre Node 24 e
dependências CommonJS. Nenhum dado real foi usado nos testes de cadastro.

## Pendências para uso completo

### Recuperação da fila — 09/10/2026

O painel Trabalho offline possui **Exportar pendentes** e **Recuperar fila de
arquivo**. Exporte antes de atualizar, limpar o navegador ou trocar de aparelho;
guarde o JSON em local privado, pois contém os dados das cargas. A exportação
inclui pendentes, conflitos e bloqueados, sem tokens, senhas ou referências de
autorização. Funciona com as referências vencidas enquanto a sessão está ativa.

No destino, entre na mesma conta e prepare o aparelho no mesmo servidor antes
de importar. A recuperação preserva os identificadores, dispositivos originais,
versões e tentativas. Não sobrescreve itens existentes nem reabre os já
confirmados; repetir a importação não duplica a fila. Identificador existente
com conteúdo diferente cancela toda a importação em uma transação IndexedDB.
Operações interrompidas durante envio voltam a pendente com o mesmo conteúdo.
Conflitos e bloqueios continuam exigindo conferência. Limites: 10 MB e 10 mil itens.

Este recurso é um backup manual da fila, não uma cópia automática do perfil
IndexedDB. Arquivos alterados podem perder validade; as permissões e validações
do servidor continuam obrigatórias na sincronização.

Backup anterior às alterações: `backups/visual-20261009-092505`, código local,
uploads e dump PostgreSQL com ZIP/CRC, catálogo e hashes verificados.
Validação: testes de fila, TypeScript e build Vite aprovados; Chrome em perfil
descartável com dados sintéticos aprovou download/importação, persistência,
reimportação sem duplicação, rollback integral de colisões e largura de 390 px.
O sandbox bloqueou inicialmente a porta local; o mesmo teste passou com
permissão de execução. Nenhuma migration ou alteração em dados reais.
Pacote de desenvolvimento reconstruído com `packaging/windows/build.py` em
`dist-windows/AGRO-AI-PRO-Standalone`; usar a pasta completa. A nova versão
não foi instalada nem homologada em dois computadores físicos.
Arquivos: `frontend/src/offline/{fila.mjs,fila.d.mts,armazenamento.mjs,TrabalhoOffline.tsx}`,
`frontend/scripts/test-offline.mjs`, `packaging/windows/test_offline_browser.cjs`
e este documento. Sem commit, push, merge ou instalação sobre o aplicativo em uso.

1. Validar o pacote em dois computadores físicos e a concorrência do servidor.
2. Disponibilizar acesso remoto autenticado. O usuário ainda não possui conta
   de serviço de acesso remoto ou domínio; nenhuma contratação/publicação ocorreu.
3. Configurar HTTPS para o celular poder instalar e reabrir a interface offline
   com o navegador fechado. HTTP em IP da rede não atende esse requisito.
4. Validar Android/iOS reais, incluindo expiração de sessão e falta de espaço.
5. Acrescentar conferência e resolução assistida de conflitos, além de backup
   automático dos perfis IndexedDB antes de atualizações; recuperação manual
   da fila disponível conforme instruções acima.
6. Expandir cadastro/edição offline aos demais módulos com suas regras próprias.

Manter o computador central ligado para sincronização e consultas oficiais.
Não limpar dados do navegador nem desinstalar o perfil com lançamentos pendentes.
