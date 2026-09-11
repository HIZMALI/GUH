"""Ten reproducible synthetic scenarios. Workbook L1 is preserved unless a scenario changes it."""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from services.telemetry.schema import CHANNELS
from services.anomaly_engine.risk import MAIN_INCOMER_REFERENCE_A

SCENARIOS = [
    {'id': 'normal_operation', 'name': 'Normal çalışma', 'description': 'Organizer L1 replay with generated companion channels.', 'duration_steps': 60, 'expected_state': 'NORMAL'},
    {'id': 'gradual_overload', 'name': 'Kademeli yük artışı', 'description': 'Generated main-incomer current climbs to 1.3× the source panel main-bus reference of 2312 A; monitoring position is an assumption.', 'duration_steps': 48, 'expected_state': 'WARNING'},
    {'id': 'thermal_hotspot', 'name': 'Termal sıcak nokta', 'description': 'Generated connection temperature rises to 88 °C.', 'duration_steps': 48, 'expected_state': 'WARNING'},
    {'id': 'high_humidity', 'name': 'Yüksek nem', 'description': 'Generated humidity rises to 98%; demo thresholds are assumptions.', 'duration_steps': 48, 'expected_state': 'WARNING'},
    {'id': 'loose_connection_signature', 'name': 'Gevşek bağlantı belirtisi', 'description': 'Temperature rises while generated load remains nearly stable; hypothesis only.', 'duration_steps': 48, 'expected_state': 'WARNING'},
    {'id': 'pd_degradation', 'name': 'PD aktivitesi artışı', 'description': 'Generated uncalibrated PD features increase to 6× baseline.', 'duration_steps': 48, 'expected_state': 'WARNING'},
    {'id': 'combined_thermal_pd', 'name': 'Termal + PD korelasyonu', 'description': 'Normal → attention → warning → severe late-stage critical, all generated.', 'duration_steps': 60, 'expected_state': 'CRITICAL'},
    {'id': 'arc_event', 'name': 'Ark olayı', 'description': 'Separate synthetic ABB TVOC-2 detector/relay event; no protection command.', 'duration_steps': 30, 'expected_state': 'CRITICAL'},
    {'id': 'sensor_failure', 'name': 'Sensör arızası', 'description': 'Missing thermal, impossible humidity and explicitly stuck phase channel.', 'duration_steps': 30, 'expected_state': 'ATTENTION'},
    {'id': 'communication_loss', 'name': 'İletişim kaybı', 'description': 'Arc Guard link fails independently, followed by gateway offline reporting and publish silence.', 'duration_steps': 30, 'expected_state': 'WARNING'},
]
SCENARIO_IDS = {item['id'] for item in SCENARIOS}

def load_replay(path=None):
    target = Path(path) if path else Path(__file__).resolve().parents[2] / 'data/synthetic/current_replay.json'
    document = json.loads(target.read_text(encoding='utf-8-sig'))
    samples = document['samples'] if isinstance(document, dict) else document
    if len(samples) != 152:
        raise ValueError('Source replay must contain all 152 workbook L1 samples')
    return samples

