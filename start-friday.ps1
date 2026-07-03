$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Logs = Join-Path $Root 'logs'
$ComposeFile = Join-Path $Root 'open-webui\docker-compose.yml'
$OllamaStart = Join-Path $Root 'ollama\start-ollama-d.ps1'
$MemoryStart = Join-Path $Root 'mem0\start-memory.ps1'
$RagStart = Join-Path $Root 'rag\start-rag.ps1'
$SearxngStart = Join-Path $Root 'searxng\start-searxng.ps1'
$VoiceStart = Join-Path $Root 'voice\start-voice.ps1'
$N8nStart = Join-Path $Root 'n8n\start-n8n.ps1'
$VisionStart = Join-Path $Root 'vision\start-vision-hotkey.ps1'
$RouterStart = Join-Path $Root 'router\start-router.ps1'
$DashboardStart = Join-Path $Root 'dashboard\start-dashboard.ps1'
$DockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Test-HttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [int]$TimeoutSec = 3
  )

  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $TimeoutSec
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
  } catch {
    return $false
  }
}

function Wait-Until {
  param(
    [Parameter(Mandatory = $true)][scriptblock]$Condition,
    [Parameter(Mandatory = $true)][string]$Name,
    [int]$TimeoutSec = 120,
    [int]$IntervalSec = 3
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  do {
    if (& $Condition) {
      return $true
    }
    Start-Sleep -Seconds $IntervalSec
  } while ((Get-Date) -lt $deadline)

  throw "$Name did not become ready within $TimeoutSec seconds."
}

Set-Location $Root

$env:OLLAMA_MODELS = Join-Path $Root 'ollama\models'

if (-not (Test-HttpOk -Uri 'http://localhost:11434/api/tags')) {
  if (-not (Test-Path $OllamaStart)) {
    throw "Missing Ollama start script: $OllamaStart"
  }

  Start-Process -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $OllamaStart) `
    -WindowStyle Hidden

  Wait-Until -Name 'Ollama' -TimeoutSec 120 -Condition {
    Test-HttpOk -Uri 'http://localhost:11434/api/tags'
  } | Out-Null
}

docker info *> (Join-Path $Logs 'docker-info-start.log')
if ($LASTEXITCODE -ne 0) {
  if (-not (Test-Path $DockerDesktop)) {
    throw "Docker is not ready, and Docker Desktop was not found at: $DockerDesktop"
  }

  Start-Process -FilePath $DockerDesktop -WindowStyle Hidden

  Wait-Until -Name 'Docker Desktop' -TimeoutSec 180 -Condition {
    docker info *> $null
    return ($LASTEXITCODE -eq 0)
  } | Out-Null
}

if (Test-Path $MemoryStart) {
  & powershell -ExecutionPolicy Bypass -File $MemoryStart
  Wait-Until -Name 'Memory bridge' -TimeoutSec 150 -Condition {
    Test-HttpOk -Uri 'http://localhost:8765/health'
  } | Out-Null
} else {
  throw "Missing memory start script: $MemoryStart"
}

if (Test-Path $RagStart) {
  & powershell -ExecutionPolicy Bypass -File $RagStart
}

if (Test-Path $SearxngStart) {
  & powershell -ExecutionPolicy Bypass -File $SearxngStart
}

if (Test-Path $VoiceStart) {
  & powershell -ExecutionPolicy Bypass -File $VoiceStart
}

if (Test-Path $N8nStart) {
  & powershell -ExecutionPolicy Bypass -File $N8nStart
}

if (Test-Path $VisionStart) {
  & powershell -ExecutionPolicy Bypass -File $VisionStart
}

if (Test-Path $RouterStart) {
  & powershell -ExecutionPolicy Bypass -File $RouterStart
}

if (Test-Path $DashboardStart) {
  & powershell -ExecutionPolicy Bypass -File $DashboardStart
}

$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
docker compose -f $ComposeFile up -d *> (Join-Path $Logs 'open-webui-start.log')
$composeExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference
if ($composeExitCode -ne 0) {
  Get-Content (Join-Path $Logs 'open-webui-start.log') -Tail 80
  throw 'Open WebUI failed to start.'
}

Wait-Until -Name 'Open WebUI' -TimeoutSec 180 -Condition {
  Test-HttpOk -Uri 'http://localhost:3000/health'
} | Out-Null

Write-Host 'FRIDAY online.'
Write-Host 'Open WebUI: http://localhost:3000'
Write-Host 'Ollama:     http://localhost:11434'
Write-Host 'Memory:     http://localhost:8765'
Write-Host 'RAG:        http://localhost:8770'
Write-Host 'Search:     http://localhost:8081'
Write-Host 'Voice TTS:  http://localhost:8880'
Write-Host 'n8n:        http://localhost:5678'
Write-Host 'Vision:     Win + Shift + F'
Write-Host 'Router:     http://localhost:8790'
Write-Host 'Dashboard:  http://localhost:8888'
