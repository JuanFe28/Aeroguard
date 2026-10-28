"""Rechaza una configuración de Deploy que publique servicios fuera del túnel local."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate(config, release):
    services = config.get('services', {})
    for name in ('postgres', 'rabbitmq', 'backend', 'frontend'):
        if name not in services:
            raise ValueError('Falta el servicio ' + name)
    if not config.get('networks', {}).get('default', {}).get('internal'):
        raise ValueError('La red de datos debe ser interna.')
    expected = {**release['images'], **release['infrastructure'], 'ai-worker': release['images']['ai-service']}
    for name, service in services.items():
        if service.get('image') != expected.get(name):
            raise ValueError('Imagen fuera del manifiesto: ' + name)
        if service.get('privileged') or service.get('network_mode') == 'host' or service.get('pid') == 'host':
            raise ValueError('Acceso al host no permitido: ' + name)
        for port in service.get('ports', []):
            if name != 'frontend' or port.get('host_ip') != '127.0.0.1' or port.get('target') != 80:
                raise ValueError('Puerto fuera del acceso privado: ' + name)
        if name in ('postgres', 'rabbitmq', 'backend', 'ai-worker', 'simulator') and set(service.get('networks', {})) != {'default'}:
            raise ValueError('El servicio debe permanecer en la red privada: ' + name)
        for volume in service.get('volumes', []):
            if volume.get('type') == 'bind':
                expected_source = (ROOT / 'backend/init.sql').resolve()
                if not (name == 'postgres' and volume.get('target') == '/docker-entrypoint-initdb.d/init.sql'
                        and volume.get('read_only') and Path(volume.get('source', '')).resolve() == expected_source):
                    raise ValueError('Montaje del host no autorizado: ' + name)
    backend = services['backend']
    if (not backend.get('read_only') or 'ALL' not in backend.get('cap_drop', [])
            or not any(option in ('no-new-privileges', 'no-new-privileges:true') for option in backend.get('security_opt', []))):
        raise ValueError('El backend debe usar sistema de archivos de solo lectura y capacidades reducidas.')
    env = backend.get('environment', {})
    if env.get('APP_ENV') != 'production' or any(str(env.get(key)).lower() != 'false' for key in ('DEBUG', 'ALLOW_DEMO_TOKENS', 'SEED_DEMO_DATA', 'ALLOW_SQLITE_FALLBACK')):
        raise ValueError('Configuración de producción inválida.')
    if len(services['frontend'].get('ports', [])) != 1:
        raise ValueError('Debe existir un único puerto local para la interfaz.')
    return {'private_loopback_only': True, 'data_network_internal': True,
            'images_match_manifest': True, 'privileged_services': False, 'production_flags': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('deploy/.env'))
    args = parser.parse_args()
    result = subprocess.run(['docker', 'compose', '--env-file', str(args.env_file.resolve()), '-f', str(ROOT / 'deploy/compose.yml'), 'config', '--format', 'json'],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise SystemExit('No se pudo validar Compose. Revisa las variables privadas sin publicar su contenido.')
    config = json.loads(result.stdout)
    release = json.loads((ROOT / 'deploy/release.json').read_text(encoding='utf-8'))
    print(json.dumps(validate(config, release), indent=2))


if __name__ == '__main__':
    main()
