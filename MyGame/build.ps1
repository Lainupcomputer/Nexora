$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================"
Write-Host " Nexora Game Build"
Write-Host "============================================================"
Write-Host ""

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $ProjectDir

# -------------------------------------------------------------
# Clean old build
# -------------------------------------------------------------

Write-Host "[BUILD] Cleaning old build..."

if (Test-Path ".\build") {
    Remove-Item ".\build" -Recurse -Force
}

if (Test-Path ".\dist") {
    Remove-Item ".\dist" -Recurse -Force
}

Write-Host "[BUILD] Clean complete."
Write-Host ""

# -------------------------------------------------------------
# Check spec
# -------------------------------------------------------------

$SpecFile = ".\MyGame.spec"

if (-not (Test-Path $SpecFile)) {
    Write-Host "[ERROR] MyGame.spec not found."
    exit 1
}

# -------------------------------------------------------------
# Check Python
# -------------------------------------------------------------

Write-Host "[BUILD] Python:"
python --version

Write-Host ""

# -------------------------------------------------------------
# Check free-threading
# -------------------------------------------------------------

Write-Host "[BUILD] Checking No-GIL support..."

python -Xgil=0 -c "import sys; print('GIL enabled:', sys._is_gil_enabled())"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Python could not start with -Xgil=0."
    exit 1
}

Write-Host ""

# -------------------------------------------------------------
# Build
# -------------------------------------------------------------

Write-Host "[BUILD] Starting PyInstaller..."
Write-Host ""

python -Xgil=0 -m PyInstaller `
    --clean `
    --noconfirm `
    $SpecFile

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Build failed."
    exit 1
}

# -------------------------------------------------------------
# Result
# -------------------------------------------------------------

$ExePath = ".\dist\MyGame\MyGame.exe"

Write-Host ""
Write-Host "============================================================"

if (Test-Path $ExePath) {
    Write-Host " BUILD SUCCESSFUL"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Executable:"
    Write-Host "  $ExePath"
    Write-Host ""
}
else {
    Write-Host " BUILD FINISHED, BUT EXE WAS NOT FOUND"
    Write-Host "============================================================"
    Write-Host ""
    exit 1
}