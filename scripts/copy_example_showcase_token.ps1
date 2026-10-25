$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$root = Split-Path -Parent $PSScriptRoot
$tokenPath = Join-Path $root 'runtime/example-showcase/control-token.dpapi'
if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) { throw 'Start the example showcase first.' }
$protected = [IO.File]::ReadAllBytes($tokenPath)
$plain = [Security.Cryptography.ProtectedData]::Unprotect($protected, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
try {
    $token = [Text.Encoding]::UTF8.GetString($plain)
    Set-Clipboard -Value $token
} finally { [Array]::Clear($plain, 0, $plain.Length) }
Write-Output 'Local dashboard token copied to clipboard. Paste it into Connect; do not share it.'
