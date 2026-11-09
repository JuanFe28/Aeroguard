"""Ensaya las pruebas de navegador en un servidor nuevo con SQLite y datos sintéticos."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', default='node')
    parser.add_argument('--port', type=int, default=18084)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'tmp' / ('qa-web-local-' + stamp)
    output.mkdir(parents=True, mode=0o700)
    env = os.environ.copy()
    env.update({
        'PYTHONPATH': str(ROOT / 'backend') + os.pathsep + str(ROOT), 'PYTHONUTF8': '1',
        'APP_ENV': 'production', 'DEBUG': 'false', 'ALLOW_DEMO_TOKENS': 'false',
        'SEED_DEMO_DATA': 'false', 'ALLOW_SQLITE_FALLBACK': 'false',
        'DATABASE_URL': 'sqlite+aiosqlite:///' + (output / 'qa.db').as_posix(),
        'SECRET_KEY': secrets.token_hex(32), 'BOOTSTRAP_ADMIN_PASSWORD': 'Qa@' + secrets.token_hex(24),
        'METRICS_BEARER_TOKEN': secrets.token_hex(32), 'REPORT_SCHEDULER_ENABLED': 'false',
        'REPORTS_DIR': str(output / 'reports'), 'APP_VERSION': '1.2.0-qa.local',
        'SOAR_AI_AGENT_ENABLED': 'false', 'AI_USE_YOLO': 'false', 'AUTH_RATE_LIMIT': '10000',
        'AEROGUARD_QA_URL': f'http://127.0.0.1:{args.port}', 'AEROGUARD_QA_CONFIRM': 'isolated',
        'AEROGUARD_QA_OUTPUT': str(output / 'results'), 'AEROGUARD_QA_HTML': str(output / 'html'),
        'AEROGUARD_QA_JSON': str(output / 'results.json'),
    })
    env['AEROGUARD_QA_ADMIN_PASSWORD'] = env['BOOTSTRAP_ADMIN_PASSWORD']
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with (output / 'backend.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'scripts.qa_local_server:app', '--host', '127.0.0.1', '--port', str(args.port)], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags)
        try:
            opener = build_opener(ProxyHandler({}))
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Servidor de prueba terminó; consultar log privado.')
                try:
                    with opener.open(env['AEROGUARD_QA_URL'] + '/health', timeout=1) as response:
                        data = json.load(response)
                    if data.get('version') == env['APP_VERSION']:
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError('Servidor local de QA no quedó disponible.')
            print('Evidencia local privada:', output, flush=True)
            result = subprocess.run([args.node, 'node_modules/@playwright/test/cli.js', 'test'], cwd=ROOT, env=env, check=False)
            subprocess.run([sys.executable, 'scripts/summarize_app_qa.py', str(output)], cwd=ROOT, check=True)
            return result.returncode
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == '__main__':
    sys.exit(main())
