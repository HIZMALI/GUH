from datetime import datetime, timedelta, timezone
import pytest
from services.simulator.scheduler import PanelScheduler, telemetry_message_id
from services.simulator.scenarios import generate_frame, load_replay
from services.telemetry.schema import TelemetryFrame, normalize_quality
from services.anomaly_engine.risk import evaluate
from services.anomaly_engine.actions import action_policy, policy_catalog, policy_notification_channels
from services.anomaly_engine.timeline import early_warning_timeline

def fleet(scenario='combined_thermal_pd', revision=2):
    return [{'id': f'PNL-{i:03}', 'device_id': f'EDGE-{i:03}', 'revision': revision if i == 1 else 1,
             'demo_run_id': f'PNL-{i:03}-r{revision if i == 1 else 1}', 'scenario': scenario if i == 1 else 'normal_operation',
             'focused_demo': i == 1, 'last_step': None} for i in range(1, 501)]

@pytest.mark.parametrize('scenario,limit', [('combined_thermal_pd', 75), ('arc_event', 20)])
def test_500_panel_focus_timing_and_shared_fps_budget(scenario, limit):
    scheduler = PanelScheduler()
    scheduler.sync(fleet(scenario), 0)
    history, transitions, timestamps, identifiers, per_panel = [], [], [], set(), {}
    samples, now, critical_at = load_replay(), 0., None
    start = datetime(2026, 9, 11, tzinfo=timezone.utc)
    while now <= limit:
        entry = scheduler.due(now)
        if entry:
            identity = telemetry_message_id(entry.panel['demo_run_id'], entry.step)
            assert identity not in identifiers
            identifiers.add(identity)
            timestamps.append(now)
            per_panel.setdefault(entry.panel['id'], []).append(now)
            if entry.focused:
                frame = TelemetryFrame.model_validate(generate_frame(entry.panel['id'], scenario, entry.step, samples,
                          timestamp=start + timedelta(seconds=now)))
                values, quality = normalize_quality(frame)
                result = evaluate(values, quality, frame.arc.model_dump(mode='json'), True, history[-12:])
                if not transitions or transitions[-1] != result['state']:
                    transitions.append(result['state'])
                history.append({'measurements': values, 'quality': quality})
                if result['state'] == 'CRITICAL' and critical_at is None:
                    critical_at = now
            scheduler.sent(entry, now)
        now = max(now + .0000001, scheduler.deadline(now))
    assert critical_at is not None and critical_at <= limit
    assert len(timestamps) <= limit * 50 + 1
    assert all(b - a >= .02 - 1e-8 for a, b in zip(timestamps, timestamps[1:]))
    assert scheduler.background_budget == pytest.approx(50 - 1 / 1.5)
    assert scheduler.background_interval == pytest.approx(499 / (50 - 1 / 1.5))
    assert len(per_panel) == 500
    for panel_id, stamps in per_panel.items():
        if panel_id != 'PNL-001':
            assert all(b - a >= scheduler.background_interval - 1e-8 for a, b in zip(stamps, stamps[1:]))
    if scenario == 'combined_thermal_pd':
        assert transitions[:4] == ['NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL']
    else:
        assert 12 <= critical_at <= 20

def test_scheduler_restart_revision_and_only_one_focus():
    panels = fleet()
    panels[0]['last_step'] = 25
    panels[1]['focused_demo'] = True
    scheduler = PanelScheduler()
    scheduler.sync(panels, 100)
    assert sum(entry.focused for entry in scheduler.entries.values()) == 1
    assert scheduler.entries['PNL-001'].step == 26
    panels[0] = {**panels[0], 'revision': 3, 'demo_run_id': 'PNL-001-r3', 'last_step': None}
    scheduler.sync(panels, 110)
    assert scheduler.entries['PNL-001'].step == 0
    assert scheduler.due(110).panel['demo_run_id'] == 'PNL-001-r3'
    with pytest.raises(ValueError):
        PanelScheduler(max_fps=.5, focus_interval=1.5)

def test_policy_channels_and_protection_boundary_are_central():
    for row in policy_catalog()['items']:
        assert all(action['safety_boundary'] for action in row['actions'])
        assert not any(action['type'] in {'trip', 'reset', 'breaker_command', 'modbus_write'} for action in row['actions'])
        notifications = [action for action in row['actions'] if action['type'] == 'notification']
        assert all(action['channel'] in {'sms_mock', 'whatsapp_mock'} for action in notifications)
        if row['trigger'] == 'NORMAL':
            assert not notifications
        else:
            assert len(notifications) == 2

def test_early_warning_never_invents_real_lead_time():
    transitions = [{'state': state, 'step': step, 'timestamp': f'2026-09-11T00:00:{step:02}+00:00', 'risk_score': score}
                   for state, step, score in [('NORMAL', 0, 8), ('ATTENTION', 12, 25), ('WARNING', 21, 55), ('CRITICAL', 34, 88)]]
    result = early_warning_timeline(transitions)
    assert result['lead_steps'] == 13 and result['status'] == 'demonstrated'
    assert result['unit'] == 'synthetic_demo_steps'
    assert 'sentetik demo adımı' in result['message']
    assert early_warning_timeline(transitions[:3])['status'] == 'before_critical'
    assert early_warning_timeline(transitions[:3], complete=True)['status'] == 'no_critical'
    assert early_warning_timeline([transitions[-1]])['lead_steps'] is None
    assert early_warning_timeline([transitions[-1]])['status'] == 'critical_without_prior_warning'
