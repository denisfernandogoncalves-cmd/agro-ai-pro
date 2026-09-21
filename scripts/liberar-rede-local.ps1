# Executar como administrador somente no servidor da rede local.
$ErrorActionPreference = 'Stop'
$nome = 'AGRO-AI-PRO-LAN-5174'
if (Get-NetFirewallRule -Name $nome -ErrorAction SilentlyContinue) {
    throw 'A regra já existe. Confira sua configuração antes de alterá-la.'
}
New-NetFirewallRule -Name $nome -DisplayName 'AGRO-AI-PRO rede local 5174' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5174 `
    -LocalAddress 192.168.1.176 -RemoteAddress LocalSubnet `
    -Profile Private -InterfaceAlias 'Wi-Fi' | Out-Null
