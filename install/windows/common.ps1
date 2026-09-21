$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $installRoot

function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "O Docker retornou erro $LASTEXITCODE. Consulte as mensagens acima." }
}

function Test-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Instale o Docker Desktop pelo site https://www.docker.com/products/docker-desktop/ e abra-o. Depois execute novamente o atalho.'
    }
    $engine = & docker info --format '{{.OSType}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') {
        throw 'Abra o Docker Desktop, aguarde a inicialização e selecione containers Linux. Depois execute novamente o atalho.'
    }
}

function Get-Installation {
    Get-Content -LiteralPath (Join-Path $installRoot 'installation.json') -Raw | ConvertFrom-Json
}

function Get-ComposeArgs {
    param($Installation)
    @('compose', '--project-name', $Installation.project, '--env-file', (Join-Path $installRoot '.env'), '-f', (Join-Path $installRoot 'compose.yaml'))
}

function Open-Application {
    param($Installation)
    $url = "http://localhost:$($Installation.port)/"
    $response = Invoke-RestMethod -Uri ($url + 'api/health/') -TimeoutSec 15
    if ($response.status -ne 'ok') { throw 'A API ainda não está pronta.' }
    Write-Host "Aplicativo pronto: $url" -ForegroundColor Green
    Start-Process $url
}

function Show-Failure {
    param($Failure)
    Write-Host "`nNão foi possível concluir: $Failure" -ForegroundColor Red
    Write-Host "A instalação foi preservada em $installRoot. O atalho permite tentar novamente."
    Read-Host 'Pressione ENTER para fechar'
}
