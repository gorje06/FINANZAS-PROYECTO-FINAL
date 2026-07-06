# FinanCuota - arranque local con SQLite persistente
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Instala Python 3.10+ desde https://www.python.org" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host " FinanCuota - instalando dependencias..." -ForegroundColor Cyan
python -m pip install -r requirements.txt -q

Write-Host ""
Write-Host " URL:    http://127.0.0.1:5000" -ForegroundColor Green
Write-Host " Admin:  admin / adminupc" -ForegroundColor Yellow
Write-Host " BD:     $((Get-Item .).FullName)\financuota.db" -ForegroundColor Gray
Write-Host ""
Write-Host " Ctrl+C para detener." -ForegroundColor Gray
Write-Host ""

python app.py
