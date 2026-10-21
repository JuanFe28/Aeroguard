"""Comprueba una instalación aislada; crea datos identificados como prueba."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import time
import uuid
import httpx
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:18000')
    parser.add_argument('--private-env', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-test-data', action='store_true', required=True)
    parser.add_argument('--backend-container', default='aeroguard-check-backend')
    args = parser.parse_args()
    env = dict(line.split('=', 1) for line in args.private_env.read_text().splitlines() if '=' in line and not line.startswith('#'))
    results = {}
    with httpx.Client(base_url=args.url, timeout=30) as client:
        def post(path, body):
            response = client.post('/api/v1/' + path, json=body)
            response.raise_for_status()
            return response.json()
        def login():
            response = client.post('/api/v1/auth/token', data={'username': 'admin', 'password': env['BOOTSTRAP_ADMIN_PASSWORD']})
            response.raise_for_status()
            return response.json()['access_token']
        assert client.get('/ready').json()['database'] == 'postgresql'
        results['postgresql_ready'] = True
        token = login()
        client.headers['Authorization'] = 'Bearer ' + token
        prefix = 'VERIFY-' + uuid.uuid4().hex[:8]
        sensor = post('sensors', {'name': prefix, 'latitude': 7, 'longitude': -73})
        zone = post('zones', {'name': prefix, 'threat_level': 'high', 'coordinates': [[6.99,-73.01],[6.99,-72.99],[7.01,-72.99],[7.01,-73.01]], 'max_altitude': 500})
        breach = post('zones/check-breach', {'latitude': 7, 'longitude': -73, 'altitude': 100})
        assert breach['is_breach']
        results['postgis_breach'] = True
        packet = {'sensor_id': sensor['id'], 'object_id': prefix, 'latitude': 7, 'longitude': -73, 'altitude': 100, 'speed': 10, 'heading': 10}
        first = post('sensors/telemetry', packet)
        second = post('sensors/telemetry', {**packet, 'latitude': 7.001})
        assert first['detection_id'] == second['detection_id'] and first['alert_triggered'] and not second['alert_triggered']
        detection_id = first['detection_id']
        points = client.get('/api/v1/detections/' + detection_id + '/trajectory').json()
        assert len(points) == 2
        results['telemetry_track_and_alert_deduplication'] = True
        report = post('reports', {'title': prefix, 'type': 'detections', 'format': 'pdf'})
        downloaded = client.get(report['file_url'])
        assert downloaded.content.startswith(b'%PDF') and downloaded.headers['X-AeroGuard-Data-Source'] == 'database'
        results['report_file_retrieval'] = True
        # Concurrent audit appends, each with an independently authenticated login.
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert len(list(pool.map(lambda _: login(), range(4)))) == 4
        verification = client.get('/api/v1/audit/verify?limit=500').json()
        assert verification['valid'] is True, verification
        results['concurrent_audit_chain'] = verification
        image = io.BytesIO()
        Image.new('RGB', (32, 32), 'white').save(image, format='PNG')
        payload = {'detection_id': detection_id, 'image_base64': base64.b64encode(image.getvalue()).decode()}
        # Management API is invoked inside the private broker network; no host port is exposed.
        publish = {'properties': {'delivery_mode': 2}, 'routing_key': 'ai.processing', 'payload': json.dumps(payload), 'payload_encoding': 'string'}
        code = "import sys,json,httpx; data=json.load(sys.stdin); result=httpx.post('http://rabbitmq:15672/api/exchanges/%2F/amq.default/publish',auth=('aeroguard',data['password']),json=data['publish']); result.raise_for_status(); print(result.text)"
        command = ['docker', 'exec', '-i', args.backend_container, 'python', '-c', code]
        response = subprocess.run(command, input=json.dumps({'password': env['RABBITMQ_DEFAULT_PASS'], 'publish': publish}), capture_output=True, text=True, check=True)
        assert json.loads(response.stdout)['routed']
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            analysis = client.get('/api/v1/detections/' + detection_id + '/ai-analysis')
            if analysis.status_code == 200:
                break
            time.sleep(0.5)
        assert analysis.status_code == 200, analysis.text
        assert analysis.json()['model_validated'] is False
        results['rabbitmq_worker_persisted'] = analysis.json()
        assert 'aeroguard_http_requests_total' in client.get('/metrics').text
        results['authenticated_metrics'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'date_utc': datetime.now(timezone.utc).isoformat(), 'checks': results}, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
