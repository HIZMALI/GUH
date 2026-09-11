import pytest
from services.simulator.scenarios import SCENARIOS, generate_frame, load_replay
from services.telemetry.schema import TelemetryFrame, normalize_quality
from services.anomaly_engine.risk import evaluate

@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda item: item['id'])
def test_all_ten_scenarios_reach_declared_state(scenario):
    samples, history, states = load_replay(), [], []
    for step in range(scenario['duration_steps']):
        frame = TelemetryFrame.model_validate(generate_frame('PNL-001', scenario['id'], step, samples))
        values, quality = normalize_quality(frame)
        result = evaluate(values, quality, frame.arc.model_dump(mode='json'), frame.communication_ok, history[-12:])
        states.append(result['state'])
        history.append({'measurements': values, 'quality': quality})
    assert scenario['expected_state'] in states
    if scenario['id'] == 'normal_operation':
        assert set(states) == {'NORMAL'}
    if scenario['id'] == 'combined_thermal_pd':
        assert {'NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL'} <= set(states)

def test_workbook_replay_values_and_relative_timing_are_preserved():
    samples = load_replay()
    assert len(samples) == 152
    for step, sample in enumerate(samples):
        frame = generate_frame('PNL-001', 'normal_operation', step, samples)
        assert frame['measurements']['current_l1'] == sample['current_l1']
        assert frame['source_row'] == sample['source_row']
        assert frame['replay_offset_seconds'] == sample['offset_seconds']
        assert frame['provenance']['current_l1'] == 'organizer_synthetic_replay'
        assert frame['provenance']['pd_peak'] == 'generated_synthetic'
        parsed = TelemetryFrame.model_validate(frame)
        values, quality = normalize_quality(parsed)
        assert evaluate(values, quality, frame['arc'], True)['state'] == 'NORMAL'

def test_sustained_arc_event_timestamp_is_stable_from_scenario_start():
    start = '2026-09-11T00:00:00+00:00'
    samples = load_replay()
    first = generate_frame('PNL-001', 'arc_event', 8, samples, scenario_started_at=start)
    later = generate_frame('PNL-001', 'arc_event', 18, samples, scenario_started_at=start)
    assert first['arc']['timestamp'] == later['arc']['timestamp'] == '2026-09-11T00:00:24+00:00'

def test_scenario_modified_l1_is_generated_not_falsely_attributed_to_workbook():
    frame = generate_frame('PNL-001', 'combined_thermal_pd', 40, load_replay())
    assert frame['provenance']['current_l1'] == 'generated_synthetic'
    assert frame['source'] == 'generated_synthetic'

def test_overload_exceeds_source_main_bus_rating():
    frame = generate_frame('PNL-001', 'gradual_overload', 47, load_replay())
    assert frame['measurements']['current_l1'] == pytest.approx(1.3 * 2312)
    assert frame['measurements']['current_l1'] > 1.2 * 2312
    assert frame['provenance']['current_l1'] == 'generated_synthetic'

def test_simulator_paces_100_250_and_500_panel_fleets():
    from services.simulator.main import publication_interval
    assert publication_interval(100, 3, 50) == 3
    assert publication_interval(250, 3, 50) == 5
    assert publication_interval(500, 3, 50) == 10
    assert publication_interval(500, 30, 50) == 30
    assert publication_interval(500, 3, 25) == 20
    with pytest.raises(ValueError):
        publication_interval(500, 3, 0)
