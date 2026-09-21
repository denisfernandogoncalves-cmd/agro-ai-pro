param(
    [Parameter(Mandatory = $true)]
    [System.Net.IPAddress]$EnderecoServidor
)

$ErrorActionPreference = 'Stop'
$octetos = $EnderecoServidor.GetAddressBytes()
$privado = $octetos.Length -eq 4 -and (
    $octetos[0] -eq 10 -or
    ($octetos[0] -eq 172 -and $octetos[1] -ge 16 -and $octetos[1] -le 31) -or
    ($octetos[0] -eq 192 -and $octetos[1] -eq 168)
)
if (-not $privado) {
    throw 'Informe o IPv4 privado do servidor na rede da fazenda/escritório.'
}

$portaAnterior = $env:FRONTEND_PORT
$hostsAnteriores = $env:DJANGO_ALLOWED_HOSTS
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $env:FRONTEND_PORT = '5174'
    $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,backend,$EnderecoServidor"
    docker compose -p agro-ai-pro up -d backend frontend
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o aplicativo na rede local.' }
    # O Nginx precisa resolver novamente o backend quando o container é recriado.
    docker compose -p agro-ai-pro restart frontend
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao atualizar a conexão do frontend com a API.' }
    Write-Output "Aplicativo: http://${EnderecoServidor}:5174/"
} finally {
    $env:FRONTEND_PORT = $portaAnterior
    $env:DJANGO_ALLOWED_HOSTS = $hostsAnteriores
    Pop-Location
}
