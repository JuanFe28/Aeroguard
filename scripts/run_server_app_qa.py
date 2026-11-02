"""Lanza pruebas completas de navegador exclusivamente contra el proyecto QA separado."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

from prepare_monitoring import read_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / 'deploy/qa-private/.env')
    args = parser.parse_args()
    envfile = args.env_file.resolve()
    values = read_values(envfile)
    if values.get('COMPOSE_PROJECT_NAME') != 'aeroguard-qa20261029' or values.get('HTTP_PORT') != '18082':
        parser.error('Se requiere el proyecto aislado aeroguard-qa20261029 en el puerto 18082.')
    if values.get('PUBLIC_FRONTEND_URL') != 'http://localhost:18082':
        parser.error('URL privada de QA inesperada; no se enviarán credenciales.')
    if os.name == 'nt':
        parser.error('Ejecutar mediante el bloque SSH en Linux, desde el worktree de la entrega.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'backups' / ('qa-app-' + stamp)
    output.mkdir(parents=True, mode=0o700)
    env = os.environ.copy()
    env['AEROGUARD_QA_EVIDENCE'] = str(output)
    env['AEROGUARD_QA_TAG'] = subprocess.check_output(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=ROOT, text=True).strip()
    compose = ['docker', 'compose', '--env-file', str(envfile), '-f', 'deploy/compose.yml', '-f', 'deploy/compose.source-qa.yml', '-f', 'deploy/compose.browser-qa.yml', '--profile', 'qa-ui']
    print('Evidencia PRIVADA:', output, flush=True)
    subprocess.run(compose + ['config', '--quiet'], cwd=ROOT, env=env, check=True)
    subprocess.run(compose + ['build', 'browser-qa'], cwd=ROOT, env=env, check=True)
    result = subprocess.run(compose + ['run', '--rm', '--no-deps', 'browser-qa'], cwd=ROOT, env=env, check=False)
    subprocess.run([sys.executable, 'scripts/summarize_app_qa.py', str(output)], cwd=ROOT, check=True)
    print('Abrir html/index.html y REVISION_VISUAL.html en la copia descargada. No subir evidencia privada a GitHub.')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
