"""Regenerate source-labelled scenario timelines using the same deterministic risk engine."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from services.simulator.scenarios import SCENARIOS, generate_frame, load_replay
from services.telemetry.schema import TelemetryFrame, normalize_quality
from services.anomaly_engine.risk import evaluate
from services.anomaly_engine.actions import action_policy
from services.anomaly_engine.timeline import early_warning_timeline

def main():
    destination = Path(__file__).resolve().parents[2] / 'data/scenarios'
    destination.mkdir(parents=True, exist_ok=True)
    samples = load_replay()
    for scenario in SCENARIOS:
        duration, history, timeline, transitions = scenario['duration_steps'], [], [], []
        start = datetime(2026, 9, 11, tzinfo=timezone.utc)
        stages = {0, 4, 8, duration // 3, 2 * duration // 3, duration - 1}
        for step in range(duration):
            frame = TelemetryFrame.model_validate(generate_frame('PNL-001', scenario['id'], step, samples,
                       timestamp=start + timedelta(seconds=step * 1.5), scenario_started_at=start, interval_seconds=1.5))
            values, quality = normalize_quality(frame)
            result = evaluate(values, quality, frame.arc.model_dump(mode='json'), frame.communication_ok, history[-12:])
            if not transitions or transitions[-1]['state'] != result['state']:
                transitions.append({'state': result['state'], 'step': step, 'timestamp': frame.timestamp.isoformat(),
                                    'risk_score': result['risk_score']})
            if step in stages:
                timeline.append({'step': step, 'elapsed_seconds_at_default_3s_interval': step * 3,
                                 'nominal_focused_elapsed_seconds': step * 1.5,
                                 'source_replay_offset_seconds': frame.replay_offset_seconds,
                                 'risk_score': result['risk_score'], 'health_score': result['health_score'],
                                 'state': result['state'], 'key_measurements': {name: values[name] for name in
                                   ['current_l1', 'temperature_c', 'humidity_pct', 'pd_baseline_ratio']},
                                 'quality_failures': result['explanation']['data_quality'],
                                 'expected_alarm': result['state'] if result['risk_score'] >= 20 else None,
                                 'rule_contributions': result['explanation']['contributions'],
                                 'arc_event': frame.arc.event, 'gateway_communication_ok': frame.communication_ok,
                                 'arc_guard_communication_ok': frame.arc.communication_ok,
                                 'expected_actions': action_policy({**result, 'arc': frame.arc.model_dump(mode='json'),
                                                                   'communication_ok': frame.communication_ok})})
            history.append({'measurements': values, 'quality': quality})
        document = {**scenario, 'mode': 'synthetic_demo', 'baseline': timeline[0], 'timeline': timeline,
                    'early_warning': early_warning_timeline(transitions, complete=True),
                    'focus_interval_seconds': 1.5,
                    'source': 'Workbook organizer-synthetic L1 replay; all other channels generated synthetic. Modified L1 scenarios explicitly generated.',
                    'timing': 'V2 focused synthetic panel uses 1.5-second deadlines. One focus slot reserves 1/1.5 fps from the total 50 fps limit; the other 499 panels use a 49.3333 fps background budget and about 10.1149-second per-panel intervals. Without focus, original max(interval,panel_count/max_fps) pacing remains. Timeline timestamps are deterministic example anchors, not actual field observations. Actual runtime UTC tracks publication; early warning is measured only in synthetic steps.',
                    'expected_outcome': 'Condition-monitoring alerts and locally simulated notification records. No device writes or protection actions.',
                    'communication_loss_note': 'Actual publisher stops this panel after step18; timeline thereafter describes expected offline state. Stale maintenance also detects silent publishers.' if scenario['id'] == 'communication_loss' else None,
                    'thresholds': 'Engineering demonstration assumptions only; never protection setpoints. PD is uncalibrated arbitrary units.'}
        (destination / f'{scenario["id"]}.json').write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exported {len(SCENARIOS)} synthetic scenario timelines to {destination}')

if __name__ == '__main__':
    main()
