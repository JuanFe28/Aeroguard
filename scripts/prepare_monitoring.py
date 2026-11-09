"""Prepara secretos locales de Monitor sin modificar el .env de la aplicación."""
import argparse
import os
from pathlib import Path
import re
import secrets


def read_values(path):
    return dict(line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines()
                if line and not line.startswith('#') and '=' in line)


def private_file(path, value):
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def prepare(env_file, directory):
    values = read_values(env_file)
    token = values.get('METRICS_BEARER_TOKEN', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,}', token):
        raise ValueError('Se requiere el token de métricas existente generado para Deploy.')
    secret_dir = directory / 'secrets'
    if secret_dir.is_symlink():
        raise ValueError('La carpeta de secretos no puede ser un enlace.')
    secret_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_path = secret_dir / 'metrics.token'
    extra = directory / '.env.monitoring'
    if token_path.is_symlink() or extra.is_symlink():
        raise ValueError('No se escriben secretos mediante enlaces.')
    if token_path.exists() and token_path.read_text(encoding='utf-8').strip() != token:
        raise ValueError('El token existente no coincide; revisar sin rotar automáticamente.')
    if extra.exists() and not re.fullmatch(r'[A-Za-z0-9_-]{32,}', read_values(extra).get('GRAFANA_ADMIN_PASSWORD', '')):
        raise ValueError('La configuración de Grafana existente necesita revisión; se conserva.')
    if not token_path.exists():
        private_file(token_path, token + '\n')
    if not extra.exists():
        private_file(extra, 'GRAFANA_ADMIN_PASSWORD=' + secrets.token_hex(24) + '\n')
    return extra


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--directory', type=Path, default=Path('deploy'))
    args = parser.parse_args()
    prepare(args.env_file, args.directory)
    print('Monitor preparado; secretos conservados en archivos privados, sin mostrarlos.')


if __name__ == '__main__':
    main()
