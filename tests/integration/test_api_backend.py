from datetime import datetime, timedelta, timezone
import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import OperationalError
from apps.api.main import create_app
from apps.api.settings import Settings
from apps.api.database import Panel, Telemetry
from apps.api.security import derive_device_key, decode_token, issue_token
from services.simulator.scenarios import generate_frame, load_replay

@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f'sqlite:///{tmp_path / "test.db"}', auth_secret=secrets.token_hex(32),
                    service_token=secrets.token_hex(32), device_token=secrets.token_hex(32), admin_username='admin',
                    passwords={role: secrets.token_urlsafe(16) for role in ('admin', 'operator', 'viewer')},
                    panel_count=3, mqtt_enabled=False, rate_limit=10000, stale_seconds=20,
                    scada_host='127.0.0.1', scada_port=1)

@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client

def token(client, settings, role='admin'):
    response = client.post('/api/auth/login', json={'username': role, 'password': settings.passwords[role]})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}

def payload(settings, step=0, scenario='normal_operation', timestamp=None, message_id=None):
    frame = generate_frame('PNL-001', scenario, step, load_replay(),
                           timestamp=timestamp, message_id=message_id)
    frame['device_key'] = derive_device_key(settings.device_token, frame['device_id'])
    return frame

def send(client, settings, frame):
    return client.post('/api/telemetry', json=frame, headers={'Authorization': 'Bearer ' + settings.service_token})

def test_auth_roles_and_validation(client, settings):
    assert client.get('/health').status_code == 200
    assert client.get('/api/fleet').status_code == 401
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'}).status_code == 401
    viewer = token(client, settings, 'viewer')
    assert client.get('/api/fleet', headers=viewer).status_code == 200
    assert client.post('/api/demo/scenario', json={'scenario': 'arc_event'}, headers=viewer).status_code == 403
    assert client.get('/api/audit', headers=viewer).status_code == 403
    assert client.post('/api/telemetry', json=payload(settings), headers=viewer).status_code == 403
    admin = token(client, settings)
    assert client.get('/api/audit', headers=admin).status_code == 200
    assert client.post('/api/demo/scenario', json={'scenario': 'not_real'}, headers=admin).status_code == 422
    assert client.post('/api/demo/scenario', json={'scenario': 'arc_event', 'panel_id': 'PNL-999'}, headers=admin).status_code == 404

def test_durable_dedupe_and_out_of_order_survive_restart(settings):
    frame = payload(settings, message_id='durable-message')
    with TestClient(create_app(settings)) as first:
        assert send(first, settings, frame).json()['accepted']
        assert send(first, settings, frame).json()['status'] == 'duplicate'
        with first.app.state.runtime.engine.begin() as connection:
            connection.execute(text('DROP INDEX ix_telemetry_panel_timestamp'))
    with TestClient(create_app(settings)) as second:
        assert 'ix_telemetry_panel_timestamp' in {index['name'] for index in inspect(second.app.state.runtime.engine).get_indexes('telemetry')}
        assert send(second, settings, frame).json()['status'] == 'duplicate'
        # Anchor the ordering boundary to the accepted frame, independent of restart duration.
        older = payload(settings, timestamp=datetime.fromisoformat(frame['timestamp']) - timedelta(seconds=1), message_id='older')
        assert send(second, settings, older).status_code == 409
        assert second.get('/api/metrics', headers={'Authorization': 'Bearer ' + settings.service_token}).json()['telemetry_rows'] == 1

def test_bound_device_identity(client, settings):
    frame = payload(settings)
    frame['panel_id'] = 'PNL-002'
    assert send(client, settings, frame).status_code == 403
    frame['panel_id'] = 'PNL-001'
    frame['device_key'] = 'incorrect-key'
    assert send(client, settings, frame).status_code == 403
    assert client.get('/api/metrics', headers={'Authorization': 'Bearer ' + settings.service_token}).json()['telemetry_rows'] == 0

