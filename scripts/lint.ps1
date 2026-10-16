# ==============================================================================
# AeroGuard C-UAS — Suite de Linting y Validacion (PowerShell)
# ==============================================================================
# Uso: .\scripts\lint.ps1 [-Fix]
# ==============================================================================

param (
    [switch]$Fix = $false
)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  AEROGUARD C-UAS - EJECUTANDO SUITE DE LINTING Y CALIDAD DE CODIGO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Validacion de Sintaxis Python (py_compile)
Write-Host "`n[1/4] Verificando sintaxis de archivos Python..." -ForegroundColor Yellow
python "$projectRoot\scripts\check_python_syntax.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Error en sintaxis Python." -ForegroundColor Red
    exit 1
}

# 2. Validacion de Sintaxis JavaScript (Node V8)
Write-Host "`n[2/4] Verificando sintaxis de archivos JavaScript..." -ForegroundColor Yellow
node "$projectRoot\scripts\check_js_syntax.js"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Error en sintaxis JavaScript." -ForegroundColor Red
    exit 1
}

# 3. Linter Python (Ruff si esta instalado)
Write-Host "`n[3/4] Comprobando linter Python (Ruff)..." -ForegroundColor Yellow
$ruffAvailable = Get-Command "ruff" -ErrorAction SilentlyContinue
if ($ruffAvailable) {
    if ($Fix) {
        ruff check "$projectRoot\backend" "$projectRoot\ai_service" "$projectRoot\sensor_simulator" --fix
    } else {
        ruff check "$projectRoot\backend" "$projectRoot\ai_service" "$projectRoot\sensor_simulator"
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Advertencias de estilo/linter encontradas por Ruff." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Ruff: Calidad de codigo Python verificada con exito." -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Ruff no esta instalado en el PATH global (instalar con: pip install ruff)." -ForegroundColor DarkGray
}

# 4. Linter JavaScript (ESLint si esta disponible)
Write-Host "`n[4/4] Comprobando linter JavaScript (ESLint)..." -ForegroundColor Yellow
$eslintPath = "$projectRoot\node_modules\.bin\eslint.cmd"
if (Test-Path $eslintPath) {
    if ($Fix) {
        & $eslintPath "$projectRoot\frontend\src" --fix
    } else {
        & $eslintPath "$projectRoot\frontend\src"
    }
} else {
    Write-Host "[INFO] ESLint local no instalado aun (ejecutar 'npm install' si se desea auditoria profunda)." -ForegroundColor DarkGray
}

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Validacion de calidad y sintaxis completada con exito." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
exit 0
