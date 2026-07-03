param(
    [string]$Model = "ollama/friday:phi4",
    [string]$ApiBase = "http://localhost:11434",
    [switch]$AutoRun
)

$ErrorActionPreference = "Stop"
$Root = "D:\Friday"
$AgentRoot = Join-Path $Root "agent"
$Python = Join-Path $AgentRoot ".venv\Scripts\python.exe"
$Interpreter = Join-Path $AgentRoot ".venv\Scripts\interpreter.exe"
$PromptFile = Join-Path $AgentRoot "FRIDAY_AGENT_SYSTEM_PROMPT.md"

if (-not (Test-Path $Python)) {
    throw "Phase 7 venv not found: $Python"
}
if (-not (Test-Path $Interpreter)) {
    throw "Open Interpreter not found: $Interpreter"
}
if (-not (Test-Path $PromptFile)) {
    throw "System prompt not found: $PromptFile"
}

$env:FRIDAY_ROOT = $Root
$env:OLLAMA_URL = $ApiBase
$env:FRIDAY_AGENT_MODEL = "friday:phi4"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$Instructions = Get-Content -LiteralPath $PromptFile -Raw

Set-Location $Root

$Args = @(
    "--model", $Model,
    "--api_base", $ApiBase,
    "--offline",
    "--disable_telemetry",
    "--safe_mode", "ask",
    "--custom_instructions", $Instructions,
    "--context_window", "8192",
    "--max_tokens", "1200"
)

if ($AutoRun) {
    $Args += "--auto_run"
}

& $Interpreter @Args
