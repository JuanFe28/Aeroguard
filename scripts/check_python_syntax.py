#!/usr/bin/env python3
"""
AeroGuard C-UAS — Python Syntax & Bytecode Compilation Validator
Verifica de forma estricta la sintaxis de todos los archivos Python del proyecto
utilizando el compilador nativo de Python (py_compile) sin dependencias externas.
"""

import os
import py_compile
import sys
from pathlib import Path

# Configurar salida segura UTF-8 para Windows / Linux / CI
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TARGET_DIRS = ["backend", "ai_service", "sensor_simulator"]
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "scratch"}

def check_python_files(root_path: Path) -> int:
    errors = 0
    checked_files = 0

    print("=" * 70)
    print(" [AEROGUARD C-UAS] Validacion de Sintaxis Python (py_compile)")
    print("=" * 70)

    for target in TARGET_DIRS:
        target_path = root_path / target
        if not target_path.exists():
            continue

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in sorted(files):
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(root_path)
                    checked_files += 1
                    try:
                        py_compile.compile(str(full_path), doraise=True)
                        print(f"  [OK]   {rel_path.as_posix()}")
                    except py_compile.PyCompileError as exc:
                        errors += 1
                        print(f"  [FAIL] {rel_path.as_posix()}")
                        print(f"         Error: {exc.msg}")
                    except Exception as exc:
                        errors += 1
                        print(f"  [FAIL] {rel_path.as_posix()}: {exc}")

    print("-" * 70)
    print(f" Total auditados: {checked_files} archivos | Errores: {errors}")
    print("=" * 70)

    if errors > 0:
        print("[ERROR] Se encontraron errores de sintaxis en el codigo Python.")
        return 1
    else:
        print("[SUCCESS] Sintaxis Python 100% valida en todos los microservicios.")
        return 0

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    sys.exit(check_python_files(project_root))
