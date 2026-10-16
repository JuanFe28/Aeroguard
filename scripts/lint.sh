#!/usr/bin/env bash
# ==============================================================================
# AeroGuard C-UAS — Suite de Linting y Validación (Bash / CI)
# ==============================================================================
# Uso: ./scripts/lint.sh [--fix]
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "======================================================================"
echo "  AEROGUARD C-UAS — EJECUTANDO SUITE DE LINTING Y CALIDAD DE CODIGO"
echo "======================================================================"

# 1. Validación de Sintaxis Python (py_compile)
echo -e "\n[1/4] Verificando sintaxis de archivos Python..."
python3 "${PROJECT_ROOT}/scripts/check_python_syntax.py"

# 2. Validación de Sintaxis JavaScript (Node V8)
echo -e "\n[2/4] Verificando sintaxis de archivos JavaScript..."
node "${PROJECT_ROOT}/scripts/check_js_syntax.js"

# 3. Linter Python (Ruff si está disponible)
echo -e "\n[3/4] Comprobando linter Python (Ruff)..."
if command -v ruff &> /dev/null; then
    if [[ "$1" == "--fix" ]]; then
        ruff check "${PROJECT_ROOT}/backend" "${PROJECT_ROOT}/ai_service" "${PROJECT_ROOT}/sensor_simulator" --fix
    else
        ruff check "${PROJECT_ROOT}/backend" "${PROJECT_ROOT}/ai_service" "${PROJECT_ROOT}/sensor_simulator"
    fi
    echo "✅ Ruff: Código Python verificado."
else
    echo "ℹ️ Ruff no encontrado en PATH (opcional)."
fi

# 4. Linter JavaScript (ESLint si está disponible)
echo -e "\n[4/4] Comprobando linter JavaScript (ESLint)..."
if [[ -f "${PROJECT_ROOT}/node_modules/.bin/eslint" ]]; then
    if [[ "$1" == "--fix" ]]; then
        "${PROJECT_ROOT}/node_modules/.bin/eslint" "${PROJECT_ROOT}/frontend/src" --fix
    else
        "${PROJECT_ROOT}/node_modules/.bin/eslint" "${PROJECT_ROOT}/frontend/src"
    fi
    echo "✅ ESLint: Código JavaScript verificado."
else
    echo "ℹ️ ESLint local no instalado aún (ejecutar 'npm install' si se desea auditoría profunda)."
fi

echo -e "\n======================================================================"
echo " [OK] Validacion de calidad y sintaxis completada con exito."
echo "======================================================================"
