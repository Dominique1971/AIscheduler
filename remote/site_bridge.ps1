param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('save', 'run')]
    [string] $Action,
    [ValidateRange(0, 86400)]
    [int] $RunSeconds = 0,
    [string] $LocalApi = 'http://127.0.0.1:8765',
    [string] $Journal = 'runtime/remote-bridge/journal.jsonl'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$credentialPath = Join-Path $root 'runtime/remote-bridge/site-credentials.dpapi'
$origin = 'https://autonomous-scheduler.jetpack71.chatgpt.site'

if ($Action -eq 'save') {
    # Supply one JSON line on stdin. Never put the values in a command line.
    $line = [Console]::In.ReadLine()
    if ([string]::IsNullOrWhiteSpace($line)) { throw 'Credential JSON is required on stdin.' }
    $credential = $line | ConvertFrom-Json
    if ($credential.site_access -isnot [string] -or $credential.site_access.Length -lt 32 -or
        $credential.agent_token -isnot [string] -or $credential.agent_token.Length -lt 43 -or
        $credential.site_access -eq $credential.agent_token) {
        throw 'Two distinct Site and agent tokens are required.'
    }
    $plain = [Text.Encoding]::UTF8.GetBytes(($credential | ConvertTo-Json -Compress))
    try {
        $protected = [Security.Cryptography.ProtectedData]::Protect(
            $plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        [IO.Directory]::CreateDirectory((Split-Path -Parent $credentialPath)) | Out-Null
        [IO.File]::WriteAllBytes($credentialPath, $protected)
    } finally {
        [Array]::Clear($plain, 0, $plain.Length)
    }
    Write-Output 'Saved bridge credentials with Windows user-scoped DPAPI.'
    return
}

if (-not (Test-Path -LiteralPath $credentialPath -PathType Leaf)) {
    throw 'Bridge credentials are not provisioned.'
}
if ([string]::IsNullOrEmpty($env:SCHEDULER_CONTROL_TOKEN)) {
    throw 'Set SCHEDULER_CONTROL_TOKEN for the local API before starting the bridge.'
}
$protected = [IO.File]::ReadAllBytes($credentialPath)
$plain = [Security.Cryptography.ProtectedData]::Unprotect(
    $protected, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
try {
    $credential = [Text.Encoding]::UTF8.GetString($plain) | ConvertFrom-Json
} finally {
    [Array]::Clear($plain, 0, $plain.Length)
}
$env:SCHEDULER_SITE_ACCESS_TOKEN = $credential.site_access
$env:SCHEDULER_REMOTE_AGENT_TOKEN = $credential.agent_token
try {
    Push-Location $root
    try {
        & python remote/bridge.py --site --origin $origin --run-seconds $RunSeconds --local-api $LocalApi --journal $Journal
        if ($LASTEXITCODE -ne 0) { throw "Bridge exited with code $LASTEXITCODE." }
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item Env:SCHEDULER_SITE_ACCESS_TOKEN, Env:SCHEDULER_REMOTE_AGENT_TOKEN -ErrorAction SilentlyContinue
}
