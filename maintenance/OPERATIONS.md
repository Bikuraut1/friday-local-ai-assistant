# FRIDAY Operations

## Daily Start

```powershell
cd D:\Friday
.\start-friday.ps1
```

Main URLs:

- Open WebUI: http://localhost:3000
- Dashboard: http://localhost:8888
- n8n: http://localhost:5678

## Health Check

```powershell
cd D:\Friday
.\maintenance\health-report.ps1
```

Reports are saved in:

```text
D:\Friday\maintenance\reports
```

## Backup

Create a normal backup without large Ollama model blobs:

```powershell
cd D:\Friday
.\maintenance\backup-friday.ps1
```

Include voice recordings:

```powershell
cd D:\Friday
.\maintenance\backup-friday.ps1 -IncludeVoiceRecordings
```

Include Qdrant/Open WebUI vector stores when you want a heavier backup:

```powershell
cd D:\Friday
.\maintenance\backup-friday.ps1 -IncludeVectorStores
```

Include Ollama model blobs only when you have enough disk space:

```powershell
cd D:\Friday
.\maintenance\backup-friday.ps1 -IncludeOllamaModels
```

Backups are saved in:

```text
D:\Friday\backups
```

## Cleanup

Preview retention cleanup without deleting files:

```powershell
cd D:\Friday
.\maintenance\cleanup-friday.ps1 -DryRun
```

Default policy keeps the newest 20 files per target folder and deletes only older unprotected files more than 30 days old:

```powershell
cd D:\Friday
.\maintenance\cleanup-friday.ps1
```

Tune retention:

```powershell
cd D:\Friday
.\maintenance\cleanup-friday.ps1 -KeepNewest 30 -DeleteOlderThanDays 45 -DryRun
```

Targets:

```text
D:\Friday\logs
D:\Friday\maintenance\reports
D:\Friday\n8n\output
D:\Friday\vision\screenshots
```

The cleanup script does not touch `backups\` and preserves files whose names start with `latest`.

## Windows Login Startup

Install startup entry:

```powershell
cd D:\Friday
.\maintenance\install-friday-startup.ps1
```

Startup logs are written to:

```text
D:\Friday\logs\startup-latest.log
D:\Friday\logs\startup-YYYYMMDD-HHMMSS.log
```

Remove startup entry:

```powershell
cd D:\Friday
.\maintenance\install-friday-startup.ps1 -Remove
```

## Shutdown

Stop only Open WebUI:

```powershell
cd D:\Friday
.\stop-friday.ps1
```

Stop everything managed by FRIDAY scripts:

```powershell
cd D:\Friday
.\stop-friday.ps1 -StopOllama -StopMemory -StopRag -StopSearch -StopVoice -StopAutomation -StopVision -StopRouter -StopDashboard
```
