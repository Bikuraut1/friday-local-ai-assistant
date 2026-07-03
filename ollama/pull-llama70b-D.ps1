$env:OLLAMA_MODELS='D:\Friday\ollama\models'
Set-Location 'D:\Friday'
ollama pull llama3.1:70b-instruct-q4_K_M *> 'D:\Friday\logs\pull-llama70b-D.log'
