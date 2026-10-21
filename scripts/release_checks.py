"""Verificación local reproducible. No publica, despliega ni modifica Trello."""

import argparse
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Carpeta NUEVA para evidencias")
    parser.add_argument("--audit-dependencies", action="store_true", help="Consulta avisos de PyPI; requiere red")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("La carpeta contiene evidencias. Usa otra para conservar el historial.")
    output.mkdir(parents=True, exist_ok=True)
    temp = ROOT / "tmp" / "release-checks" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    temp.mkdir(parents=True)
    env = os.environ.copy()
    env.update({
        "PYTHONUTF8": "1", "APP_ENV": "development", "DEBUG": "true",
        "AI_USE_YOLO": "false", "SOAR_AI_AGENT_ENABLED": "false",
        "REPORTS_DIR": str(temp / "reports"), "COVERAGE_FILE": str(temp / ".coverage"),
        "AEROGUARD_LOAD_REPORT_DIR": str(output / "load"),
    })
    checks = []

    def run(name, command, timeout=180):
        print(f"Ejecutando {name}...", flush=True)
        start = datetime.now(timezone.utc)
        with (output / f"{name}.txt").open("w", encoding="utf-8") as log:
            try:
                process = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=timeout, check=False)
                code = process.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                log.write(str(error))
                code = -1
        result = {"name": name, "command": command, "exit_code": code,
                  "started_utc": start.isoformat(), "passed": code == 0}
        log_path = output / f"{name}.txt"
        log_path.write_text(re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
                                   "[JWT_DE_PRUEBA_REDACTADO]", log_path.read_text(encoding="utf-8")), encoding="utf-8")
        checks.append(result)
        return result

    run("syntax-python", [sys.executable, "scripts/check_python_syntax.py"])
    run("syntax-js", ["node", "scripts/check_js_syntax.js"])
    run("pytest", [sys.executable, "-m", "pytest", "backend/tests",
                   "--ignore=backend/tests/test_websocket_load.py", "-q", "--tb=short",
                   f"--basetemp={temp / 'functional'}", "--cov=backend/app",
                   f"--cov-report=json:{output / 'coverage.json'}",
                   f"--junitxml={output / 'pytest.xml'}"])
    run("load", [sys.executable, "-m", "pytest", "backend/tests/test_websocket_load.py", "-q", "-s",
                 f"--basetemp={temp / 'load'}", f"--junitxml={output / 'load.xml'}"])
    sast = run("bandit", [sys.executable, "-m", "bandit", "-r", "backend/app", "ai_service",
                           "sensor_simulator", "scripts", "-f", "json", "-o", str(output / "bandit.json")])
    if (output / "bandit.json").exists():
        scan = json.loads((output / "bandit.json").read_text(encoding="utf-8"))
        sast["severity_counts"] = {
            severity: sum(item["issue_severity"] == severity for item in scan["results"])
            for severity in ("LOW", "MEDIUM", "HIGH")
        }
        sast["passed"] = (sast["exit_code"] in (0, 1) and not scan["errors"]
                          and not any(item["issue_severity"] != "LOW" for item in scan["results"]))
        sast["criterion"] = "Sin errores de análisis ni avisos medios/altos; bajos conservados"
    if args.audit_dependencies:
        run("dependencies", [sys.executable, "-m", "pip_audit", "--progress-spinner", "off",
                             "--format", "json", "--output", str(output / "dependencies.json")], timeout=300)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    dirty = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True, check=False)
    summary = {"date_utc": datetime.now(timezone.utc).isoformat(), "base_commit": commit.stdout.strip(),
               "working_tree": dirty.stdout.splitlines(), "python": sys.version,
               "scope": "SQLite temporal, imágenes sintéticas, WS local; sin servicios externos",
               "dependencies_audited": args.audit_dependencies, "checks": checks,
               "checks_passed": all(check["passed"] for check in checks),
               "official_release_approved": False}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks_passed": summary["checks_passed"],
                      "checks": [{"name": c["name"], "passed": c["passed"]} for c in checks]}, indent=2))
    return 0 if summary["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
