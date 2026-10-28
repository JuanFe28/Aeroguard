"""Genera credenciales privadas para un despliegue nuevo sin sobrescribirlas."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit


def prepare(directory: Path, url: str, project: str, port: int):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Indica un origen HTTP/HTTPS, sin rutas, credenciales ni parámetros.')
    if parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Este despliegue privado utiliza un origen local y un túnel SSH.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,48}', project):
        raise ValueError('Nombre de proyecto inválido.')
    if not 1024 <= port <= 65535:
        raise ValueError('El puerto debe estar entre 1024 y 65535.')
    if (parsed.port or (443 if parsed.scheme == 'https' else 80)) != port:
        raise ValueError('El puerto del origen debe coincidir con --port.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / '.env'
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('El archivo .env ya existe. Se conserva sin cambios.')
    env = {
        'COMPOSE_PROJECT_NAME': project, 'HTTP_PORT': str(port),
        'PUBLIC_FRONTEND_URL': url.rstrip('/'),
        'BACKEND_CORS_ORIGINS': json.dumps([url.rstrip('/')], separators=(',', ':')),
        # Hex evita caracteres reservados al interpolar credenciales en las URL internas.
        'POSTGRES_PASSWORD': secrets.token_hex(24), 'RABBITMQ_DEFAULT_PASS': secrets.token_hex(24),
        'SECRET_KEY': secrets.token_hex(40), 'BOOTSTRAP_ADMIN_PASSWORD': 'Ag!' + secrets.token_hex(18),
        'METRICS_BEARER_TOKEN': secrets.token_hex(32), 'AI_WORKER_TOKEN': '', 'SIMULATOR_TOKEN': '',
    }
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(f'{key}={value}' for key, value in env.items()) + '\n')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('deploy'))
    parser.add_argument('--url', default='http://localhost:8080')
    parser.add_argument('--project', default='aeroguard-academic')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    try:
        path = prepare(args.directory, args.url, args.project, args.port)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(f'Configuración privada creada: {path}. Las credenciales no se muestran ni se suben a Git.')


if __name__ == '__main__':
    main()
