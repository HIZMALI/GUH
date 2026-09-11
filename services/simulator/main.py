"""On-premise simulator. MQTT default; explicit HTTP transport is a labelled local fallback."""
import argparse
import logging
import os
import signal
import time
import uuid
import httpx
import paho.mqtt.client as mqtt
from apps.api.security import derive_device_key
from services.simulator.scenarios import generate_frame, load_replay
from services.simulator.scheduler import PanelScheduler, publication_interval, telemetry_message_id

log = logging.getLogger('gridsentinel.simulator')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=['mqtt', 'http'], default=os.getenv('SIMULATOR_TRANSPORT', 'mqtt'))
    parser.add_argument('--interval', type=float, default=float(os.getenv('SIMULATOR_INTERVAL', '3')))
    parser.add_argument('--max-fps', type=float, default=float(os.getenv('SIMULATOR_MAX_FPS', '50')),
                        help='Shared maximum publication rate, including the focused panel')
    parser.add_argument('--focus-interval', type=float, default=float(os.getenv('SIMULATOR_FOCUS_INTERVAL', '1.5')))
    parser.add_argument('--cycles', type=int, default=0, help='0 runs until stopped')
    args = parser.parse_args()
    try:
        scheduler = PanelScheduler(args.interval, args.max_fps, args.focus_interval)
    except ValueError as exc:
        parser.error(str(exc))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    token, device_token = os.environ['SERVICE_TOKEN'], os.environ['DEVICE_TOKEN']
    samples = load_replay()
    api_url = os.getenv('API_URL', 'http://api:8000').rstrip('/')
    connected, running = False, True
    broker = None
    if args.transport == 'mqtt':
        broker = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f'gridsentinel-simulator-{uuid.uuid4().hex[:8]}')
        broker.username_pw_set(os.environ['MQTT_USERNAME'], os.environ['MQTT_PASSWORD'])

        def on_connect(client, userdata, flags, reason_code, properties):
            nonlocal connected
            connected = not reason_code.is_failure
            log.info('MQTT connected=%s', connected)

        def on_disconnect(client, userdata, flags, reason_code, properties):
            nonlocal connected
            connected = False
            log.warning('MQTT disconnected; reconnecting without inventing successful publication')

        broker.on_connect, broker.on_disconnect = on_connect, on_disconnect
        broker.reconnect_delay_set(1, 30)
        broker.connect_async(os.getenv('MQTT_HOST', 'mqtt'), int(os.getenv('MQTT_PORT', '1883')), 30)
        broker.loop_start()

    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    next_poll, next_log, published, focused_published = 0., 0., 0, 0
    last_stats = None
    with httpx.Client(base_url=api_url, headers={'Authorization': 'Bearer ' + token}, timeout=20) as api:
        while running:
            now = time.monotonic()
            if now >= next_poll:
                try:
                    response = api.get('/api/demo/state')
                    response.raise_for_status()
                    scheduler.sync(response.json()['panels'], time.monotonic())
                    stats = scheduler.stats()
                    if stats != last_stats:
                        log.info('Synthetic scheduler configuration=%s', stats)
                        last_stats = stats
                except httpx.HTTPError as exc:
                    log.warning('Demo state unavailable (%s); retaining last known schedule', type(exc).__name__)
                next_poll = time.monotonic() + 1
            now = time.monotonic()
            entry = scheduler.due(now) if (not broker or connected) else None
            if entry:
                panel, step = entry.panel, entry.step
                if (panel['scenario'] == 'communication_loss' and step >= 18) or (args.cycles and entry.emitted >= args.cycles):
                    entry.disabled = True
                else:
                    frame = generate_frame(panel['id'], panel['scenario'], step, samples,
                                           message_id=telemetry_message_id(panel['demo_run_id'], step),
                                           scenario_started_at=panel['started_at'], interval_seconds=entry.interval)
                    if frame['arc']['event']:
                        entry.arc_event_timestamp = entry.arc_event_timestamp or frame['timestamp']
                        frame['arc']['timestamp'] = entry.arc_event_timestamp
                    frame.update(scenario_revision=panel['revision'], demo_run_id=panel['demo_run_id'],
                                 focused_demo=entry.focused, demo_interval_seconds=entry.interval)
                    frame['device_key'] = derive_device_key(device_token, frame['device_id'])
                    try:
                        if broker:
                            import json
                            info = broker.publish(f'gridsentinel/telemetry/{frame["device_id"]}', json.dumps(frame), qos=1)
                            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                                raise RuntimeError('MQTT publish was not accepted by client')
                        else:
                            response = api.post('/api/telemetry', json=frame)
                            response.raise_for_status()
                        scheduler.sent(entry, time.monotonic())
                        published += 1
                        focused_published += int(entry.focused)
                    except (httpx.HTTPError, RuntimeError) as exc:
                        scheduler.retry(entry, time.monotonic())
                        log.warning('Synthetic publication failed panel=%s (%s); retrying', panel['id'], type(exc).__name__)
            if now >= next_log:
                log.info('Synthetic progress transport=%s published=%s focused_published=%s scheduler=%s',
                         args.transport, published, focused_published, scheduler.stats())
                next_log = now + 10
            if args.cycles and scheduler.entries and all(entry.disabled for entry in scheduler.entries.values()):
                break
            now = time.monotonic()
            deadline = min(next_poll, scheduler.deadline(now)) if (not broker or connected) else min(next_poll, now + .5)
            time.sleep(max(.001, min(1, deadline - now)))
    if broker:
        broker.disconnect()
        broker.loop_stop()

if __name__ == '__main__':
    main()
