$ErrorActionPreference = 'Stop'
$WebRoot = $PSScriptRoot
Set-Location -LiteralPath $WebRoot
python -m pip install -r requirements.txt
npm ci
Write-Host 'Setup complete. Start with .\start_qshift_web.ps1' -ForegroundColor Green
