"""Inicia la exposición local con procesos ocultos y comprueba su disponibilidad."""

import os
from http.client import HTTPConnection, HTTPException
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "tmp" / "expo"


def ready(url, marker):
    connection = None
    try:
        target = urlsplit(url)
        if target.scheme != "http" or target.hostname != "127.0.0.1" or target.username or target.password:
            return False
        connection = HTTPConnection(target.hostname, target.port or 80, timeout=1)
        path = target.path or "/"
        if target.query:
            path += "?" + target.query
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status == 200 and marker in response.read(16384)
    except (HTTPException, ValueError, TimeoutError, OSError):
        return False
    finally:
        if connection is not None:
            connection.close()


def start_service(name, port, url, marker, command, environment):
    if ready(url, marker):
        print(f"{name} ya disponible: {url}")
        return
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Puerto {port} ocupado por otro servicio. Revisa {url}.")
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"{name.lower()}.log"
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} terminó con código {process.returncode}. Revisa {log_path}.")
        if ready(url, marker):
            print(f"{name} listo (PID {process.pid}): {url}")
            return
        time.sleep(0.3)
    process.terminate()
    raise RuntimeError(f"{name} no quedó listo en 40 segundos. Revisa {log_path}.")


def main():
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    # Este iniciador siempre usa su propia BD local; Docker no es un requisito.
    LOGS.mkdir(parents=True, exist_ok=True)
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{(LOGS / 'aeroguard.db').as_posix()}"
    environment["AI_USE_YOLO"] = "false"
    environment["REPORTS_DIR"] = str(LOGS / "reports")
    start_service(
        "Backend", 8000, "http://127.0.0.1:8000/health", b"healthy",
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"),
         "--host", "127.0.0.1", "--port", "8000"], environment,
    )
    start_service(
        "Frontend", 3000, "http://127.0.0.1:3000/", b"AeroGuard",
        [sys.executable, "-m", "http.server", "3000", "--bind", "127.0.0.1",
         "--directory", str(ROOT / "frontend")], environment,
    )
    print("Frontend: http://127.0.0.1:3000 | API: http://127.0.0.1:8000/docs")
    print(f"Logs: {LOGS}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
