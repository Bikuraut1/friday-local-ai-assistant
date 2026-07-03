# FRIDAY Phase 8 - n8n Automation

Phase 8 runs n8n locally at `http://localhost:5678` and a small local automation API at `http://localhost:8788`.

## Start

```powershell
Set-Location D:\Friday
.\n8n\start-n8n.ps1
.\n8n\import-workflows.ps1
```

## Test

```powershell
Set-Location D:\Friday
.\n8n\test-n8n.ps1
```

## Workflows

- `FRIDAY - Monday Morning Briefing`
- `FRIDAY - Auto Ingest Knowledge Base`
- `FRIDAY - Weekly Memory Consolidation`
- `FRIDAY - Email Digest Pipeline`

## Manual Triggers

```powershell
Invoke-RestMethod -Uri 'http://localhost:5678/webhook/friday/monday-briefing' -Method Post -TimeoutSec 240
Invoke-RestMethod -Uri 'http://localhost:5678/webhook/friday/auto-ingest' -Method Post -TimeoutSec 240
Invoke-RestMethod -Uri 'http://localhost:5678/webhook/friday/memory-consolidation' -Method Post -TimeoutSec 240
Invoke-RestMethod -Uri 'http://localhost:5678/webhook/friday/email-digest' -Method Post -TimeoutSec 240
```

## Account Note

n8n 2.27.4 enforces passwords of 8 to 64 characters with at least one uppercase letter and one number. The requested password `12345` is rejected by n8n's supported setup API.
