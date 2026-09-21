. (Join-Path $PSScriptRoot 'common.ps1')
try {
    $state = Get-Installation
    if (-not $state.installed) {
        & (Join-Path $PSScriptRoot 'install.ps1')
        exit $LASTEXITCODE
    }
    Test-DockerReady
    $compose = Get-ComposeArgs $state
    # Start existing containers only: reopening never applies migrations or rebuilds images.
    Invoke-Docker ($compose + @('start', '--wait', '--wait-timeout', '180'))
    Open-Application $state
} catch { Show-Failure $_; exit 1 }