def generate_frame(panel_id: str, scenario: str, step: int, samples: list[dict],
                   timestamp=None, message_id=None, scenario_started_at=None, interval_seconds=3):
    if scenario not in SCENARIO_IDS:
        raise ValueError(f'Unknown scenario {scenario}')
    index = int(panel_id.split('-')[1])
    sample = samples[(step + index - 1) % len(samples)]
    wave = math.sin(step * .31 + index * .7)
    original = float(sample['current_l1'])
    current = original
    # Organizer L1 replay is at most 540 A; the load rule uses the 2312 A
    # source main-bus rating under an explicit main-incomer monitoring assumption.
    temperature, humidity, pd_ratio = 37 + wave * .6, 49 + wave, 1 + wave * .04
    progress = min(1, max(0, (step - 4) / 40))
    changed_current = False
    if scenario == 'gradual_overload':
        current, changed_current = 318 + (1.3 * MAIN_INCOMER_REFERENCE_A - 318) * progress, True
        temperature += progress * 18
    elif scenario in {'thermal_hotspot', 'loose_connection_signature', 'combined_thermal_pd'}:
        current, changed_current = 318 * (1 + .06 * progress) + wave * .4, True
        temperature += progress * (51 if scenario != 'combined_thermal_pd' else 43)
    if scenario == 'high_humidity':
        humidity = 49 + 49 * progress
    if scenario in {'pd_degradation', 'combined_thermal_pd'}:
        pd_ratio = 1 + 5 * max(0, (progress - (.2 if scenario == 'combined_thermal_pd' else 0)))
    values = {
        'current_l1': round(current, 3), 'current_l2': round(current * (1 + .017 * wave), 3),
        'current_l3': round(current * (1 - .013 * wave), 3), 'current_neutral': round(abs(current * .025 * wave), 3),
        'voltage_l1': round(230 + wave, 2), 'voltage_l2': round(231 - wave * .8, 2), 'voltage_l3': round(230 + wave * .4, 2),
        'active_power_kw': round(current * .230 * 3 * .94, 2), 'reactive_power_kvar': round(current * .230 * 3 * .34, 2),
        'apparent_power_kva': round(current * .230 * 3, 2), 'power_factor': .94,
        'frequency_hz': round(50 + wave * .03, 3), 'thd_current': round(5 + wave * .5, 2),
        'thd_voltage': round(2 + wave * .2, 2), 'temperature_c': round(temperature, 2),
        'ambient_temperature_c': round(26 + wave * .2, 2), 'humidity_pct': round(humidity, 2),
        'pd_pulse_count': round(8 * pd_ratio), 'pd_peak': round(1.7 * pd_ratio, 3),
        'pd_rms': round(.5 * pd_ratio, 3), 'pd_activity_rate': round(2 * pd_ratio, 3),
        'pd_baseline_ratio': round(pd_ratio, 3), 'battery_pct': round(94 - (step % 100) * .02, 2),
    }
    quality = {name: 'good' for name in CHANNELS}
    arc = {'event': scenario == 'arc_event' and step >= 8, 'detectors': [], 'trip_relays': [],
           'timestamp': None, 'system_state': 0, 'active_errors': [], 'communication_ok': True}
    ts = timestamp or datetime.now(timezone.utc)
    if arc['event']:
        start = datetime.fromisoformat(scenario_started_at) if isinstance(scenario_started_at, str) else scenario_started_at
        event_time = start + timedelta(seconds=8 * interval_seconds) if start else ts - timedelta(seconds=max(0, step - 8) * interval_seconds)
        arc.update(detectors=['X1:3', 'X2:6'], trip_relays=['K4'], timestamp=event_time.isoformat(), system_state=1)
    if scenario == 'sensor_failure' and step >= 8:
        values.update(temperature_c=None, humidity_pct=137, current_l3=318)
        quality.update(temperature_c='missing', humidity_pct='invalid', current_l3='stuck')
    if scenario == 'communication_loss' and step >= 6:
        arc['communication_ok'] = False
    provenance = {name: 'generated_synthetic' for name in CHANNELS}
    if not changed_current:
        provenance['current_l1'] = 'organizer_synthetic_replay'
    return {'message_id': message_id or f'{panel_id}-{int(ts.timestamp()*1000000)}-{step}',
            'device_id': f'EDGE-{index:03}', 'panel_id': panel_id, 'timestamp': ts.isoformat(),
            'source': 'generated_synthetic' if changed_current else 'organizer_synthetic_replay',
            'scenario': scenario, 'measurements': values, 'quality': quality, 'provenance': provenance,
            'arc': arc, 'communication_ok': not (scenario == 'communication_loss' and step >= 12),
            'source_row': int(sample['source_row']), 'replay_offset_seconds': int(sample['offset_seconds']),
            'simulation_step': step, 'accelerated': True}
