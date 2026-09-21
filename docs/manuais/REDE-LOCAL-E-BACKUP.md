# Uso na rede local e backups

## Acesso

Servidor configurado em 10/09/2026: Wi-Fi privado, IPv4 `192.168.1.176`.
Nos computadores da mesma rede, abrir `http://192.168.1.176:5174/` no navegador
e entrar com o usuário do aplicativo. Todos usam o mesmo banco central.
No próprio servidor, `http://127.0.0.1:5174/` continua disponível.
O servidor e o Docker Desktop devem permanecer ligados durante o uso.

A porta TCP 5174 está liberada pela regra `AGRO-AI-PRO-LAN-5174`, somente
no Wi-Fi privado, para `LocalSubnet` e endereço local `192.168.1.176`.
Não houve configuração de acesso pela internet.
O teste HTTP foi realizado no servidor; falta confirmar o acesso em outro PC.

Para iniciar novamente, no checkout
`D:\PROJETOS\AGRO-AI-PRO\.worktrees\runtime-origin-main`:

```powershell
.\scripts\start-rede-local.ps1 -EnderecoServidor 192.168.1.176
```

O script preserva a porta 5174 e configura os hosts aceitos pelo backend.
Também reinicia o frontend para atualizar a resolução do backend após recriação.
Se o roteador mudar o IP, será necessário atualizar o endereço de acesso,
os hosts e a regra de firewall. Reservar esse IP no roteador evita a mudança;
a reserva não foi configurada nesta entrega.

## Fazer backup manual

Destino escolhido: `D:\AGRO IA\Backups`.
No checkout acima, executar:

```powershell
D:\PROJETOS\AGRO-AI-PRO\.venv\Scripts\python.exe scripts\backup_local.py --destino 'D:\AGRO IA\Backups'
```

Cada execução cria uma pasta com data, hora e identificador de microssegundos,
sem sobrescrever backups anteriores. O Docker Desktop precisa estar funcionando.
O backup contém código atual inclusive alterações locais, uploads, banco,
estado Git, diff e manifesto com tamanhos e SHA-256. Dependências instaladas,
outros worktrees e backups anteriores ficam fora do ZIP de código.

Com PostgreSQL ativo, usa `pg_dump` e verifica leitura integral com `pg_restore`,
sem restaurar dados. Com PostgreSQL parado, copia o volume somente para leitura.
Os ZIPs passam por verificação CRC. Somente uma execução que termina com
`Backup validado` e gera `manifesto.json` deve ser considerada concluída.

As cópias são privadas e podem conter dados e configuração do aplicativo.
Mantenha o destino restrito às pessoas autorizadas. A pasta está no mesmo disco
D: do projeto: copie os backups para outro dispositivo para proteção contra
falha do disco. Não foi configurado backup automático nem cópia externa.
Restauração exige autorização explícita e ensaio em ambiente isolado.
