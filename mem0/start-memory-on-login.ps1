$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Logs = Join-Path $Root 'logs'
$OllamaStart = Join-Path $Root 'ollama\start-ollama-d.ps1'
$MemoryStart = Join-Path $Root 'mem0\start-memory.ps1'
$DockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$LogFile = Join-Path $Logs 'memory-startup-task.log'

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Write-Log {
  param([Parameter(Mandatory = $true)][string]$Message)
  Add-Content -Path $LogFile -Value "[$(Get-Date -Format s)] $Message"
}

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
    [int]$TimeoutSec = 180,
    [int]$IntervalSec = 3
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  do {
    if (& $Condition) {
      Write-Log "$Name is ready."
      return $true
    }
    Start-Sleep -Seconds $IntervalSec
  } while ((Get-Date) -lt $deadline)

  Write-Log "$Name did not become ready within $TimeoutSec seconds."
  return $false
}

try {
  Write-Log 'Starting FRIDAY memory startup task.'
  Set-Location $Root
  $env:OLLAMA_MODELS = Join-Path $Root 'ollama\models'

  if (-not (Test-HttpOk -Uri 'http://localhost:11434/api/tags')) {
    if (-not (Test-Path $OllamaStart)) {
      throw "Missing Ollama start script: $OllamaStart"
    }
    Write-Log 'Starting Ollama.'
    Start-Process -FilePath 'powershell.exe' `
      -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $OllamaStart) `
      -WindowStyle Hidden
    Wait-Until -Name 'Ollama' -TimeoutSec 150 -Condition {
      Test-HttpOk -Uri 'http://localhost:11434/api/tags'
    } | Out-Null
  } else {
    Write-Log 'Ollama already online.'
  }

  docker info *> (Join-Path $Logs 'docker-info-memory-startup.log')
  if ($LASTEXITCODE -ne 0) {
    if (-not (Test-Path $DockerDesktop)) {
      throw "Docker Desktop not found: $DockerDesktop"
    }
    Write-Log 'Starting Docker Desktop.'
    Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
    Wait-Until -Name 'Docker Desktop' -TimeoutSec 240 -Condition {
      docker info *> $null
      return ($LASTEXITCODE -eq 0)
    } | Out-Null
  } else {
    Write-Log 'Docker already online.'
  }

  if (-not (Test-Path $MemoryStart)) {
    throw "Missing memory start script: $MemoryStart"
  }

  Write-Log 'Starting memory bridge.'
  $memoryStdout = Join-Path $Logs 'memory-startup-task-start-memory.log'
  $memoryStderr = Join-Path $Logs 'memory-startup-task-start-memory.err.log'
  $memoryProcess = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $MemoryStart) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $memoryStdout `
    -RedirectStandardError $memoryStderr `
    -WindowStyle Hidden `
    -Wait `
    -PassThru

  if ($memoryProcess.ExitCode -ne 0) {
    throw "start-memory.ps1 failed with exit code $($memoryProcess.ExitCode). See $memoryStderr"
  }

  if (Test-HttpOk -Uri 'http://localhost:8765/health' -TimeoutSec 5) {
    Write-Log 'FRIDAY memory bridge online: http://localhost:8765'
    exit 0
  }

  throw 'Memory bridge health check failed after start-memory.ps1.'
} catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  exit 1
}
