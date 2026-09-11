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

log = logging.getLogger('gridsentinel.simulator')

def publication_interval(panel_count, requested_interval, max_fps):
    """Bound the scheduled average publication rate without speeding up smaller fleets."""
    if requested_interval <= 0 or max_fps <= 0 or panel_count < 0:
        raise ValueError('Interval and max_fps must be positive; panel_count cannot be negative')
    return max(requested_interval, panel_count / max_fps)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=['mqtt', 'http'], default=os.getenv('SIMULATOR_TRANSPORT', 'mqtt'))
    parser.add_argument('--interval', type=float, default=float(os.getenv('SIMULATOR_INTERVAL', '3')))
    parser.add_argument('--max-fps', type=float, default=float(os.getenv('SIMULATOR_MAX_FPS', '50')),
                        help='Maximum scheduled fleet-average publication rate; effective interval grows with fleet size')
    parser.add_argument('--cycles', type=int, default=0, help='0 runs until stopped')
    args = parser.parse_args()
    if args.interval <= 0 or args.max_fps <= 0:
        parser.error('--interval and --max-fps must both be positive')
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
    run_id, state, cycle = uuid.uuid4().hex[:12], {}, 0
    arc_event_times, last_effective_interval = {}, None
    with httpx.Client(base_url=api_url, headers={'Authorization': 'Bearer ' + token}, timeout=20) as api:
        while running and (not args.cycles or cycle < args.cycles):
            began = time.monotonic()
            effective_interval = args.interval
            published, skipped = 0, 0
            try:
                response = api.get('/api/demo/state')
                response.raise_for_status()
                panels = response.json()['panels']
                effective_interval = publication_interval(len(panels), args.interval, args.max_fps)
                if effective_interval != last_effective_interval:
                    log.info('Synthetic pacing panels=%s requested_interval_s=%.3f effective_interval_s=%.3f max_fps=%.1f scheduled_fps=%.2f',
                             len(panels), args.interval, effective_interval, args.max_fps, len(panels) / effective_interval)
                    last_effective_interval = effective_interval
                for panel in panels:
                    identity = (panel['id'], panel['revision'])
                    step = state.get(identity, 0)
                    # Communication loss ultimately produces real silence; staleness maintenance observes it.
                    if panel['scenario'] == 'communication_loss' and step >= 18:
                        skipped += 1
                        continue
                    if args.transport == 'mqtt' and not connected:
                        skipped += 1
                        continue
                    frame = generate_frame(panel['id'], panel['scenario'], step, samples,
                                           message_id=f'{run_id}-{panel["id"]}-{panel["revision"]}-{step}',
                                           scenario_started_at=panel['started_at'], interval_seconds=effective_interval)
                    if frame['arc']['event']:
                        # Use the first actual synthetic event publication time and retain it
                        # for this scenario revision, even when fleet pacing changes.
                        frame['arc']['timestamp'] = arc_event_times.setdefault(identity, frame['timestamp'])
                    frame['device_key'] = derive_device_key(device_token, frame['device_id'])
                    if broker:
                        import json
                        info = broker.publish(f'gridsentinel/telemetry/{frame["device_id"]}', json.dumps(frame), qos=1)
                        if info.rc != mqtt.MQTT_ERR_SUCCESS:
                            raise RuntimeError('MQTT publish was not accepted by client')
                    else:
                        response = api.post('/api/telemetry', json=frame)
                        response.raise_for_status()
                    state[identity] = step + 1
                    published += 1
                cycle += 1
                if cycle == 1 or cycle % 10 == 0:
                    log.info('Synthetic cycle=%s transport=%s panels=%s published=%s skipped=%s effective_interval_s=%.3f elapsed_ms=%.1f',
                             cycle, args.transport, len(panels), published, skipped, effective_interval, (time.monotonic() - began) * 1000)
            except (httpx.HTTPError, RuntimeError) as exc:
                log.warning('Synthetic cycle failed (%s); retrying', type(exc).__name__)
            time.sleep(max(.1, effective_interval - (time.monotonic() - began)))
    if broker:
        broker.disconnect()
        broker.loop_stop()

if __name__ == '__main__':
    main()
