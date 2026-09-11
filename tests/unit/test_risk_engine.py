from services.anomaly_engine.risk import evaluate, state_for, MAIN_INCOMER_REFERENCE_A
from services.simulator.scenarios import generate_frame, load_replay
from services.telemetry.schema import TelemetryFrame, normalize_quality

def evaluate_frame(frame, history=None):
    parsed = TelemetryFrame.model_validate(frame)
    values, quality = normalize_quality(parsed)
    return evaluate(values, quality, parsed.arc.model_dump(mode='json'), parsed.communication_ok, history)

def test_state_boundaries():
    assert [state_for(score) for score in (0, 19, 20, 44, 45, 79, 80, 100)] == [
        'NORMAL', 'NORMAL', 'ATTENTION', 'ATTENTION', 'WARNING', 'WARNING', 'CRITICAL', 'CRITICAL']

def test_normal_demo_starts_at_eight_and_ninety_six():
    result = evaluate_frame(generate_frame('PNL-001', 'combined_thermal_pd', 0, load_replay()))
    assert (result['risk_score'], result['health_score'], result['state']) == (8, 96, 'NORMAL')

def test_impossible_and_missing_values_never_become_zero_or_healthy():
    frame = generate_frame('PNL-001', 'normal_operation', 0, load_replay())
    frame['measurements']['humidity_pct'] = 130
    frame['measurements']['temperature_c'] = None
    parsed = TelemetryFrame.model_validate(frame)
    values, quality = normalize_quality(parsed)
    assert values['temperature_c'] is None and values['humidity_pct'] == 130
    assert quality['temperature_c'] == 'missing' and quality['humidity_pct'] == 'invalid'
    result = evaluate_frame(frame)
    assert result['state'] == 'ATTENTION'
    assert result['confidence'] < 100
    assert len(result['explanation']['data_quality']) == 2

def test_arc_event_overrides_missing_data_and_communication():
    result = evaluate({}, {'temperature_c': 'missing'}, {'event': True, 'communication_ok': False}, False)
    assert result['risk_score'] == 100 and result['state'] == 'CRITICAL'
    assert result['health_score'] == 0
    assert any(item['rule'] == 'arc_event' for item in result['explanation']['contributions'])

def test_arc_communication_failure_is_independent():
    frame = generate_frame('PNL-001', 'normal_operation', 0, load_replay())
    frame['arc']['communication_ok'] = False
    result = evaluate_frame(frame)
    assert result['risk_score'] >= 20
    assert any('Arc Guard iletişimi' in line for line in result['explanation']['data_quality'])

def test_temperature_load_correlation_and_statistics():
    frame = generate_frame('PNL-001', 'loose_connection_signature', 30, load_replay())
    history = [{'measurements': {'temperature_c': 37 + i * .2, 'current_l1': 318},
                'quality': {'temperature_c': 'good', 'current_l1': 'good'}} for i in range(12)]
    result = evaluate_frame(frame, history)
    rules = {item['rule'] for item in result['explanation']['contributions']}
    assert {'thermal_load_correlation', 'thermal_trend'} <= rules
    assert result['explanation']['trend']['temperature_ewma_c'] > 37
    assert 'varsayımdır, kesin tanı değildir' in next(p['detail'] for p in result['explanation']['contributions'] if p['rule'] == 'thermal_load_correlation')

def test_invalid_temperature_is_excluded_from_thermal_rule():
    result = evaluate({'temperature_c': 500}, {'temperature_c': 'invalid'}, {}, True)
    assert all(rule['rule'] != 'temperature' for rule in result['explanation']['contributions'])
    assert result['risk_score'] == 20

def test_load_uses_source_main_bus_rating_and_exact_demo_boundaries():
    assert MAIN_INCOMER_REFERENCE_A == 2312
    for ratio, expected_points in [(0.949, 0), (.95, 12), (1, 25), (1.2, 42)]:
        measurements = {name: ratio * MAIN_INCOMER_REFERENCE_A for name in ['current_l1', 'current_l2', 'current_l3']}
        result = evaluate(measurements, {name: 'good' for name in measurements}, {}, True)
        load_points = sum(item['points'] for item in result['explanation']['contributions'] if item['rule'] == 'load')
        assert load_points == expected_points
    assert 'ana girişten izlendiği varsayılır' in ' '.join(result['explanation']['assumptions'])
