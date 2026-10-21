"""Backup PostgreSQL y restauración de verificación en una base NUEVA. Nunca sobrescribe una BD."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid


def run(*args, capture=False):
    return subprocess.run(args, check=True, capture_output=capture, text=capture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', default='aeroguard-postgres')
    parser.add_argument('--database', default='aeroguard')
    parser.add_argument('--user', default='aeroguard')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-restore', action='store_true')
    parser.add_argument('--reports-container', help='Incluye los archivos originales del backend en una carpeta separada')
    args = parser.parse_args()
    for value in (args.database, args.user, args.container):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
            parser.error('Identificador inválido.')
    if args.output.exists():
        parser.error('Usa una ruta nueva para conservar respaldos anteriores.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = run('docker', 'exec', args.container, 'mktemp', '-d', capture=True).stdout.strip()
    remote = temporary + '/database.dump'
    run('docker', 'exec', args.container, 'pg_dump', '-U', args.user, '-d', args.database, '-Fc', '-f', remote)
    run('docker', 'cp', args.container + ':' + remote, str(args.output))
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'sha256': digest, 'bytes': args.output.stat().st_size,
              'format': 'pg_dump custom', 'restore_verified': False}
    if args.verify_restore:
        target = 'aeroguard_restore_' + uuid.uuid4().hex[:12]
        run('docker', 'exec', args.container, 'createdb', '-U', args.user, target)
        run('docker', 'exec', args.container, 'pg_restore', '-U', args.user, '-d', target, '--exit-on-error', remote)
        counts = {}
        queries = {'users': 'SELECT count(*) FROM users', 'sensors': 'SELECT count(*) FROM sensors',
                   'detections': 'SELECT count(*) FROM detections', 'audit_logs': 'SELECT count(*) FROM audit_logs',
                   'reports': 'SELECT count(*) FROM reports'}
        for table, query in queries.items():
            def count(database):
                return int(run('docker', 'exec', args.container, 'psql', '-U', args.user, '-d', database, '-Atc', query, capture=True).stdout.strip())
            source_count, restored_count = count(args.database), count(target)
            if source_count != restored_count:
                raise RuntimeError('El conteo restaurado no coincide: ' + table)
            counts[table] = source_count
        result.update(restore_verified=True, restored_database=target, row_counts=counts)
    if args.reports_container:
        reports = args.output.with_suffix('.reports')
        if reports.exists():
            raise FileExistsError('La carpeta de reportes ya existe.')
        run('docker', 'cp', args.reports_container + ':/tmp/aeroguard/reports', str(reports))
        result['report_files'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in reports.iterdir() if path.is_file()}
    args.output.with_suffix(args.output.suffix + '.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    run('docker', 'exec', args.container, 'rm', remote)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
