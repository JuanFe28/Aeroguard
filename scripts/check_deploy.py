"""Comprueba el despliegue mediante su proxy, sin imprimir contraseñas ni tokens."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('No se siguen redirecciones durante una comprobación autenticada.')


def check(env_file, url, bootstrap=False):
    env = dict(line.split('=', 1) for line in env_file.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))
    target, configured = urlsplit(url), urlsplit(env['PUBLIC_FRONTEND_URL'])
    if (target.scheme not in ('http', 'https') or target.hostname not in ('localhost', '127.0.0.1', '::1')
            or target.username or target.password or target.query or target.fragment or target.path not in ('', '/')
            or (target.scheme, target.netloc) != (configured.scheme, configured.netloc)):
        raise ValueError('El destino debe coincidir con PUBLIC_FRONTEND_URL antes de enviar credenciales.')
    url = url.rstrip('/')
    opener = build_opener(ProxyHandler({}), NoRedirects())
    def request(path, data=None, token=None):
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        with opener.open(Request(url + path, data=data, headers=headers), timeout=15) as response:
            return response.read()
    if b'id="app"' not in request('/'):
        raise RuntimeError('Frontend no disponible.')
    health = json.loads(request('/health'))
    if health['status'] != 'healthy' or health['env'] != 'production':
        raise RuntimeError('El backend no está en producción.')
    try:
        request('/api/v1/users')
    except HTTPError as error:
        if error.code != 401:
            raise RuntimeError('Respuesta de autenticación no esperada.') from error
    else:
        raise RuntimeError('La API permite acceso anónimo a usuarios.')
    if bootstrap:
        payload = urlencode({'username': 'admin', 'password': env['BOOTSTRAP_ADMIN_PASSWORD']}).encode()
        token = json.loads(request('/api/v1/auth/token', data=payload))['access_token']
        try:
            profile = json.loads(request('/api/v1/auth/me', token=token))
            if profile['role'] != 'admin':
                raise RuntimeError('El administrador no está disponible.')
        finally:
            # Usar solo en la primera instalación: logout revoca todas las sesiones del administrador.
            request('/api/v1/auth/logout', data=b'', token=token)
    return {'checked_utc': datetime.now(timezone.utc).isoformat(), 'origin': url,
            'frontend': True, 'backend_environment': health['env'], 'version': health['version'],
            'anonymous_access_blocked': True, 'bootstrap_login': bootstrap, 'test_session_revoked': bootstrap}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('deploy/.env'))
    parser.add_argument('--url', default='http://localhost:8080')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-bootstrap-login', action='store_true', help='Solo en instalación nueva: verifica login y revoca las sesiones del administrador.')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Usa un archivo nuevo para conservar evidencias anteriores.')
    result = check(args.env_file, args.url, args.check_bootstrap_login)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
