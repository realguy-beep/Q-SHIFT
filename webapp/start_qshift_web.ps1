$ErrorActionPreference = 'Stop'
$WebRoot = $PSScriptRoot
Set-Location -LiteralPath $WebRoot

if (-not (Test-Path -LiteralPath (Join-Path $WebRoot 'node_modules'))) {
    throw "Frontend dependencies are missing. Run 'npm install' from $WebRoot first."
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python is not on PATH. Activate the project Python environment, then rerun.'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Node.js/npm is not on PATH. Install Node.js, then rerun.'
}

npm run build

Write-Host 'Starting Q-SHIFT locally at http://127.0.0.1:8765 (Ctrl+C to stop).' -ForegroundColor Green
python -m uvicorn backend.app:app --app-dir $WebRoot --host 127.0.0.1 --port 8765 --no-proxy-headers
