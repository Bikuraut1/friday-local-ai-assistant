$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Mem0Root = Join-Path $Root 'mem0'
$Logs = Join-Path $Root 'logs'
$Python = Join-Path $Mem0Root '.venv\Scripts\python.exe'
$Bridge = Join-Path $Mem0Root 'bridge\memory_bridge.py'
$Compose = Join-Path $Mem0Root 'docker-compose.yml'
$PidFile = Join-Path $Mem0Root 'bridge\memory-bridge.pid'

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

Set-Location $Mem0Root

docker compose -f $Compose up -d
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to start Qdrant.'
}

$deadline = (Get-Date).AddSeconds(120)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:6333/readyz' -TimeoutSec 3
    if ($response.StatusCode -eq 200) { break }
  } catch {}
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

try {
  $existing = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8765/health' -TimeoutSec 15
  if ($existing.StatusCode -eq 200) {
    Write-Host 'FRIDAY memory bridge is already running.'
    exit 0
  }
} catch {}

$env:FRIDAY_ROOT = $Root
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:QDRANT_HOST = '127.0.0.1'
$env:QDRANT_PORT = '6333'
$env:MEM0_TELEMETRY = 'False'
$env:ANONYMIZED_TELEMETRY = 'False'
$env:DO_NOT_TRACK = 'true'

$process = Start-Process -FilePath $Python `
  -ArgumentList @('-m', 'uvicorn', 'bridge.memory_bridge:app', '--host', '0.0.0.0', '--port', '8765') `
  -WorkingDirectory $Mem0Root `
  -RedirectStandardOutput (Join-Path $Logs 'memory-bridge.log') `
  -RedirectStandardError (Join-Path $Logs 'memory-bridge.err.log') `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path $PidFile -Value $process.Id

$deadline = (Get-Date).AddSeconds(120)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8765/health' -TimeoutSec 5
    if ($response.StatusCode -eq 200 -and $response.Content -like '*"status":true*') {
      Write-Host 'FRIDAY memory bridge online: http://localhost:8765'
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

Get-Content (Join-Path $Logs 'memory-bridge.err.log') -Tail 80 -ErrorAction SilentlyContinue
throw 'FRIDAY memory bridge did not become healthy.'
