param(
  [switch]$StopOllama,
  [switch]$StopMemory,
  [switch]$StopRag,
  [switch]$StopSearch,
  [switch]$StopVoice,
  [switch]$StopAutomation,
  [switch]$StopVision,
  [switch]$StopRouter,
  [switch]$StopDashboard
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$ComposeFile = Join-Path $Root 'open-webui\docker-compose.yml'
$MemoryStop = Join-Path $Root 'mem0\stop-memory.ps1'
$RagStop = Join-Path $Root 'rag\stop-reranker.ps1'
$SearxngCompose = Join-Path $Root 'searxng\docker-compose.yml'
$VoiceStop = Join-Path $Root 'voice\stop-voice.ps1'
$N8nStop = Join-Path $Root 'n8n\stop-n8n.ps1'
$VisionStop = Join-Path $Root 'vision\stop-vision-hotkey.ps1'
$RouterStop = Join-Path $Root 'router\stop-router.ps1'
$DashboardStop = Join-Path $Root 'dashboard\stop-dashboard.ps1'

Set-Location $Root

if ($StopMemory -and (Test-Path $MemoryStop)) {
  & powershell -ExecutionPolicy Bypass -File $MemoryStop
}

if ($StopRag -and (Test-Path $RagStop)) {
  & powershell -ExecutionPolicy Bypass -File $RagStop
}

if ($StopSearch -and (Test-Path $SearxngCompose)) {
  docker compose -f $SearxngCompose stop
  if ($LASTEXITCODE -ne 0) {
    throw 'Failed to stop SearXNG.'
  }
}

if ($StopVoice -and (Test-Path $VoiceStop)) {
  & powershell -ExecutionPolicy Bypass -File $VoiceStop
}

if ($StopAutomation -and (Test-Path $N8nStop)) {
  & powershell -ExecutionPolicy Bypass -File $N8nStop
}

if ($StopVision -and (Test-Path $VisionStop)) {
  & powershell -ExecutionPolicy Bypass -File $VisionStop
}

if ($StopRouter -and (Test-Path $RouterStop)) {
  & powershell -ExecutionPolicy Bypass -File $RouterStop
}

if ($StopDashboard -and (Test-Path $DashboardStop)) {
  & powershell -ExecutionPolicy Bypass -File $DashboardStop
}

docker compose -f $ComposeFile stop
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to stop Open WebUI.'
}

if ($StopOllama) {
  Get-Process -Name ollama -ErrorAction SilentlyContinue | Stop-Process
}

Write-Host 'FRIDAY web UI stopped.'
if ($StopOllama) {
  Write-Host 'Ollama stopped.'
} else {
  Write-Host 'Ollama left running. Use -StopOllama to stop it too.'
}

if (-not $StopMemory) {
  Write-Host 'Memory left running. Use -StopMemory to stop it too.'
}
if (-not $StopRag) {
  Write-Host 'RAG reranker left running. Use -StopRag to stop it too.'
}
if (-not $StopSearch) {
  Write-Host 'Search left running. Use -StopSearch to stop it too.'
}
if (-not $StopVoice) {
  Write-Host 'Voice left running. Use -StopVoice to stop it too.'
}
if (-not $StopAutomation) {
  Write-Host 'Automation left running. Use -StopAutomation to stop it too.'
}
if (-not $StopVision) {
  Write-Host 'Vision hotkey left running. Use -StopVision to stop it too.'
}
if (-not $StopRouter) {
  Write-Host 'Model router left running. Use -StopRouter to stop it too.'
}
if (-not $StopDashboard) {
  Write-Host 'Dashboard left running. Use -StopDashboard to stop it too.'
}
