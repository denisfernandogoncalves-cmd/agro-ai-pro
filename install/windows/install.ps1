. (Join-Path $PSScriptRoot 'common.ps1')
try {
    $statePath = Join-Path $installRoot 'installation.json'
    if (-not (Test-Path -LiteralPath $statePath)) {
        $port = 5183
        $used = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners().Port
        while ($used -contains $port) { $port++ }
        $id = [guid]::NewGuid().ToString('N').Substring(0, 12)
        $state = [pscustomobject]@{ project = "agro-teste-$id"; port = $port; installed = $false }
        $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
        # Secrets are newly generated for this isolated database, never copied from the project.
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $bytes = New-Object byte[] 48
            $rng.GetBytes($bytes)
            $secret = [Convert]::ToBase64String($bytes)
            $rng.GetBytes($bytes)
            $password = [Convert]::ToBase64String($bytes)
        } finally { $rng.Dispose() }
        "APP_PORT=$port`nPOSTGRES_PASSWORD=$password`nDJANGO_SECRET_KEY=$secret" | Set-Content -LiteralPath (Join-Path $installRoot '.env') -Encoding ASCII
    }
    # Apply on retries too; use .NET Framework without module autoloading.
    $account = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $directory = New-Object System.IO.DirectoryInfo($installRoot)
    $acl = $directory.GetAccessControl()
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($account, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
    $directory.SetAccessControl($acl)
    $state = Get-Installation
    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcut = $shell.CreateShortcut((Join-Path $desktop "AGRO-AI-PRO Teste $($state.port).lnk"))
    $shortcut.TargetPath = Join-Path $installRoot 'AGRO-AI-PRO.exe'
    $shortcut.Arguments = '--start'
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.Description = 'AGRO-AI-PRO - ambiente local de teste'
    $shortcut.Save()
    Test-DockerReady
    $compose = Get-ComposeArgs $state
    if (-not $state.installed) {
        Write-Host "`nPreparando o aplicativo. Na primeira execução, aguarde os downloads e a compilação."
        Invoke-Docker ($compose + @('build'))
        Invoke-Docker ($compose + @('up', '-d', '--wait', 'postgres', 'redis'))
        Invoke-Docker ($compose + @('run', '--rm', '--no-deps', 'backend', 'python', 'backend/manage.py', 'migrate', '--noinput'))
        Invoke-Docker ($compose + @('up', '-d', '--build', '--wait', '--wait-timeout', '300'))
        Write-Host "`nCrie seu usuário de acesso. A senha digitada ficará oculta." -ForegroundColor Cyan
        Invoke-Docker ($compose + @('exec', 'backend', 'python', 'backend/manage.py', 'createsuperuser'))
        $state.installed = $true
        $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    }
    Open-Application $state
} catch { Show-Failure $_; exit 1 }
