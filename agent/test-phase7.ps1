$ErrorActionPreference = "Stop"
$Root = "D:\Friday"
$Python = "D:\Friday\agent\.venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python venv missing: $Python"
}

Write-Host "1. Compile Phase 7 tools"
& $Python -m py_compile `
    "D:\Friday\agent\tools\safe_paths.py" `
    "D:\Friday\agent\tools\file_manager.py" `
    "D:\Friday\agent\tools\web_scraper.py" `
    "D:\Friday\agent\tools\email_handler.py" `
    "D:\Friday\agent\tools\scheduler.py" `
    "D:\Friday\agent\tools\sysinfo.py"

Write-Host "2. Verify blocked system path"
& $Python "D:\Friday\agent\tools\file_manager.py" read "C:\Windows\System32\config\SAM"

Write-Host "3. Verify allowed Desktop PDF search"
& $Python "D:\Friday\agent\tools\file_manager.py" largest "$env:USERPROFILE\Desktop" --pattern "*.pdf" --limit 5

Write-Host "4. Verify system status tool"
& $Python "D:\Friday\agent\tools\sysinfo.py" summary

Write-Host "5. Verify Open Interpreter install"
& "D:\Friday\agent\.venv\Scripts\interpreter.exe" --version

Write-Host "Phase 7 smoke test complete."
