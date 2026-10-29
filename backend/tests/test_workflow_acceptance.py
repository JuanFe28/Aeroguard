"""Aceptación integrada con usuarios reales, SQLite aislado y telemetría sintética."""
import hashlib
from uuid import uuid4
import pytest
from app.core.config import settings
from app.core.security import create_access_token

AUTH = {'Authorization': 'Bearer ' + create_access_token({'sub': 'admin', 'role': 'admin'})}
POSITION = {'latitude': 7.005, 'longitude': -72.995, 'altitude': 60, 'speed': 10, 'heading': 45}


def test_complete_detection_alert_report_audit_workflow(isolated_client, monkeypatch, tmp_path):
    client = isolated_client
    monkeypatch.setattr(settings, 'REPORTS_DIR', str(tmp_path))
    roles = {}
    for role in ['admin', 'operator', 'analyst']:
        username = 'flow_' + uuid4().hex[:10]
        response = client.post('/api/v1/users', headers=AUTH, json={
            'username': username, 'email': username + '@example.com', 'password': 'QA-flow-only@12345',
            'first_name': 'QA', 'last_name': role, 'role': role,
        })
        assert response.status_code == 201, response.text
        login = client.post('/api/v1/auth/token', data={'username': username, 'password': 'QA-flow-only@12345'})
        assert login.status_code == 200
        roles[role] = {'Authorization': 'Bearer ' + login.json()['access_token']}
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    admin, operator, analyst = (roles[r] for r in ['admin', 'operator', 'analyst'])
    zone = client.post('/api/v1/zones', headers=admin, json={
        'name': 'QA synthetic workflow', 'coordinates': [[7, -73], [7, -72.99], [7.01, -72.99], [7.01, -73]],
        'min_altitude': 0, 'max_altitude': 200,
    })
    assert zone.status_code == 201, zone.text
    sensor = client.post('/api/v1/sensors', headers=admin, json={'name': 'QA sensor ' + uuid4().hex[:8], 'latitude': 7, 'longitude': -73})
    assert sensor.status_code == 201
    packet = {**POSITION, 'sensor_id': sensor.json()['id'], 'object_id': 'QA-SYNTHETIC-TRACK'}
    first = client.post('/api/v1/sensors/telemetry', headers=operator, json=packet)
    second = client.post('/api/v1/sensors/telemetry', headers=operator, json={**packet, 'latitude': 7.006})
    assert first.status_code == second.status_code == 202, second.text
    detection_id = first.json()['detection_id']
    assert second.json()['detection_id'] == detection_id
    assert first.json()['alert_triggered'] is True
    assert second.json()['alert_triggered'] is False
    trajectory = client.get(f'/api/v1/detections/{detection_id}/trajectory', headers=analyst)
    assert len(trajectory.json()) == 2
    detection = client.get(f'/api/v1/detections/{detection_id}', headers=analyst).json()
    assert detection['ai_confidence'] is None and detection['ai_analyzed'] is False
    alert = next(a for a in client.get('/api/v1/alerts', headers=operator).json() if a['detection_id'] == detection_id)
    assigned = client.patch(f"/api/v1/alerts/{alert['id']}/assign", headers=operator)
    assert assigned.status_code == 200
    assert assigned.json()['status'] == 'assigned'
    assert client.patch(f"/api/v1/alerts/{alert['id']}/resolve", headers=analyst, json={'notes': 'No autorizado'}).status_code == 403
    resolved = client.patch(f"/api/v1/alerts/{alert['id']}/resolve", headers=operator, json={'notes': 'QA sintético: revisión humana de prueba, sin incidente real.'})
    assert resolved.status_code == 200 and resolved.json()['status'] == 'resolved'
    assert client.patch(f'/api/v1/detections/{detection_id}/status?new_status=resolved', headers=operator).status_code == 200
    report = client.post('/api/v1/reports', headers=analyst, json={'title': 'QA synthetic workflow', 'type': 'detections', 'format': 'csv'})
    assert report.status_code == 201, report.text
    record = report.json()
    original = client.get(record['file_url'], headers=analyst)
    assert detection_id in original.text
    assert hashlib.sha256(original.content).hexdigest() == record['params']['file_sha256']
    assert client.get(record['file_url'], headers=analyst).content == original.content
    assert client.get(record['file_url'], headers=operator).status_code == 403
    audit = client.get('/api/v1/audit?action=ALERT_RESOLVED', headers=analyst)
    assert any(row['resource_id'] == alert['id'] for row in audit.json())
    verification = client.get('/api/v1/audit/verify?limit=500', headers=analyst)
    assert verification.status_code == 200 and verification.json()['valid'] is True


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/api/v1/detections/not-a-uuid', None),
    ('get', '/api/v1/detections/not-a-uuid/ai-analysis', None),
    ('get', '/api/v1/sensors/not-a-uuid', None),
    ('get', '/api/v1/zones/not-a-uuid', None),
    ('get', '/api/v1/users/not-a-uuid', None),
    ('delete', '/api/v1/reports/schedules/not-a-uuid', None),
    ('patch', '/api/v1/alerts/not-a-uuid/assign', None),
    ('patch', '/api/v1/alerts/not-a-uuid/resolve', {'notes': 'QA valid note'}),
])
def test_invalid_ids_do_not_reach_uuid_queries(isolated_client, method, path, payload):
    assert isolated_client.request(method, path, headers=AUTH, json=payload).status_code == 422


