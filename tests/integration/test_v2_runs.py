from datetime import datetime, timedelta, timezone
import json
import secrets
import sqlite3
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from apps.api.database import Alarm, Event, Notification, Panel, SchemaMigration, Telemetry
from apps.api.main import create_app
from apps.api.settings import Settings
from apps.api.security import derive_device_key
from services.simulator.scenarios import generate_frame, load_replay
from services.simulator.scheduler import telemetry_message_id

@pytest.fixture
def config(tmp_path):
    return Settings(database_url=f'sqlite:///{tmp_path / "v2.db"}', auth_secret=secrets.token_hex(32),
                    service_token=secrets.token_hex(32), device_token=secrets.token_hex(32), admin_username='admin',
                    passwords={role: secrets.token_urlsafe(16) for role in ('admin', 'operator', 'viewer')},
                    panel_count=3, mqtt_enabled=False, rate_limit=10000)

@pytest.fixture
def api(config):
    with TestClient(create_app(config)) as client:
        login = client.post('/api/auth/login', json={'username': 'admin', 'password': config.passwords['admin']}).json()
        client.headers['Authorization'] = 'Bearer ' + login['access_token']
        yield client

def select_run(api, scenario, panel_id='PNL-001', focus=True):
    response = api.post('/api/demo/scenario', json={'scenario': scenario, 'panel_id': panel_id, 'focus': focus})
    assert response.status_code == 200
    return response.json()

def frame(config, run, step=0, timestamp=None):
    document = generate_frame(run['panel_id'], run['scenario'], step, load_replay(), timestamp=timestamp)
    document.update(demo_run_id=run['demo_run_id'], scenario_revision=run['scenario_revision'], focused_demo=run['focused_demo'],
                    demo_interval_seconds=1.5, device_key=derive_device_key(config.device_token, document['device_id']))
    return document

def test_switch_keeps_old_critical_history_but_current_run_is_clean(api, config):
    old = select_run(api, 'arc_event')
    assert api.post('/api/telemetry', json=frame(config, old, 8)).json()['state'] == 'CRITICAL'
    normal = select_run(api, 'normal_operation')
    pending = api.get('/api/panels/PNL-001').json()
    assert pending['pending_current_run'] is True
    assert pending['current_run_history'] == [] and pending['current_run_alarms'] == [] and pending['actions'] == []
    assert any(row['state'] == 'CRITICAL' for row in pending['full_history'])
    assert all(alarm['resolution_reason'] == 'demo_run_superseded' for alarm in pending['historical_alarms'])
    assert api.post('/api/telemetry', json=frame(config, normal, 0)).json()['state'] == 'NORMAL'
    current = api.get('/api/panels/PNL-001').json()
    assert current['pending_current_run'] is False and current['risk_score'] == 8
    assert {row['state'] for row in current['current_run_history']} == {'NORMAL'}
    assert current['explanation']['trend'] == {}
    assert any(row['state'] == 'CRITICAL' for row in current['full_history'])
    assert len(api.get('/api/audit').json()['items']) >= 4
    assert api.get('/api/alarms?scope=current').json()['items'] == []

def test_mismatched_run_cannot_change_snapshot_and_duplicate_remains_idempotent(api, config):
    old = select_run(api, 'arc_event')
    accepted = frame(config, old, 8)
    assert api.post('/api/telemetry', json=accepted).status_code == 200
    current = select_run(api, 'normal_operation')
    assert api.post('/api/telemetry', json=accepted).json()['status'] == 'duplicate'
    assert api.post('/api/telemetry', json=frame(config, old, 9)).status_code == 409
    assert api.post('/api/telemetry', json=frame(config, current, 0)).status_code == 200
    duplicate_step = frame(config, current, 0)
    assert api.post('/api/telemetry', json=duplicate_step).status_code == 409
    detail = api.get('/api/panels/PNL-001').json()
    assert detail['risk_score'] == 8 and len(detail['current_run_history']) == 1
    assert api.get('/api/metrics').json()['run_rejected'] == 1

def test_legacy_payload_is_accepted_but_never_assigned_to_current_run(api, config):
    selected = select_run(api, 'normal_operation')
    legacy = frame(config, selected, 0)
    legacy.pop('demo_run_id')
    legacy.pop('scenario_revision')
    legacy['measurements']['temperature_c'] = 85
    assert api.post('/api/telemetry', json=legacy).status_code == 200
    detail = api.get('/api/panels/PNL-001').json()
    assert detail['current_run_history'] == [] and detail['pending_current_run']
    assert detail['full_history'][0]['demo_run_id'] is None
    assert api.post('/api/telemetry', json=frame(config, selected, 0)).json()['risk_score'] == 8
    detail = api.get('/api/panels/PNL-001').json()
    assert len(detail['current_run_history']) == 1 and detail['explanation']['trend'] == {}

