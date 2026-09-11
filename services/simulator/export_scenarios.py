"""Regenerate source-labelled scenario timelines using the same deterministic risk engine."""
import json
from pathlib import Path
from services.simulator.scenarios import SCENARIOS, generate_frame, load_replay
from services.telemetry.schema import TelemetryFrame, normalize_quality
from services.anomaly_engine.risk import evaluate

def main():
    destination = Path(__file__).resolve().parents[2] / 'data/scenarios'
    destination.mkdir(parents=True, exist_ok=True)
    samples = load_replay()
    for scenario in SCENARIOS:
        duration, history, timeline = scenario['duration_steps'], [], []
        stages = {0, 4, 8, duration // 3, 2 * duration // 3, duration - 1}
        for step in range(duration):
            frame = TelemetryFrame.model_validate(generate_frame('PNL-001', scenario['id'], step, samples))
            values, quality = normalize_quality(frame)
            result = evaluate(values, quality, frame.arc.model_dump(mode='json'), frame.communication_ok, history[-12:])
            if step in stages:
                timeline.append({'step': step, 'elapsed_seconds_at_default_3s_interval': step * 3,
                                 'source_replay_offset_seconds': frame.replay_offset_seconds,
                                 'risk_score': result['risk_score'], 'health_score': result['health_score'],
                                 'state': result['state'], 'key_measurements': {name: values[name] for name in
                                   ['current_l1', 'temperature_c', 'humidity_pct', 'pd_baseline_ratio']},
                                 'quality_failures': result['explanation']['data_quality'],
                                 'expected_alarm': result['state'] if result['risk_score'] >= 20 else None,
                                 'rule_contributions': result['explanation']['contributions'],
                                 'arc_event': frame.arc.event, 'gateway_communication_ok': frame.communication_ok,
                                 'arc_guard_communication_ok': frame.arc.communication_ok})
            history.append({'measurements': values, 'quality': quality})
        document = {**scenario, 'mode': 'synthetic_demo', 'baseline': timeline[0], 'timeline': timeline,
                    'source': 'Workbook organizer-synthetic L1 replay; all other channels generated synthetic. Modified L1 scenarios explicitly generated.',
                    'timing': 'At the default 100-panel fleet, one 900-second workbook offset is replayed per 3-second publication interval (300×). Fleet-average pacing uses max(requested interval, panel count / SIMULATOR_MAX_FPS), default 50 fps: 250 panels use 5 seconds, 500 use 10 seconds. Actual UTC timestamps track publication. Scenario rules use accepted-frame rolling windows.',
                    'expected_outcome': 'Condition-monitoring alerts and locally simulated notification records. No device writes or protection actions.',
                    'communication_loss_note': 'Actual publisher stops this panel after step18; timeline thereafter describes expected offline state. Stale maintenance also detects silent publishers.' if scenario['id'] == 'communication_loss' else None,
                    'thresholds': 'Engineering demonstration assumptions only; never protection setpoints. PD is uncalibrated arbitrary units.'}
        (destination / f'{scenario["id"]}.json').write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exported {len(SCENARIOS)} synthetic scenario timelines to {destination}')

if __name__ == '__main__':
    main()