def test_rejects_naive_future_nonfinite_unknown_and_oversized(client, settings):
    frame = payload(settings)
    frame['timestamp'] = '2026-01-01T12:00:00'
    assert send(client, settings, frame).status_code == 422
    frame = payload(settings, timestamp=datetime.now(timezone.utc) + timedelta(hours=1))
    assert send(client, settings, frame).status_code == 422
    frame = payload(settings)
    frame['measurements']['invented_channel'] = 4
    assert send(client, settings, frame).status_code == 422
    response = client.post('/api/telemetry', content='x' * 40000, headers={'Content-Type': 'application/json'})
    assert response.status_code == 413

def test_alarm_acknowledge_resolve_and_mock_notification_dedup(client, settings):
    admin, operator = token(client, settings), token(client, settings, 'operator')
    timestamp = datetime.now(timezone.utc)
    assert send(client, settings, payload(settings, 10, 'arc_event', timestamp)).status_code == 200
    alarms = client.get('/api/alarms', headers=admin).json()['items']
    arc_alarm = next(a for a in alarms if a['kind'] == 'arc')
    assert arc_alarm['severity'] == 'CRITICAL'
    initial_notifications = client.get('/api/notifications', headers=admin).json()['items']
    assert all(n['status'] == 'simulated' and 'mock' in n['channel'] for n in initial_notifications)
    assert client.post(f'/api/alarms/{arc_alarm["id"]}/acknowledge', headers=operator).json()['status'] == 'acknowledged'
    assert send(client, settings, payload(settings, 11, 'arc_event', timestamp + timedelta(milliseconds=1))).status_code == 200
    assert len(client.get('/api/notifications', headers=admin).json()['items']) == len(initial_notifications)
    assert send(client, settings, payload(settings, 0, 'normal_operation', timestamp + timedelta(milliseconds=2))).status_code == 200
    alarms = client.get('/api/alarms', headers=admin).json()['items']
    assert all(a['status'] == 'resolved' for a in alarms)
    assert client.post(f'/api/alarms/{arc_alarm["id"]}/acknowledge', headers=operator).status_code == 409

def test_missing_invalid_stuck_and_stale_channels(client, settings):
    admin = token(client, settings)
    now = datetime.now(timezone.utc)
    for step in range(13):
        frame = payload(settings, step, timestamp=now + timedelta(milliseconds=step))
        frame['measurements']['temperature_c'] = 37.5
        assert send(client, settings, frame).status_code == 200
    panel = client.get('/api/panels/PNL-001', headers=admin).json()
    assert panel['quality']['temperature_c'] == 'stuck'
    failure = payload(settings, 15, 'sensor_failure', timestamp=now + timedelta(milliseconds=15))
    assert send(client, settings, failure).status_code == 200
    panel = client.get('/api/panels/PNL-001', headers=admin).json()
    assert panel['measurements']['temperature_c'] is None
    assert panel['quality']['humidity_pct'] == 'invalid'
    rt = client.app.state.runtime
    with rt.sessions.begin() as db:
        stored = db.get(Panel, 'PNL-001')
        stored.received_at = now - timedelta(seconds=30)
    rt.mark_stale()
    panel = client.get('/api/panels/PNL-001', headers=admin).json()
    assert panel['communication_ok'] is False and panel['health_score'] == 0
    assert panel['state'] in {'WARNING', 'CRITICAL'}
    assert panel['quality']['current_l1'] == 'stale'

def test_scenario_control_fleet_expansion_and_reset_preserve_history(client, settings):
    admin = token(client, settings)
    assert send(client, settings, payload(settings)).status_code == 200
    result = client.post('/api/demo/scenario', json={'scenario': 'combined_thermal_pd'}, headers=admin)
    assert result.status_code == 200
    state = client.get('/api/demo/state', headers=admin).json()['panels']
    assert state[0]['scenario'] == 'combined_thermal_pd' and state[0]['revision'] == 2
    assert client.post('/api/demo/fleet', json={'count': 100}, headers=admin).json()['count'] == 100
    assert client.post('/api/demo/fleet', json={'count': 2}, headers=admin).json()['count'] == 100
    assert client.post('/api/demo/reset', headers=admin).status_code == 200
    assert client.get('/api/metrics', headers=admin).json()['telemetry_rows'] == 1

