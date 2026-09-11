"""Read-only final readiness proof. Run after selecting a clean 500-panel normal demo."""
import json
import time
from datetime import datetime, timezone
from scripts.verify_stack import ROOT, compose, read_env, request


def main():
    config = read_env()
    status, login = request('/api/auth/login', {'username': config['ADMIN_USERNAME'], 'password': config['ADMIN_PASSWORD']})
    assert status == 200
    token = login['access_token']
    def api(path):
        status, data = request(path, token=token)
        assert status == 200, path
        return data
    deadline = time.monotonic() + 60
    while True:
        fleet = api('/api/fleet')
        panel = api('/api/panels/PNL-001')
        if (fleet['summary']['total'] == 500 and fleet['summary']['offline'] == 0
            and fleet['summary']['normal'] == 500 and fleet['summary']['open_alarms'] == 0
            and all(not p['pending_current_run'] for p in fleet['panels'])
            and not panel['pending_current_run'] and panel['scenario'] == 'normal_operation'
            and panel['state'] == 'NORMAL' and not panel['current_run_alarms']):
            break
        assert time.monotonic() < deadline, 'Presentation did not become ready'
        time.sleep(1)
    bank = api('/api/scada/registers?panel_id=PNL-500')
    assert bank['connected'] and (bank['bank'], bank['port'], bank['unit_id']) == (3, 1504, 6)
    registers = {row['address']: row['value'] for row in bank['registers']}
    assert registers[7] == 1 and registers[8] > 0
    raw = compose('ps', '--format', 'json')
    services = json.loads(raw) if raw.lstrip().startswith('[') else [json.loads(line) for line in raw.splitlines() if line]
    assert len(services) == 6 and all(s['State'] == 'running' for s in services)
    assert all(s.get('Health') == 'healthy' for s in services if s['Service'] != 'simulator')
    rate = int(compose('exec', '-T', 'api', 'python', '-c', "import os; print(os.getenv('API_RATE_LIMIT','1200'))").strip())
    assert rate == 1200, 'Load-only rate limit still active'
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'passed': True,
              'dashboard': 'http://localhost:3000', 'fleet': fleet['summary'],
              'panel': {k: panel[k] for k in ['id', 'demo_run_id', 'scenario_revision', 'scenario', 'state', 'risk_score', 'health_score', 'pending_current_run']},
              'current_run_rows': len(panel['current_run_history']), 'current_run_alarms': len(panel['current_run_alarms']),
              'full_history_total': panel['full_history_total'], 'scada_pnl500': bank,
              'api_rate_limit': rate, 'scada_host_pnl500_port': int(config.get('SCADA_HOST_PORT_BASE', config.get('SCADA_PORT_BASE', '1502'))) + 2,
              'mqtt_host_port': int(config.get('MQTT_HOST_PORT', '1883')), 'services': [{'service': s['Service'], 'state': s['State'], 'health': s.get('Health')} for s in services],
              'mode': 'synthetic_demo; no external notification or physical field connection'}
    path = ROOT / 'docs/verification/v2-final-runtime.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'panels': 500, 'normal_run': panel['demo_run_id'], 'scada_pnl500': 'bank3/1504/unit6', 'rate_limit': rate}))


if __name__ == '__main__':
    main()
