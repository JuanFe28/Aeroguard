"""Regresiones del QA de escritorio del 28 de octubre."""
import pytest
from app.core.security import create_access_token

AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}
POLYGON = [[7.1, -73.2], [7.2, -73.2], [7.2, -73.1]]


@pytest.mark.parametrize('payload', [{}, {'drone': {}}, {'zone': {}}])
def test_soar_does_not_invent_missing_telemetry(isolated_client, payload):
    response = isolated_client.post('/api/v1/alerts/trigger-incident', headers=AUTH, json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize('values', [
    {'min_altitude': 300, 'max_altitude': 100, 'coordinates': POLYGON},
    {'min_altitude': -1, 'coordinates': POLYGON},
    {'max_altitude': 15001, 'coordinates': POLYGON},
    {'coordinates': []},
    {'coordinates': [[7, -73]] * 3},
    {'coordinates': [[91, -73], [7, -73], [8, -72]]},
    {'coordinates': [['invalid', -73], [7, -73], [8, -72]]},
    {'coordinates': [{'lat': 7}, [7, -73], [8, -72]]},
])
def test_invalid_zone_is_rejected(isolated_client, values):
    response = isolated_client.post('/api/v1/zones', headers=AUTH, json={'name': 'QA invalid', **values})
    assert response.status_code == 422


def test_zone_draft_activation_and_partial_altitude_update(isolated_client):
    response = isolated_client.post('/api/v1/zones', headers=AUTH, json={
        'name': 'QA draft', 'is_active': False, 'min_altitude': 100, 'max_altitude': 200,
    })
    assert response.status_code == 201
    path = '/api/v1/zones/' + response.json()['id']
    assert isolated_client.put(path, headers=AUTH, json={'is_active': True}).status_code == 422
    assert isolated_client.put(path, headers=AUTH, json={'max_altitude': 50}).status_code == 422
    response = isolated_client.put(path, headers=AUTH, json={'coordinates': POLYGON, 'is_active': True})
    assert response.status_code == 200
    assert response.json()['is_active'] is True
    assert response.json()['max_altitude'] == 200


def test_zone_accepts_equator_and_prime_meridian(isolated_client):
    response = isolated_client.post('/api/v1/zones', headers=AUTH, json={
        'name': 'QA zero coordinates',
        'coordinates': [{'lat': 0, 'lng': 0}, {'lat': 0, 'lng': 1}, {'lat': 1, 'lng': 0}],
    })
    assert response.status_code == 201
    assert response.json()['coordinates'] == [[0, 0], [0, 1], [1, 0]]
