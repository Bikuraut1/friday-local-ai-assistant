$ErrorActionPreference = 'Stop'

$WorkflowDir = 'D:\Friday\n8n\workflows'
$files = Get-ChildItem -LiteralPath $WorkflowDir -Filter '*.json' | Sort-Object Name

if (-not $files) {
  throw "No workflow files found in $WorkflowDir"
}

foreach ($file in $files) {
  $containerPath = "/friday/n8n/workflows/$($file.Name)"
  Write-Host "Importing $($file.Name)"
  docker exec friday-n8n n8n import:workflow --input="$containerPath"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to import workflow: $($file.FullName)"
  }
}

Write-Host 'FRIDAY n8n workflows imported.'