def test_full_history_pagination_and_alarm_filters(api, config):
    selected = select_run(api, 'arc_event')
    for step in range(8, 14):
        assert api.post('/api/telemetry', json=frame(config, selected, step)).status_code == 200
    first = api.get('/api/panels/PNL-001/history?scope=current&limit=2').json()
    assert first['total'] == 6 and len(first['items']) == 2 and first['next_before_id']
    second = api.get(f'/api/panels/PNL-001/history?scope=current&limit=2&before_id={first["next_before_id"]}').json()
    assert not {item['id'] for item in first['items']} & {item['id'] for item in second['items']}
    assert all(item['simulation_step'] < first['items'][0]['simulation_step'] for item in second['items'])
    alarms = api.get('/api/alarms?scope=current&status=active&severity=CRITICAL').json()['items']
    assert alarms and all(alarm['is_current_run'] for alarm in alarms)

def test_early_warning_is_structured_from_durable_current_run_transitions(api, config):
    selected = select_run(api, 'combined_thermal_pd')
    for step in range(45):
        assert api.post('/api/telemetry', json=frame(config, selected, step)).status_code == 200
    detail = api.get('/api/panels/PNL-001').json()
    timeline = detail['early_warning']
    assert [event['state'] for event in timeline['transitions']][:4] == ['NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL']
    assert timeline['status'] == 'demonstrated' and timeline['lead_steps'] > 0
    assert timeline['lead_steps'] == timeline['critical_step'] - timeline['warning_step']
    assert timeline['unit'] == 'synthetic_demo_steps'
    notifications = api.get('/api/notifications').json()['items']
    assert notifications and all(item['demo_run_id'] == selected['demo_run_id'] and item['status'] == 'simulated' for item in notifications)

def test_action_policy_results_match_deduplicated_mock_records_and_arc_audit(api, config):
    selected = select_run(api, 'arc_event')
    assert api.post('/api/telemetry', json=frame(config, selected, 8)).status_code == 200
    detail = api.get('/api/panels/PNL-001').json()
    actions = [action for action in detail['actions'] if action['type'] == 'notification']
    assert actions and all(action['status'] == 'simulated' and action['channel'].endswith('_mock') for action in actions)
    count = len(api.get('/api/notifications').json()['items'])
    assert api.post('/api/telemetry', json=frame(config, selected, 9)).status_code == 200
    detail = api.get('/api/panels/PNL-001').json()
    assert all(action['status'] == 'deduplicated' for action in detail['actions'] if action['type'] == 'notification')
    assert len(api.get('/api/notifications').json()['items']) == count
    assert any(item['action'] == 'synthetic_arc_event' for item in api.get('/api/audit').json()['items'])
    assert len(api.get('/api/action-policy').json()['items']) == 6


def test_fleet_counts_only_owning_current_run_active_or_acknowledged_alarms(api):
    rt = api.app.state.runtime
    with rt.sessions.begin() as db:
        runs = {p.id: rt.run_id(p) for p in db.scalars(select(Panel))}
        samples = [
            ('PNL-001', runs['PNL-001'], 'active'),
            ('PNL-002', runs['PNL-002'], 'acknowledged'),
            ('PNL-003', runs['PNL-003'], 'resolved'),
            ('PNL-001', 'PNL-001-r0', 'active'),
            ('PNL-001', None, 'acknowledged'),
            ('PNL-003', runs['PNL-001'], 'active'),  # Another panel's identity cannot qualify.
            ('PNL-002', runs['PNL-002'], 'deferred'),
        ]
        for panel_id, run_id, status in samples:
            db.add(Alarm(panel_id=panel_id, panel_name=panel_id, demo_run_id=run_id,
                         kind='condition', severity='ATTENTION', title='Regression fixture',
                         message='Synthetic historical alarm', status=status))
        db.flush()
        before = list(db.execute(select(Alarm.id, Alarm.panel_id, Alarm.demo_run_id, Alarm.status)))
    assert api.get('/api/fleet').json()['summary']['open_alarms'] == 2
    assert len(api.get('/api/alarms?scope=all').json()['items']) == len(samples)
    with rt.sessions.begin() as db:
        assert list(db.execute(select(Alarm.id, Alarm.panel_id, Alarm.demo_run_id, Alarm.status))) == before
        for alarm in db.scalars(select(Alarm).where(Alarm.id.in_([before[0].id, before[1].id]))):
            alarm.status = 'resolved'
    assert api.get('/api/fleet').json()['summary']['open_alarms'] == 0
    assert len(api.get('/api/alarms?scope=all').json()['items']) == len(samples)


