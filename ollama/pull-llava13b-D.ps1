$env:OLLAMA_MODELS='D:\Friday\ollama\models'
Set-Location 'D:\Friday'
ollama pull llava:13b *> 'D:\Friday\logs\pull-llava13b-D.log'
