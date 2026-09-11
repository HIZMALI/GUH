"""MQTT QoS1 ingestion with bounded payload and durable API-level deduplication."""
import json
import logging
import os
import queue
import threading
from pydantic import ValidationError
from fastapi import HTTPException
import paho.mqtt.client as mqtt
from services.telemetry.schema import TelemetryFrame

log = logging.getLogger(__name__)

def start_subscriber(runtime):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='gridsentinel-ingestion', clean_session=False)
    client.manual_ack_set(True)
    pending = queue.Queue(maxsize=8192)
    username, password = os.getenv('MQTT_USERNAME'), os.getenv('MQTT_PASSWORD')
    if not username or not password:
        raise RuntimeError('MQTT username and password must be bootstrapped')
    client.username_pw_set(username, password)

    def on_connect(client, userdata, flags, reason_code, properties):
        runtime.metrics['mqtt_connected'] = not reason_code.is_failure
        if not reason_code.is_failure:
            runtime.metrics['mqtt_connections'] += 1
            client.subscribe('gridsentinel/telemetry/+', qos=1)
        else:
            log.error('MQTT authentication/connection failed: %s', reason_code)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        runtime.metrics['mqtt_connected'] = False
        runtime.metrics['mqtt_disconnects'] += 1

    def on_message(client, userdata, message):
        runtime.metrics['mqtt_messages'] += 1
        try:
            if len(message.payload) > 32768:
                raise ValueError('payload too large')
            frame = TelemetryFrame.model_validate_json(message.payload)
            if message.topic != f'gridsentinel/telemetry/{frame.device_id}':
                raise ValueError('topic/device identity mismatch')
            pending.put_nowait((frame, message.mid, message.qos))
        except (ValidationError, ValueError, HTTPException) as exc:
            runtime.metrics['mqtt_rejected'] += 1
            log.warning('MQTT frame rejected (%s)', type(exc).__name__)
            client.ack(message.mid, message.qos)
        except queue.Full:
            # Broker retains the unacknowledged QoS1 frame in the persistent session.
            runtime.metrics['mqtt_rejected'] += 1
            log.error('MQTT processing queue full; frame not acknowledged, broker redelivery requires reconnect')
        except Exception:
            runtime.metrics['mqtt_rejected'] += 1
            log.exception('MQTT frame handling failed; frame not acknowledged')

    def persist():
        while not runtime.stop.is_set():
            try:
                frame, mid, qos = pending.get(timeout=.5)
            except queue.Empty:
                continue
            retries = 0
            while not runtime.stop.is_set():
                try:
                    runtime.ingest(frame)
                    client.ack(mid, qos)
                    break
                except HTTPException as exc:
                    # Identity/order/schema failures are permanent and must not poison the queue.
                    runtime.metrics['mqtt_rejected'] += 1
                    log.warning('MQTT ingestion rejected status=%s', exc.status_code)
                    client.ack(mid, qos)
                    break
                except Exception as exc:
                    retries += 1
                    if retries == 1 or retries % 10 == 0:
                        log.error('MQTT persistence unavailable (%s); retaining unacknowledged frame, retry=%s', type(exc).__name__, retries)
                    runtime.stop.wait(min(5, retries))
            pending.task_done()

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(os.getenv('MQTT_HOST', 'mqtt'), int(os.getenv('MQTT_PORT', '1883')), keepalive=30)
    client.loop_start()
    threading.Thread(target=persist, name='mqtt-persistence', daemon=True).start()
    return client
