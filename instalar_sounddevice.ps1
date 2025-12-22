# Script para instalar sounddevice e desinstalar pyaudio

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Instalador sounddevice para Karaoke" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Desinstala pyaudio se existir
Write-Host "1. Desinstalando pyaudio (se existir)..." -ForegroundColor Yellow
pip uninstall -y pyaudio
Write-Host ""

# Instala sounddevice
Write-Host "2. Instalando sounddevice..." -ForegroundColor Green
pip install sounddevice
Write-Host ""

# Verifica numpy
Write-Host "3. Verificando numpy..." -ForegroundColor Green
pip install --upgrade numpy
Write-Host ""

# Teste de importação
Write-Host "4. Testando instalação..." -ForegroundColor Cyan
python -c "import sounddevice as sd; import numpy as np; print('✓ sounddevice e numpy instalados com sucesso!')"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Instalação concluída!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Agora você pode executar o karaoke:" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor Yellow
Write-Host ""
