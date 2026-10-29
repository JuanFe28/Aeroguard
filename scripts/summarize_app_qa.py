"""Resume los resultados de Playwright y prepara una galería para revisión humana."""
import html
import json
from pathlib import Path
import sys


def summarize(root):
    report = root / 'results.json'
    if not report.exists():
        raise RuntimeError('No existe results.json: la batería no llegó a terminar; no declarar aprobación.')
    data = json.loads(report.read_text(encoding='utf-8'))
    failures = []
    def visit(suites):
        for suite in suites:
            for spec in suite.get('specs', []):
                for test in spec.get('tests', []):
                    if test.get('status') != 'expected':
                        failures.append({'title': spec['title'], 'status': test.get('status')})
            visit(suite.get('suites', []))
    visit(data.get('suites', []))
    stats = data.get('stats', {})
    suite_complete = sum(stats.get(key, 0) for key in ('expected', 'unexpected', 'skipped', 'flaky')) >= 51
    summary = {'stats': stats, 'failures': failures, 'suite_complete': suite_complete,
               'runner_errors': len(data.get('errors', [])),
               'functional_passed': suite_complete and stats.get('expected', 0) >= 51 and not failures and not data.get('errors') and not any(stats.get(key, 0) for key in ('unexpected', 'skipped', 'flaky')),
               'visual_acceptance': 'PENDIENTE_REVISION_HUMANA',
               'scope': 'QA sintético. Capturas/inventarios no prueban todos los estados posibles ni una operación real.'}
    (root / 'RESUMEN.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    images = sorted((root / 'html' / 'data').glob('*.png'))
    cards = ''.join(f'<figure><img loading="lazy" src="{html.escape(p.relative_to(root).as_posix())}"><figcaption>{html.escape(p.name)}<label><input type="checkbox"> Revisada: texto, color, alineación, espacio, foco y legibilidad</label></figcaption></figure>' for p in images)
    page = '<!doctype html><html lang="es"><meta charset="utf-8"><title>Revisión visual pendiente — AeroGuard QA</title><style>body{font:16px system-ui;background:#eef2f6;color:#172235;margin:24px}figure{background:white;padding:16px;margin:24px 0}img{max-width:100%;border:1px solid #8b98a7}label{display:block;padding:12px}a{color:#0647a8}</style><h1>Revisión visual pendiente</h1><p>Las casillas sirven para revisión local durante esta sesión y no se guardan. Registrar la aceptación y sus observaciones en un archivo aparte. El resultado automático no aprueba el diseño.</p><p><a href="html/index.html">Abrir informe: nombres de casos, capturas, inventarios de campos y errores</a></p>' + cards + '</html>'
    (root / 'REVISION_VISUAL.html').write_text(page, encoding='utf-8')
    print(json.dumps({'functional_passed': summary['functional_passed'], 'visual_acceptance': summary['visual_acceptance'], 'failed_cases': len(failures)}, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    result = summarize(Path(sys.argv[1]))
    sys.exit(0 if result['functional_passed'] else 1)
