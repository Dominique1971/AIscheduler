$Port = 8877

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$homeDir = Join-Path $root 'runtime/example-showcase'
$tokenPath = Join-Path $homeDir 'control-token.dpapi'
$db = Join-Path $homeDir 'scheduler.sqlite'
$apiOrigin = "http://127.0.0.1:$Port"
New-Item -ItemType Directory -Force -Path $homeDir | Out-Null

if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) {
    $bytes = [byte[]]::new(48)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $token = [Convert]::ToBase64String($bytes)
    $plain = [Text.Encoding]::UTF8.GetBytes($token)
    try {
        $protected = [Security.Cryptography.ProtectedData]::Protect($plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        [IO.File]::WriteAllBytes($tokenPath, $protected)
    } finally { [Array]::Clear($plain, 0, $plain.Length); [Array]::Clear($bytes, 0, $bytes.Length) }
}
$protected = [IO.File]::ReadAllBytes($tokenPath)
$plain = [Security.Cryptography.ProtectedData]::Unprotect($protected, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
try { $token = [Text.Encoding]::UTF8.GetString($plain) } finally { [Array]::Clear($plain, 0, $plain.Length) }
if ($token.Length -lt 32) { throw 'Stored showcase token is invalid.' }

function Test-OwnedProcess([string] $Name) {
    $pidPath = Join-Path $homeDir "$Name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) { return $false }
    $processId = [int](Get-Content -LiteralPath $pidPath -Raw)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if (-not $process) { return $false }
    return $process.CommandLine -like "*$homeDir*" -or ($Name -eq 'bridge' -and $process.CommandLine -like '*site_bridge.ps1*' -and $process.CommandLine -like "*$Port*")
}

$python = (Get-Command python -ErrorAction Stop).Source
$powershell = (Get-Command pwsh -ErrorAction Stop).Source
$priorToken = $env:SCHEDULER_CONTROL_TOKEN
try {
    $env:SCHEDULER_CONTROL_TOKEN = $token
    Push-Location $root
    try {
        if (-not (Test-OwnedProcess 'api')) {
            $process = Start-Process -FilePath $python -ArgumentList @('-m','scheduler','--db',$db,'serve','--port',[string]$Port) -WorkingDirectory $root -Environment @{ SCHEDULER_CONTROL_TOKEN = $token } -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $homeDir 'api.stdout.log') -RedirectStandardError (Join-Path $homeDir 'api.stderr.log')
            [IO.File]::WriteAllText((Join-Path $homeDir 'api.pid'), [string]$process.Id)
        }
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $response = Invoke-RestMethod -Uri "$apiOrigin/api/v1/examples" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 2
                if ($response.items.Count -eq 2) { $ready = $true; break }
            } catch { Start-Sleep -Milliseconds 300 }
        }
        if (-not $ready) { throw "Showcase API did not become ready at $apiOrigin" }
        & $python scripts/bootstrap_example_showcase.py
        if ($LASTEXITCODE -ne 0) { throw 'Example import or integrity check failed.' }
        if (-not (Test-OwnedProcess 'daemon')) {
            $process = Start-Process -FilePath $python -ArgumentList @('-m','scheduler','--db',$db,'daemon','--workers','4') -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $homeDir 'daemon.stdout.log') -RedirectStandardError (Join-Path $homeDir 'daemon.stderr.log')
            [IO.File]::WriteAllText((Join-Path $homeDir 'daemon.pid'), [string]$process.Id)
        }
        $bridgeCredentials = Join-Path $root 'runtime/remote-bridge/site-credentials.dpapi'
        if (Test-Path -LiteralPath $bridgeCredentials -PathType Leaf) {
            if (-not (Test-OwnedProcess 'bridge')) {
                $process = Start-Process -FilePath $powershell -ArgumentList @('-NoProfile','-File',(Join-Path $root 'remote/site_bridge.ps1'),'-Action','run','-LocalApi',$apiOrigin,'-Journal',(Join-Path $homeDir 'bridge.jsonl')) -WorkingDirectory $root -Environment @{ SCHEDULER_CONTROL_TOKEN = $token } -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $homeDir 'bridge.stdout.log') -RedirectStandardError (Join-Path $homeDir 'bridge.stderr.log')
                [IO.File]::WriteAllText((Join-Path $homeDir 'bridge.pid'), [string]$process.Id)
            }
            Write-Output 'Owner-private Site bridge started for the isolated example database.'
        } else { Write-Output 'Bridge credentials absent; local showcase started only.' }
        Write-Output "Local dashboard: $apiOrigin/"
        Write-Output 'Use scripts/copy_example_showcase_token.ps1 to copy the local control token for Connect.'
    } finally { Pop-Location }
} finally {
    if ($null -eq $priorToken) { Remove-Item Env:SCHEDULER_CONTROL_TOKEN -ErrorAction SilentlyContinue }
    else { $env:SCHEDULER_CONTROL_TOKEN = $priorToken }
}