def test_attention_keeps_alarm_event_and_scada_without_mock_then_warning_escalates_once(api, config):
    from services.scada_bridge.registers import encode_panel
    selected = select_run(api, 'combined_thermal_pd')
    observed = set()
    attention_alarm = None
    for step in range(23):
        assert api.post('/api/telemetry', json=frame(config, selected, step)).status_code == 200
        detail = api.get('/api/panels/PNL-001').json()
        notifications = api.get('/api/notifications').json()['items']
        if detail['state'] == 'ATTENTION':
            observed.add('ATTENTION')
            assert notifications == []
            assert not any(a['type'] == 'notification' for a in detail['actions'])
            assert {'dashboard_state', 'event_log', 'persistent_alarm', 'scada_alarm_flag',
                    'operator_recommendation'} <= {a['type'] for a in detail['actions']}
            assert encode_panel(detail)[3] == 1
            alarms = detail['current_run_alarms']
            assert len(alarms) == 1 and alarms[0]['severity'] == 'ATTENTION'
            attention_alarm = alarms[0]['id']
            assert any(e['type'] == 'alarm_created' for e in detail['current_run_events'])
            assert api.post(f'/api/alarms/{attention_alarm}/acknowledge').status_code == 200
            assert api.get('/api/fleet').json()['summary']['open_alarms'] == 1
        elif detail['state'] == 'WARNING':
            observed.add('WARNING')
            assert len(notifications) == 2
            assert {n['channel'] for n in notifications} == {'sms_mock', 'whatsapp_mock'}
            assert all(n['status'] == 'simulated' and n['alarm_id'] == attention_alarm for n in notifications)
            assert detail['current_run_alarms'][0]['status'] == 'active'
            assert any(a['type'] == 'maintenance_recommendation' for a in detail['actions'])
    assert observed == {'ATTENTION', 'WARNING'}

def test_focus_is_single_and_progress_survives_api_restart(config):
    with TestClient(create_app(config)) as api:
        login = api.post('/api/auth/login', json={'username': 'admin', 'password': config.passwords['admin']}).json()
        api.headers['Authorization'] = 'Bearer ' + login['access_token']
        api.post('/api/demo/fleet', json={'count': 500})
        select_run(api, 'combined_thermal_pd')
        selected = select_run(api, 'arc_event', 'PNL-500')
        assert api.post('/api/telemetry', json=frame(config, selected, 8)).status_code == 200
        state = api.get('/api/demo/state').json()
        assert state['focus_panel_id'] == 'PNL-500'
        assert sum(panel['focused_demo'] for panel in state['panels']) == 1
        assert state['background_fps_budget'] + 1 / state['focus_interval_seconds'] == pytest.approx(50)
    with TestClient(create_app(config)) as api:
        api.headers['Authorization'] = 'Bearer ' + config.service_token
        state = api.get('/api/demo/state').json()
        panel = next(panel for panel in state['panels'] if panel['id'] == 'PNL-500')
        assert panel['last_step'] == 8 and panel['demo_run_id'] == selected['demo_run_id'] and panel['arc_event_timestamp']

def test_v1_sqlite_migration_preserves_legacy_records_without_guessing_run(config):
    path = config.database_url.removeprefix('sqlite:///')
    sample = generate_frame('PNL-001', 'normal_operation', 0, load_replay())
    result = {'risk_score': 8, 'health_score': 96, 'state': 'NORMAL'}
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE telemetry (id INTEGER PRIMARY KEY, device_id VARCHAR(24), panel_id VARCHAR(20), message_id VARCHAR(128), timestamp DATETIME, received_at DATETIME, payload JSON, result JSON)')
        db.execute('INSERT INTO telemetry VALUES (1,?,?,?,?,?,?,?)', ('EDGE-001', 'PNL-001', 'v1-preserved', sample['timestamp'], sample['timestamp'], json.dumps(sample), json.dumps(result)))
    with TestClient(create_app(config)) as api:
        api.headers['Authorization'] = 'Bearer ' + config.service_token
        full = api.get('/api/panels/PNL-001/history').json()
        assert full['total'] == 1 and full['items'][0]['demo_run_id'] is None
        assert api.get('/api/panels/PNL-001/history?scope=current').json()['total'] == 0
        rt = api.app.state.runtime
        with rt.sessions() as db:
            assert db.get(SchemaMigration, 2)
            assert db.get(Telemetry, 1).message_id == 'v1-preserved'
        indexes = {item['name'] for item in inspect(rt.engine).get_indexes('telemetry')}
        assert {'ix_telemetry_panel_run_timestamp', 'uq_telemetry_run_step'} <= indexes

