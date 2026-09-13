# tools/build_docs.ps1

$ErrorActionPreference = "Stop"

# Projektverzeichnis ermitteln
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Nexora Engine - Documentation Build" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Virtuelle Umgebung aktivieren
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvActivate)) {
    Write-Host "[ERROR] .venv wurde nicht gefunden:" -ForegroundColor Red
    Write-Host $VenvActivate
    exit 1
}

Write-Host "[1/4] Aktiviere virtuelle Umgebung..." -ForegroundColor Yellow
& $VenvActivate

# Alten Build löschen
$BuildDirectory = Join-Path $ProjectRoot "docs\build"

Write-Host "[2/4] Lösche alten Docs-Build..." -ForegroundColor Yellow

if (Test-Path $BuildDirectory) {
    Remove-Item -Recurse -Force $BuildDirectory
}

# Dokumentation bauen
Write-Host "[3/4] Baue Sphinx-Dokumentation..." -ForegroundColor Yellow
Write-Host ""

sphinx-build -b html docs/source docs/build/html

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Sphinx-Build fehlgeschlagen." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Browser öffnen
Write-Host ""
Write-Host "[4/4] Öffne Dokumentation..." -ForegroundColor Yellow

$IndexFile = Join-Path $ProjectRoot "docs\build\html\index.html"

if (Test-Path $IndexFile) {
    Start-Process $IndexFile
} else {
    Write-Host "[ERROR] index.html wurde nicht gefunden." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Documentation build erfolgreich!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""