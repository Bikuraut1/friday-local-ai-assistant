$ErrorActionPreference = 'Stop'

docker exec friday-open-webui python -c "from faster_whisper import WhisperModel; root='/app/backend/data/cache/whisper/models'; WhisperModel('base.en', device='cpu', compute_type='int8', download_root=root, local_files_only=False); print('base.en ready')"
docker exec friday-open-webui python -c "from faster_whisper import WhisperModel; root='/app/backend/data/cache/whisper/models'; WhisperModel('medium.en', device='cpu', compute_type='int8', download_root=root, local_files_only=False); print('medium.en ready')"

Get-ChildItem -LiteralPath 'D:\Friday\open-webui\data\cache\whisper\models' -Force | Select-Object Name, LastWriteTime | Format-Table -AutoSize
