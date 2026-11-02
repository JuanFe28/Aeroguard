"""Aceptación RBAC con usuarios persistidos y JWT obtenidos por login real."""
from uuid import uuid4
import pytest
from app.core.config import settings
from app.core.security import create_access_token


@pytest.fixture
def accounts(isolated_client):
    admin = {'Authorization': 'Bearer ' + create_access_token({'sub': 'admin', 'role': 'admin'})}
    result = {}
    for role in ['admin', 'operator', 'analyst']:
        username = 'qa_' + uuid4().hex[:12]
        password = 'QA-test-only@12345'
        response = isolated_client.post('/api/v1/users', headers=admin, json={
            'username': username, 'email': username + '@example.com', 'password': password,
            'first_name': 'QA', 'last_name': role, 'role': role,
        })
        assert response.status_code == 201, response.text
        login = isolated_client.post('/api/v1/auth/token', data={'username': username, 'password': password})
        assert login.status_code == 200
        result[role] = {'id': response.json()['id'], 'username': username, 'password': password,
                        'headers': {'Authorization': 'Bearer ' + login.json()['access_token']}}
    return result


@pytest.mark.parametrize('role,path,expected', [
    ('operator', '/api/v1/users', 403), ('operator', '/api/v1/config', 403),
    ('operator', '/api/v1/reports', 403), ('operator', '/api/v1/audit', 403),
    ('analyst', '/api/v1/users', 403), ('analyst', '/api/v1/config', 403),
    ('analyst', '/api/v1/reports', 200), ('analyst', '/api/v1/audit', 200),
    ('operator', '/api/v1/detections', 200), ('analyst', '/api/v1/detections', 200),
])
def test_actual_roles_enforced_in_production(isolated_client, accounts, monkeypatch, role, path, expected):
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    assert isolated_client.get(path, headers=accounts[role]['headers']).status_code == expected


def test_deactivation_and_reactivation_require_new_login(isolated_client, accounts, monkeypatch):
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    operator = accounts['operator']
    path = '/api/v1/users/' + operator['id'] + '/status'
    admin = accounts['admin']['headers']
    assert isolated_client.patch(path + '?active=false', headers=admin).status_code == 200
    assert isolated_client.get('/api/v1/detections', headers=operator['headers']).status_code in (401, 403)
    assert isolated_client.post('/api/v1/auth/token', data={'username': operator['username'], 'password': operator['password']}).status_code in (401, 403)
    assert isolated_client.patch(path + '?active=true', headers=admin).status_code == 200
    assert isolated_client.get('/api/v1/detections', headers=operator['headers']).status_code == 401
    login = isolated_client.post('/api/v1/auth/token', data={'username': operator['username'], 'password': operator['password']})
    assert login.status_code == 200
    assert isolated_client.get('/api/v1/detections', headers={'Authorization': 'Bearer ' + login.json()['access_token']}).status_code == 200


def test_role_change_revokes_token_and_uses_persisted_role(isolated_client, accounts, monkeypatch):
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    analyst = accounts['analyst']
    response = isolated_client.put('/api/v1/users/' + analyst['id'], headers=accounts['admin']['headers'], json={'role': 'operator'})
    assert response.status_code == 200
    assert isolated_client.get('/api/v1/reports', headers=analyst['headers']).status_code == 401
    login = isolated_client.post('/api/v1/auth/token', data={'username': analyst['username'], 'password': analyst['password']})
    assert login.status_code == 200
    assert isolated_client.get('/api/v1/reports', headers={'Authorization': 'Bearer ' + login.json()['access_token']}).status_code == 403


def test_admin_cannot_disable_or_demote_own_session(isolated_client, accounts, monkeypatch):
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    admin = accounts['admin']
    path = '/api/v1/users/' + admin['id']
    assert isolated_client.patch(path + '/status?active=false', headers=admin['headers']).status_code == 400
    assert isolated_client.put(path, headers=admin['headers'], json={'role': 'operator'}).status_code == 400
