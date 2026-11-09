from uuid import uuid4
from app.core.security import create_access_token

AUTH = {'Authorization': 'Bearer ' + create_access_token({'sub': 'admin', 'role': 'admin'})}


def test_trajectory_rejects_invalid_and_missing_detection(isolated_client):
    assert isolated_client.get('/api/v1/detections/invalid/trajectory', headers=AUTH).status_code == 422
    assert isolated_client.get(f'/api/v1/detections/{uuid4()}/trajectory', headers=AUTH).status_code == 404


def test_trajectory_preserves_sample_time_and_sorts_history(isolated_client):
    sensor = isolated_client.post('/api/v1/sensors', headers=AUTH, json={
        'name': 'QA trajectory', 'latitude': 0, 'longitude': 0,
    }).json()
    detection_ids = []
    for index, timestamp in enumerate(['2026-10-29T12:00:02Z', '2026-10-29T12:00:00Z', '2026-10-29T12:00:01Z']):
        response = isolated_client.post('/api/v1/sensors/telemetry', headers=AUTH, json={
            'sensor_id': sensor['id'], 'object_id': 'QA-TRAJECTORY', 'latitude': index / 100,
            'longitude': 0, 'altitude': 30, 'speed': 0, 'heading': 0, 'timestamp': timestamp,
        })
        assert response.status_code == 202
        detection_ids.append(response.json()['detection_id'])
    assert len(set(detection_ids)) == 1
    samples = isolated_client.get(f'/api/v1/detections/{detection_ids[0]}/trajectory', headers=AUTH).json()
    assert len(samples) == 3
    assert [p['latitude'] for p in samples] == [0.01, 0.02, 0]
    assert all(p['timestamp'].startswith('2026-10-29T12:00:0') for p in samples)