def test_restart_replay_uses_stable_run_step_idempotency_key(config):
    with TestClient(create_app(config)) as first:
        login = first.post('/api/auth/login', json={'username': 'admin', 'password': config.passwords['admin']}).json()
        first.headers['Authorization'] = 'Bearer ' + login['access_token']
        selected = select_run(first, 'normal_operation')
        queued = frame(config, selected, 0)
        queued['message_id'] = telemetry_message_id(selected['demo_run_id'], 0)
        assert first.post('/api/telemetry', json=queued).json()['accepted'] is True
    with TestClient(create_app(config)) as restarted:
        restarted.headers['Authorization'] = 'Bearer ' + config.service_token
        retry = frame(config, selected, 0)
        retry['message_id'] = telemetry_message_id(selected['demo_run_id'], 0)
        assert retry['message_id'] == queued['message_id']
        assert restarted.post('/api/telemetry', json=retry).json()['status'] == 'duplicate'
        assert restarted.get('/api/metrics').json()['telemetry_rows'] == 1
        assert restarted.get('/api/demo/state').json()['panels'][0]['last_step'] == 0

@pytest.mark.parametrize('scenario,step,expected', [('normal_operation', 0, 'WARNING'), ('arc_event', 8, 'CRITICAL')])
def test_stale_reads_preserve_risk_and_run_without_waiting_for_maintenance(api, config, scenario, step, expected):
    import threading
    import time
    rt = api.app.state.runtime
    rt.stop.set()  # Deterministically exercise the read projection before maintenance runs.
    selected = select_run(api, scenario)
    assert api.post('/api/telemetry', json=frame(config, selected, step)).status_code == 200
    with rt.sessions.begin() as db:
        panel = db.get(Panel, 'PNL-001')
        panel.received_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    release, acquired = threading.Event(), threading.Event()

    def busy_maintenance():
        with rt.lock:
            acquired.set()
            release.wait(5)

    worker = threading.Thread(target=busy_maintenance)
    worker.start()
    assert acquired.wait(1)
    before = api.get('/api/notifications').json()['items']
    try:
        began = time.monotonic()
        projected = api.get('/api/panels/PNL-001').json()
        fleet = api.get('/api/fleet').json()
        assert time.monotonic() - began < 1
        for item in [projected, next(panel for panel in fleet['panels'] if panel['id'] == 'PNL-001')]:
            assert item['state'] == expected and item['health_score'] == 0
            assert item['communication_ok'] is False and item['sensor_health'] == 0
            assert item['quality']['current_l1'] == 'stale' and item['alarm_active'] is True
            assert item['pending_current_run'] is False and item['demo_run_id'] == selected['demo_run_id']
            assert any(action['type'] == 'stale_data' for action in item['actions'])
            assert all(action['status'] == 'eligible' for action in item['actions'] if action['type'] == 'notification')
        assert api.get('/api/notifications').json()['items'] == before
        with rt.sessions() as db:
            assert db.get(Panel, 'PNL-001').snapshot['communication_ok'] is True
    finally:
        release.set()
        worker.join(1)
    rt.mark_stale()
    persisted = api.get('/api/panels/PNL-001').json()
    assert persisted['state'] == projected['state'] and persisted['risk_score'] == projected['risk_score']
    assert any(alarm['kind'] == 'availability' and alarm['status'] == 'active' for alarm in persisted['current_run_alarms'])
    notifications = api.get('/api/notifications').json()['items']
    if scenario == 'arc_event':
        assert len(notifications) > len(before)  # Arc remains urgent even with lost communication.
    else:
        assert notifications == before  # Availability-only policy has no SMS/WhatsApp.
    rt.mark_stale()
    assert api.get('/api/notifications').json()['items'] == notifications
    select_run(api, 'normal_operation')
    pending = api.get('/api/panels/PNL-001').json()
    assert pending['pending_current_run'] is True and pending['actions'] == [] and pending['demo_step'] is None
