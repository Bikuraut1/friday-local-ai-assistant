$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$RagRoot = Join-Path $Root 'rag'
$RagEnv = Join-Path $RagRoot '.env'
$Logs = Join-Path $Root 'logs'
$Python = Join-Path $Root 'mem0\.venv\Scripts\python.exe'
$PidFile = Join-Path $RagRoot 'reranker.pid'
$QdrantCompose = Join-Path $Root 'mem0\docker-compose.yml'
$OpenWebUICompose = Join-Path $Root 'open-webui\docker-compose.yml'
$MemoryStart = Join-Path $Root 'mem0\start-memory.ps1'

New-Item -ItemType Directory -Force -Path $Logs | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'knowledge-base\inbox') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'knowledge-base\personal') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'knowledge-base\projects') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'knowledge-base\archive') | Out-Null

if (Test-Path $RagEnv) {
  Get-Content -LiteralPath $RagEnv | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_ -split '=', 2
    if ($name) { [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process') }
  }
}

docker compose -f $QdrantCompose up -d
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to start Qdrant.'
}

if (Test-Path $MemoryStart) {
  & powershell -ExecutionPolicy Bypass -File $MemoryStart
}

try {
  $existing = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8770/health' -TimeoutSec 3
  if ($existing.StatusCode -eq 200) {
    Write-Host 'FRIDAY reranker already running.'
  }
} catch {
  $process = Start-Process -FilePath $Python `
    -ArgumentList @('-m', 'uvicorn', 'reranker:app', '--host', '0.0.0.0', '--port', '8770') `
    -WorkingDirectory $RagRoot `
    -RedirectStandardOutput (Join-Path $Logs 'rag-reranker.log') `
    -RedirectStandardError (Join-Path $Logs 'rag-reranker.err.log') `
    -WindowStyle Hidden `
    -PassThru
  Set-Content -Path $PidFile -Value $process.Id
}

$deadline = (Get-Date).AddSeconds(60)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8770/health' -TimeoutSec 3
    if ($response.StatusCode -eq 200) { break }
  } catch {}
  Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

docker compose -f $OpenWebUICompose up -d --force-recreate
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to recreate Open WebUI with Phase 4 RAG settings.'
}

$deadline = (Get-Date).AddSeconds(180)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000/health' -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
      Write-Host 'FRIDAY RAG online.'
      Write-Host 'Open WebUI: http://localhost:3000'
      Write-Host 'Qdrant:     http://localhost:6333'
      Write-Host 'Reranker:   http://localhost:8770'
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

throw 'Open WebUI did not become healthy after Phase 4 RAG configuration.'
