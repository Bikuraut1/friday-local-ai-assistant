param(
  [int]$KeepNewest = 20,
  [int]$DeleteOlderThanDays = 30,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if ($KeepNewest -lt 0) {
  throw 'KeepNewest must be 0 or greater.'
}
if ($DeleteOlderThanDays -lt 1) {
  throw 'DeleteOlderThanDays must be 1 or greater.'
}

$Root = 'D:\Friday'
$Cutoff = (Get-Date).AddDays(-$DeleteOlderThanDays)

$Targets = @(
  Join-Path $Root 'logs'
  Join-Path $Root 'maintenance\reports'
  Join-Path $Root 'n8n\output'
  Join-Path $Root 'vision\screenshots'
)

function Test-ProtectedFile {
  param([System.IO.FileInfo]$File)

  if ($File.FullName -like (Join-Path $Root 'backups\*')) {
    return $true
  }

  if ($File.Name -like 'latest*') {
    return $true
  }

  return $false
}

$totalCandidates = 0

foreach ($target in $Targets) {
  if (-not (Test-Path -LiteralPath $target)) {
    Write-Host "SKIP missing: $target"
    continue
  }

  $files = Get-ChildItem -LiteralPath $target -File -Force |
    Where-Object { -not (Test-ProtectedFile $_) } |
    Sort-Object LastWriteTime -Descending

  $keepSet = @{}
  $files | Select-Object -First $KeepNewest | ForEach-Object {
    $keepSet[$_.FullName] = $true
  }

  $candidates = @(
    $files | Where-Object {
      $_.LastWriteTime -lt $Cutoff -and -not $keepSet.ContainsKey($_.FullName)
    }
  )

  Write-Host "TARGET $target"
  Write-Host "  files=$($files.Count) keep_newest=$KeepNewest older_than_days=$DeleteOlderThanDays candidates=$($candidates.Count)"

  foreach ($file in $candidates) {
    $totalCandidates++
    if ($DryRun) {
      Write-Host "  DRYRUN delete $($file.FullName)"
    } else {
      Remove-Item -LiteralPath $file.FullName -Force
      Write-Host "  DELETED $($file.FullName)"
    }
  }
}

if ($DryRun) {
  Write-Host "Dry run complete. Candidates: $totalCandidates"
} else {
  Write-Host "Cleanup complete. Deleted: $totalCandidates"
}
