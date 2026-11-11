"""Fija en deploy/ las imágenes publicadas por el workflow "Release de AeroGuard en GHCR".

Actualiza a la vez deploy/compose.yml y deploy/release.json para que no queden
desalineados. Recibe las cuatro líneas `imagen:version@sha256:...` que el resumen
del workflow muestra en "Imagen publicada y comprobada".

Uso:
  python scripts/set_release_digests.py --version 1.2.0-rc.2 --commit <sha completo> \
      --evidence https://github.com/JuanFe28/Aeroguard/actions/runs/<id> \
      ghcr.io/juanfe28/aeroguard-backend:1.2.0-rc.2@sha256:... \
      ghcr.io/juanfe28/aeroguard-frontend:1.2.0-rc.2@sha256:... \
      ghcr.io/juanfe28/aeroguard-ai-service:1.2.0-rc.2@sha256:... \
      ghcr.io/juanfe28/aeroguard-simulator:1.2.0-rc.2@sha256:...

--dry-run muestra los cambios sin escribir.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / 'deploy/compose.yml'
RELEASE = ROOT / 'deploy/release.json'
COMPONENTS = ('backend', 'frontend', 'ai-service', 'simulator')
IMAGE_RE = re.compile(
    r'^ghcr\.io/(?P<owner>[a-z0-9-]+)/aeroguard-(?P<component>[a-z-]+):(?P<version>[0-9A-Za-z.-]+)@sha256:[0-9a-f]{64}$')
VERSION_RE = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-rc\.[1-9]\d*)?$')


def parse_images(lines, version):
    images = {}
    for line in lines:
        line = line.strip().strip('`')
        match = IMAGE_RE.match(line)
        if not match:
            raise SystemExit(f'Formato de imagen inválido: {line}')
        if match['version'] != version:
            raise SystemExit(f'{line} no corresponde a la versión {version}.')
        if match['component'] not in COMPONENTS:
            raise SystemExit(f'Componente desconocido: {match["component"]}')
        if match['component'] in images:
            raise SystemExit(f'Componente repetido: {match["component"]}')
        images[match['component']] = line
    missing = [c for c in COMPONENTS if c not in images]
    if missing:
        raise SystemExit(f'Faltan imágenes: {", ".join(missing)}')
    return {c: images[c] for c in COMPONENTS}


def update_compose(text, images):
    for component, image in images.items():
        pattern = re.compile(rf'(image:\s*)ghcr\.io/[a-z0-9-]+/aeroguard-{re.escape(component)}:[^\s]+')
        text, count = pattern.subn(lambda m, img=image: m.group(1) + img, text)
        if count != 1:
            raise SystemExit(f'compose.yml debe tener exactamente una imagen de {component} (encontradas: {count}).')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', required=True)
    parser.add_argument('--commit', required=True, help='SHA completo (40 caracteres) que construyó las imágenes')
    parser.add_argument('--evidence', required=True, help='URL de la ejecución del workflow de Release')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('images', nargs=4)
    args = parser.parse_args()

    if not VERSION_RE.match(args.version):
        raise SystemExit(f'Versión inválida: {args.version}')
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise SystemExit('El commit debe ser el SHA completo de 40 caracteres.')
    if not args.evidence.startswith('https://github.com/') or '/actions/runs/' not in args.evidence:
        raise SystemExit('La evidencia debe ser la URL de la ejecución en GitHub Actions.')

    images = parse_images(args.images, args.version)
    compose = update_compose(COMPOSE.read_text(encoding='utf-8'), images)
    release = json.loads(RELEASE.read_text(encoding='utf-8'))
    release.update({'version': args.version, 'commit': args.commit, 'images': images, 'evidence': args.evidence})

    if args.dry_run:
        print(json.dumps(release, indent=2))
        return
    COMPOSE.write_text(compose, encoding='utf-8', newline='\n')
    RELEASE.write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'deploy/compose.yml y deploy/release.json apuntan a {args.version}.')


if __name__ == '__main__':
    main()
