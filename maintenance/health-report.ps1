param(
  [string]$OutDir = 'D:\Friday\maintenance\reports'
)

$ErrorActionPreference = 'Continue'

$Root = 'D:\Friday'
$env:OLLAMA_MODELS = Join-Path $Root 'ollama\models'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-Endpoint {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Uri,
    [int]$TimeoutSec = 5
  )

  $started = Get-Date
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec $TimeoutSec
    return [ordered]@{
      name = $Name
      uri = $Uri
      ok = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
      status = $response.StatusCode
      elapsed_ms = [int]((Get-Date) - $started).TotalMilliseconds
      error = $null
    }
  } catch {
    return [ordered]@{
      name = $Name
      uri = $Uri
      ok = $false
      status = $null
      elapsed_ms = [int]((Get-Date) - $started).TotalMilliseconds
      error = $_.Exception.Message
    }
  }
}

function Get-ProcessInfo {
  param([string]$Pattern)

  Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*$Pattern*"
  } | Select-Object ProcessId,Name,CommandLine
}

$endpoints = @(
  (Get-Endpoint -Name 'open_webui' -Uri 'http://localhost:3000/health' -TimeoutSec 5),
  (Get-Endpoint -Name 'ollama' -Uri 'http://localhost:11434/api/tags' -TimeoutSec 5),
  (Get-Endpoint -Name 'memory_bridge' -Uri 'http://localhost:8765/health' -TimeoutSec 15),
  (Get-Endpoint -Name 'qdrant' -Uri 'http://localhost:6333/collections' -TimeoutSec 5),
  (Get-Endpoint -Name 'rag_reranker' -Uri 'http://localhost:8770/health' -TimeoutSec 5),
  (Get-Endpoint -Name 'searxng' -Uri 'http://localhost:8081/' -TimeoutSec 5),
  (Get-Endpoint -Name 'kokoro_tts' -Uri 'http://localhost:8880/v1/models' -TimeoutSec 5),
  (Get-Endpoint -Name 'n8n' -Uri 'http://localhost:5678/healthz' -TimeoutSec 5),
  (Get-Endpoint -Name 'n8n_automation' -Uri 'http://localhost:8788/health' -TimeoutSec 5),
  (Get-Endpoint -Name 'router' -Uri 'http://localhost:8790/health' -TimeoutSec 5),
  (Get-Endpoint -Name 'dashboard' -Uri 'http://localhost:8888/health' -TimeoutSec 5)
)

$containers = @()
try {
  $containers = docker ps --format '{{json .}}' | ForEach-Object { $_ | ConvertFrom-Json }
} catch {
  $containers = @([ordered]@{ error = $_.Exception.Message })
}

$models = @()
try {
  $models = ollama list | Select-Object -Skip 1
} catch {
  $models = @("ERROR $($_.Exception.Message)")
}

$gpu = @()
try {
  $gpu = nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits
} catch {
  $gpu = @("ERROR $($_.Exception.Message)")
}

$report = [ordered]@{
  timestamp = (Get-Date).ToString('s')
  root = $Root
  endpoints = $endpoints
  containers = $containers
  models = $models
  gpu = $gpu
  processes = [ordered]@{
    voice = @(Get-ProcessInfo -Pattern 'wake_listener.py')
    vision_hotkey = @(Get-ProcessInfo -Pattern 'analyze_screen.py')
    router = @(Get-ProcessInfo -Pattern 'model_router.py')
    dashboard = @(Get-ProcessInfo -Pattern 'dashboard_server.py')
  }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$path = Join-Path $OutDir "friday-health-$stamp.json"
$report | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -Path $path

$failed = @($endpoints | Where-Object { -not $_.ok })
Write-Host "Health report: $path"
Write-Host "Endpoints OK: $(($endpoints.Count - $failed.Count))/$($endpoints.Count)"
if ($failed.Count -gt 0) {
  Write-Host 'Failed endpoints:'
  $failed | ForEach-Object { Write-Host " - $($_.name): $($_.error)" }
  exit 1
}

Write-Host 'All FRIDAY endpoints are reachable.'