@pytest.mark.parametrize('field,value', [('sensor_id', 'bad'), ('zone_id', 'bad'), ('latitude', 91), ('longitude', -181), ('altitude', -1), ('speed', -1), ('heading', 361), ('ai_confidence', 2)])
def test_detection_rejects_invalid_input(isolated_client, field, value):
    assert isolated_client.post('/api/v1/detections', headers=AUTH, json={**POSITION, field: value}).status_code == 422


@pytest.mark.parametrize('field', ['sensor_id', 'zone_id'])
def test_detection_rejects_missing_references(isolated_client, field):
    assert isolated_client.post('/api/v1/detections', headers=AUTH, json={**POSITION, field: str(uuid4())}).status_code == 404


def test_alert_rejects_missing_detection_and_empty_resolution(isolated_client):
    assert isolated_client.post('/api/v1/alerts', headers=AUTH, json={'detection_id': str(uuid4()), 'title': 'QA', 'message': 'QA'}).status_code == 404
    assert isolated_client.patch(f'/api/v1/alerts/{uuid4()}/resolve', headers=AUTH, json={'notes': '   '}).status_code == 422


def test_zone_reference_does_not_invent_a_breach(isolated_client):
    zone = isolated_client.post('/api/v1/zones', headers=AUTH, json={
        'name': 'QA zero ceiling', 'coordinates': [[0, 0], [0, 1], [1, 0]], 'max_altitude': 0,
    })
    assert zone.status_code == 201
    response = isolated_client.post('/api/v1/detections', headers=AUTH, json={
        **POSITION, 'latitude': 0.1, 'longitude': 0.1, 'altitude': 50, 'zone_id': zone.json()['id'],
    })
    assert response.status_code == 422


def test_alert_assignment_requires_an_existing_authorized_user(isolated_client):
    alert = isolated_client.post('/api/v1/alerts', headers=AUTH, json={'title': 'QA assignment', 'message': 'Synthetic test'})
    assert alert.status_code == 201
    path = f"/api/v1/alerts/{alert.json()['id']}/assign"
    assert isolated_client.patch(path + '?user_id=invalid', headers=AUTH).status_code == 422
    assert isolated_client.patch(path + '?user_id=' + str(uuid4()), headers=AUTH).status_code == 404


@pytest.mark.parametrize('path', ['/api/v1/detections', '/api/v1/alerts', '/api/v1/users', '/api/v1/audit'])
def test_list_pagination_is_bounded(isolated_client, path):
    assert isolated_client.get(path + '?skip=-1', headers=AUTH).status_code == 422
    assert isolated_client.get(path + '?limit=1000000', headers=AUTH).status_code == 422
