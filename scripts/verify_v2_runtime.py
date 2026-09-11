"""Measure focused synthetic demos and SCADA banks on the real local 500-panel stack.

Does not inject frames or delete history. Scenario selections and a simulator restart
are real authorized demo operations. Run separately from browser scenario tests/load.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import struct
import time

from scripts.verify_stack import ROOT, compose, read_env, request, wait_health
from services.scada_bridge.master import read_panel_registers


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def database_probe(maximum=None):
    # All identifiers and code are fixed; no credentials are printed or persisted.
    code = '''import json, os
from sqlalchemy import create_engine,text
with create_engine(os.environ['DATABASE_URL']).connect() as db:
    maximum = MAXIMUM
    if maximum is None: maximum = db.execute(text('SELECT max(id) FROM telemetry')).scalar()
    row=db.execute(text("SELECT count(*) AS count, min(id) AS first_id, max(id) AS last_id, md5(string_agg(md5(concat_ws('|',id,device_id,panel_id,message_id,timestamp,payload::text,result::text)),'' ORDER BY id)) AS digest FROM telemetry WHERE id <= :maximum"), {'maximum':maximum}).mappings().one()
    print(json.dumps(dict(row)))
'''.replace('MAXIMUM', repr(maximum))
    return json.loads(compose('exec', '-T', 'api', 'python', '-c', code))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='docs/verification/v2-runtime.json')
    parser.add_argument('--preserve-before', action='store_true', help='Record immutable legacy row digest before deployment, then exit.')
    args = parser.parse_args()
    preservation_path = ROOT / 'docs/verification/v2-legacy-preservation.json'
    if args.preserve_before:
        preservation_path.write_text(json.dumps({'before': database_probe()}, indent=2), encoding='utf-8')
        print('Legacy row digest recorded; no data modified.', flush=True)
        return
    wait_health()
    env = read_env()
    status, login = request('/api/auth/login', {'username': env['ADMIN_USERNAME'], 'password': env['ADMIN_PASSWORD']})
    require(status == 200, 'Login failed')
    token = login['access_token']
    results = []

    def api(path, body=None):
        code, data = request(path, body, token)
        require(code == 200, f'{path}: HTTP {code}')
        return data

    def check(name, fn):
        start = time.monotonic()
        try:
            details = fn()
            results.append({'name': name, 'passed': True, 'seconds': round(time.monotonic() - start, 3), 'detail': details})
            print('PASS', name, flush=True)
        except Exception as exc:
            results.append({'name': name, 'passed': False, 'seconds': round(time.monotonic() - start, 3), 'detail': str(exc)})
            print('FAIL', name, str(exc), flush=True)

    def detail():
        return api('/api/panels/PNL-001')

    def select(scenario):
        return api('/api/demo/scenario', {'panel_id': 'PNL-001', 'scenario': scenario, 'focus': True})

    def until(predicate, timeout):
        deadline = time.monotonic() + timeout
        while True:
            data = detail()
            if predicate(data):
                return data
            if time.monotonic() >= deadline:
                raise AssertionError(f'Timeout {timeout}s; state={data.get("state")}, step={data.get("simulation_step")}')
            time.sleep(.5)

    api('/api/demo/fleet', {'count': 500})
    api('/api/demo/reset', {})
    # Wait for accepted explicit observations, not just a fixed sleep.
    deadline = time.monotonic() + 60
    while True:
        ready = api('/api/fleet')
        if len(ready['panels']) == 500 and all(p['communication_ok'] and not p['pending_current_run'] for p in ready['panels']):
            break
        require(time.monotonic() < deadline, '500 current runs did not become ready')
        time.sleep(1)

    def preserve():
        document = json.loads(preservation_path.read_text(encoding='utf-8'))
        document['after'] = database_probe(document['before']['last_id'])
        document['passed'] = document['before'] == document['after']
        preservation_path.write_text(json.dumps(document, indent=2), encoding='utf-8')
        require(document['passed'], 'Existing telemetry changed during migration')
        return document

    if preservation_path.exists():
        check('V1 PostgreSQL rows preserved through additive migration', preserve)

    measured = {}

    def combined():
        fleet_before = api('/api/fleet')
        metrics_before = api('/api/metrics')
        start = time.monotonic()
        run = select('combined_thermal_pd')
        current = until(lambda d: bool(d['current_run_history']), 8)
        first = current['current_run_history'][0]
        require(first['state'] == 'NORMAL' and first['risk_score'] == 8 and first['health_score'] == 96, 'First frame is not clean normal baseline')
        current = until(lambda d: d['demo_run_id'] == run['demo_run_id'] and not d['pending_current_run'] and d['state'] == 'CRITICAL', 75 - (time.monotonic() - start))
        elapsed = time.monotonic() - start
        require(elapsed <= 75, 'Critical exceeded 75 seconds')
        timeline = current['early_warning']
        require([row['state'] for row in timeline['transitions']][:4] == ['NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL'], 'Missing ordered warning transitions')
        require(timeline['lead_steps'] > 0 and timeline['unit'] == 'synthetic_demo_steps', 'No synthetic lead evidence')
        fleet_after = api('/api/fleet')
        metrics_after = api('/api/metrics')
        old = {panel['id']: panel['last_seen'] for panel in fleet_before['panels']}
        advanced = sum(panel['id'] != 'PNL-001' and panel['last_seen'] != old.get(panel['id']) for panel in fleet_after['panels'])
        require(fleet_after['summary']['total'] == 500 and advanced == 499, f'Background fleet did not all progress: {advanced}/499')
        require(fleet_after['summary']['offline'] == 0, 'Background panels offline')
        metric_seconds = (datetime.fromisoformat(metrics_after['timestamp']) - datetime.fromisoformat(metrics_before['timestamp'])).total_seconds()
        average = (metrics_after['accepted'] - metrics_before['accepted']) / metric_seconds
        measured.update(combined_run_id=run['demo_run_id'], combined_critical_seconds=round(elapsed, 3))
        return {'run': run, 'critical_seconds': round(elapsed, 3), 'first_frame': {k: first[k] for k in ['risk_score', 'health_score', 'state', 'simulation_step']}, 'early_warning': timeline, 'background_panels_advanced': advanced, 'fleet': fleet_after['summary'], 'observed_ingestion_fps': round(average, 3), 'ingestion_window_seconds': round(metric_seconds, 3), 'rate_note': 'API counter window; ingestion can drain a prior queue. Scheduler publication ceiling is independently tested with a virtual clock.', 'scheduler': {k: v for k, v in api('/api/demo/state').items() if k != 'panels'}}

    check('500 live panels: focused combined normal to critical within 75 seconds', combined)

    def clean():
        before = detail()
        run = select('normal_operation')
        pending = detail()
        require(pending['demo_run_id'] == run['demo_run_id'], 'New run not exposed')
        current = until(lambda d: not d['pending_current_run'] and len(d['current_run_history']) >= 3, 12)
        require(all(row['demo_run_id'] == run['demo_run_id'] and row['state'] == 'NORMAL' for row in current['current_run_history']), 'Old critical values leaked into current chart')
        require(not current['current_run_alarms'], 'Old alarm leaked into current run')
        require(current['full_history_total'] >= before['full_history_total'], 'History deleted')
        require(any(row['state'] == 'CRITICAL' and row['demo_run_id'] == measured['combined_run_id'] for row in current['full_history']), 'Measured combined critical no longer accessible')
        old_alarms = [row for row in current['historical_alarms'] if row['demo_run_id'] == measured['combined_run_id']]
        require(old_alarms and all(row['status'] == 'resolved' and row['resolution_reason'] == 'demo_run_superseded' for row in old_alarms), 'Measured combined alarm history not preserved with superseded reason')
        return {'run_id': run['demo_run_id'], 'current_rows': len(current['current_run_history']), 'history_before': before['full_history_total'], 'history_after': current['full_history_total'], 'historical_alarms': len(current['historical_alarms']), 'risk': current['risk_score'], 'health': current['health_score']}

    check('New normal run isolates charts and alarms while retaining historical critical', clean)

    def arc():
        start = time.monotonic()
        run = select('arc_event')
        current = until(lambda d: not d['pending_current_run'] and d['demo_run_id'] == run['demo_run_id'] and d['arc']['event'], 20)
        elapsed = time.monotonic() - start
        require(elapsed <= 20, 'Arc event exceeded 20 seconds')
        stamp = current['arc']['timestamp']
        compose('restart', 'simulator')
        time.sleep(5)
        after = detail()
        require(after['demo_run_id'] == run['demo_run_id'] and after['arc']['timestamp'] == stamp, 'Arc event timestamp changed after simulator restart')
        history = after['current_run_history']
        steps = [row['simulation_step'] for row in history]
        require(len(steps) == len(set(steps)) and max(steps) > max(row['simulation_step'] for row in current['current_run_history']), 'Restart duplicated or stopped run steps')
        measured.update(arc_run_id=run['demo_run_id'], arc_seconds=round(elapsed, 3))
        return {'run_id': run['demo_run_id'], 'arc_seconds': round(elapsed, 3), 'arc_timestamp': stamp, 'timestamp_preserved_after_simulator_restart': True, 'unique_current_steps': len(steps), 'detectors': after['arc']['detectors'], 'trip_relays': after['arc']['trip_relays']}

    check('Focused arc within 20 seconds and durable restart identity', arc)

    def banks():
        rows = []
        for number, bank, port, unit in [(1, 1, 1502, 1), (247, 1, 1502, 247), (248, 2, 1503, 1), (494, 2, 1503, 247), (495, 3, 1504, 1), (500, 3, 1504, 6)]:
            panel_id = f'PNL-{number:03d}'
            response = api('/api/scada/registers?panel_id=' + panel_id)
            require(response['connected'] and (response['bank'], response['port'], response['unit_id']) == (bank, port, unit), panel_id + ' API bank mismatch')
            registers = read_panel_registers('127.0.0.1', port, unit)
            require(len(registers) >= 12, panel_id + ' TCP register set incomplete')
            rows.append({'panel_id': panel_id, 'bank': bank, 'port': port, 'unit_id': unit, 'connected': True, 'transport': 'actual_modbus_tcp', 'registers': registers})
        for port in (1502, 1503, 1504):
            for function, address, value, expected in [(3, 60000, 1, 2), (6, 0, 0, 1), (16, 0, 1, 1)]:
                pdu = struct.pack('>BHH', function, address, value)
                if function == 16:
                    pdu += bytes([2, 0, 0])
                with socket.create_connection(('127.0.0.1', port), 3) as connection:
                    connection.sendall(struct.pack('>HHHB', 777, 0, len(pdu) + 1, 1) + pdu)
                    response = b''
                    while len(response) < 9:
                        part = connection.recv(1024)
                        if not part: break
                        response += part
                require(response[-2:] == bytes([function | 0x80, expected]), f'Bank {port} did not reject function/address')
        return {'boundaries': rows, 'all_three_banks_reject_invalid_registers_and_writes': True}

    check('Actual TCP across all six SCADA bank boundaries including PNL-500', banks)
    def notifications():
        items = api('/api/notifications')['items']
        rows = [row for row in items if row['demo_run_id'] == measured.get('arc_run_id')]
        require(rows and {row['channel'] for row in rows} == {'sms_mock', 'whatsapp_mock'}, 'Measured arc run missing both mock channels')
        require(all(row['status'] == 'simulated' for row in rows), 'Non-simulated notification')
        return {'arc_run_id': measured['arc_run_id'], 'count': len(rows), 'channels': sorted({row['channel'] for row in rows}), 'all_simulated': True}
    check('Measured arc creates both local simulated notification channels', notifications)
    # Presentation ends on a clean focus run; all historical evidence remains in DB.
    def presentation():
        run = select('normal_operation')
        current = until(lambda d: not d['pending_current_run'] and d['state'] == 'NORMAL', 10)
        return {'run_id': run['demo_run_id'], 'risk': current['risk_score'], 'state': current['state']}
    check('Restore clean normal presentation run', presentation)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'environment': 'actual local Docker/PostgreSQL/MQTT/three Modbus TCP banks', 'data': 'synthetic; elapsed demo time is not field prediction lead time', 'measurements': measured, 'checks': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', output, flush=True)
    if not all(row['passed'] for row in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