def test_scada_unavailable_is_not_reported_connected(client, settings):
    admin = token(client, settings)
    result = client.get('/api/scada/registers', headers=admin).json()
    assert result['connected'] is False and result['registers'] == [] and result['error']

def test_tampered_and_expired_tokens(client, settings):
    valid = issue_token('admin', 'admin', settings.auth_secret, 100)
    assert client.get('/api/fleet', headers={'Authorization': 'Bearer ' + valid[:-2] + 'xx'}).status_code == 401
    expired = issue_token('admin', 'admin', settings.auth_secret, -1)
    assert client.get('/api/fleet', headers={'Authorization': 'Bearer ' + expired}).status_code == 401

def test_service_cannot_mutate_scenarios_or_read_audit(client, settings):
    service = {'Authorization': 'Bearer ' + settings.service_token}
    assert client.post('/api/demo/scenario', json={'scenario': 'arc_event'}, headers=service).status_code == 403
    assert client.get('/api/audit', headers=service).status_code == 403

def test_database_failure_is_explicit_503(client, monkeypatch):
    def unavailable():
        raise OperationalError('SELECT 1', {}, Exception('test database unavailable'))
    monkeypatch.setattr(client.app.state.runtime, 'sessions', unavailable)
    response = client.get('/health')
    assert response.status_code == 503
    assert response.json()['database'] == 'unavailable'

def test_request_rate_limit_does_not_hide_health(client, settings):
    client.app.state.runtime.settings.rate_limit = 1
    bearer = {'Authorization': 'Bearer ' + settings.service_token}
    assert client.get('/api/fleet', headers=bearer).status_code == 200
    limited = client.get('/api/fleet', headers=bearer)
    assert limited.status_code == 429 and limited.headers['Retry-After'] == '60'
    assert client.get('/health').status_code == 200

def test_notification_only_on_new_or_higher_severity(client, settings):
    admin = token(client, settings)
    now = datetime.now(timezone.utc)
    frame = payload(settings, timestamp=now)
    frame['measurements']['temperature_c'] = 55
    assert send(client, settings, frame).status_code == 200
    count = len(client.get('/api/notifications', headers=admin).json()['items'])
    assert count == 0  # ATTENTION has a persistent alarm, but no mock delivery.
    frame = payload(settings, timestamp=now + timedelta(milliseconds=1))
    frame['measurements'].update(temperature_c=70, pd_baseline_ratio=3)
    assert send(client, settings, frame).json()['state'] == 'CRITICAL'
    assert len(client.get('/api/notifications', headers=admin).json()['items']) == count + 2
    frame['timestamp'] = (now + timedelta(milliseconds=2)).isoformat()
    frame['message_id'] += '-repeat'
    assert send(client, settings, frame).status_code == 200
    assert len(client.get('/api/notifications', headers=admin).json()['items']) == count + 2

def test_busy_writer_is_retryable_503_without_blocking_reads(client, settings):
    import threading
    import time
    rt = client.app.state.runtime
    rt.stop.set()
    rt.settings.write_lock_timeout_seconds = .05
    acquired, release = threading.Event(), threading.Event()

    def blocked_writer():
        with rt.lock:
            acquired.set()
            release.wait(5)

    holder = threading.Thread(target=blocked_writer)
    holder.start()
    assert acquired.wait(1)
    frame = payload(settings, message_id='retry-after-writer-timeout')
    service = {'Authorization': 'Bearer ' + settings.service_token}
    try:
        began = time.monotonic()
        response = send(client, settings, frame)
        assert response.status_code == 503 and response.headers['Retry-After'] == '5'
        assert time.monotonic() - began < 1
        assert response.json()['status'] == 'degraded'
        began = time.monotonic()
        assert client.get('/api/panels/PNL-001', headers=service).status_code == 200
        assert client.get('/api/fleet', headers=service).status_code == 200
        assert time.monotonic() - began < 1
        assert rt.metrics['write_lock_timeouts'] == 1
    finally:
        release.set()
        holder.join(1)
    assert send(client, settings, frame).json()['status'] == 'accepted'
    assert send(client, settings, frame).json()['status'] == 'duplicate'
    assert client.get('/api/metrics', headers=service).json()['telemetry_rows'] == 1
