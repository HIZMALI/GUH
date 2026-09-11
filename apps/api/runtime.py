"""Transactional ingestion, durable identity/order guarantees, alarm lifecycle."""
import hmac
import threading
import time
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from apps.api.database import (Panel, Telemetry, Alarm, Event, Notification, Audit, User,
                               utcnow, aware, as_dict, make_database)
from apps.api.security import derive_device_key, key_hash, hash_password
from services.anomaly_engine.risk import evaluate, STATE_ORDER
from services.telemetry.schema import TelemetryFrame, normalize_quality, CHANNELS
from services.notification.adapters import compose_notifications

class Runtime:
    def __init__(self, settings):
        self.settings = settings
        self.engine, self.sessions = make_database(settings.database_url)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.mqtt = None
        self.dummy_password_hash = hash_password('non-authenticating timing equalizer')
        self.metrics = {'accepted': 0, 'duplicates': 0, 'out_of_order': 0, 'invalid': 0,
                        'identity_rejected': 0, 'ingestion_latency_ms_total': 0.,
                        'ingestion_latency_ms_max': 0., 'db_write_ms_total': 0.,
                        'alarm_processing_ms_total': 0., 'mqtt_messages': 0, 'mqtt_rejected': 0,
                        'mqtt_connected': False, 'mqtt_connections': 0, 'mqtt_disconnects': 0}
        self.seed()

    def seed(self):
        with self.sessions.begin() as db:
            for role, password in self.settings.passwords.items():
                username = self.settings.admin_username if role == 'admin' else role
                if not db.get(User, username):
                    db.add(User(username=username, role=role, password_hash=hash_password(password)))
            for index in range(1, self.settings.panel_count + 1):
                panel_id, device_id = f'PNL-{index:03}', f'EDGE-{index:03}'
                if db.get(Panel, panel_id):
                    continue
                missing = {key: 'missing' for key in CHANNELS}
                snapshot = evaluate({}, missing, {'communication_ok': False}, False)
                snapshot.update(measurements={key: None for key in CHANNELS}, quality=missing,
                                provenance={key: 'generated_synthetic' for key in CHANNELS},
                                source='generated_synthetic', communication_ok=False, arc={'event': False, 'detectors': [],
                                'trip_relays': [], 'timestamp': None, 'system_state': 0, 'active_errors': [],
                                'communication_ok': False}, status='awaiting_telemetry', alarm_active=False)
                db.add(Panel(id=panel_id, name=f'Demo Pano {index:03}',
                             region=f'Simüle Bölge {(index - 1) // 50 + 1}',
                             substation=f'Demo TM {(index - 1) // 10 + 1:02}',
                             transformer=f'Demo TR {(index - 1) // 5 + 1:02}', device_id=device_id,
                             device_key_hash=key_hash(derive_device_key(self.settings.device_token, device_id)),
                             scenario='normal_operation', snapshot=snapshot))

    def audit(self, username, action, target='', details=None):
        with self.sessions.begin() as db:
            db.add(Audit(username=username, action=action, target=target, details=details or {}))

    def notify(self, db, alarm, kind):
        message = f'[SIMULATED] {alarm.panel_name}: {alarm.severity} — {alarm.title}. {alarm.message}'
        for item in compose_notifications(message):
            db.add(Notification(alarm_id=alarm.id, panel_id=alarm.panel_id, channel=item.channel,
                                recipient=item.recipient, status=item.status, message=item.message))
        db.add(Event(panel_id=alarm.panel_id, type=kind, message=message))

    def alarms(self, db, panel, result):
        began = time.perf_counter()
        explanations = result['explanation']
        desired = {}
        if result['risk_score'] >= 20:
            desired['condition'] = (result['state'], 'Koşul izleme riski', explanations['possible_cause'])
        if explanations['data_quality']:
            desired['availability'] = ('WARNING' if not result['communication_ok'] else 'ATTENTION',
                                       'Veri kullanılabilirliği', '; '.join(explanations['data_quality']))
        if result.get('arc', {}).get('event'):
            desired['arc'] = ('CRITICAL', 'ARC EVENT · Sentetik ABB TVOC-2',
                              'Detector: ' + ', '.join(result['arc'].get('detectors', [])) +
                              ' / Relay: ' + ', '.join(result['arc'].get('trip_relays', [])))
        existing = {a.kind: a for a in db.scalars(select(Alarm).where(Alarm.panel_id == panel.id,
                                                        Alarm.status != 'resolved')).all()}
        for kind, (severity, title, message) in desired.items():
            alarm = existing.get(kind)
            if alarm is None:
                alarm = Alarm(panel_id=panel.id, panel_name=panel.name, kind=kind, severity=severity,
                              title=title, message=message, status='active')
                db.add(alarm)
                db.flush()
                self.notify(db, alarm, 'alarm_created')
            else:
                escalated = STATE_ORDER[severity] > STATE_ORDER[alarm.severity]
                alarm.message = message
                # Peak severity is preserved until resolution, avoiding repeat escalation spam.
                if escalated:
                    alarm.severity, alarm.status, alarm.acknowledged_at = severity, 'active', None
                    self.notify(db, alarm, 'alarm_escalated')
        for kind, alarm in existing.items():
            if kind not in desired:
                alarm.status, alarm.resolved_at = 'resolved', utcnow()
                db.add(Event(panel_id=panel.id, type='alarm_resolved', message=f'{alarm.title}: condition cleared.'))
        result['alarm_active'] = bool(desired)
        self.metrics['alarm_processing_ms_total'] += (time.perf_counter() - began) * 1000

    def ingest(self, frame: TelemetryFrame, supplied_key: str | None = None):
        started = time.perf_counter()
        now = utcnow()
        if frame.timestamp > now + timedelta(minutes=5):
            self.metrics['invalid'] += 1
            raise HTTPException(422, 'Timestamp exceeds permitted five-minute future skew')
        with self.lock, self.sessions.begin() as db:
            panel = db.scalar(select(Panel).where(Panel.id == frame.panel_id).with_for_update())
            key = supplied_key or frame.device_key or ''
            if not panel or panel.device_id != frame.device_id or not hmac.compare_digest(panel.device_key_hash, key_hash(key)):
                self.metrics['identity_rejected'] += 1
                raise HTTPException(403, 'Device identity/key is not bound to this panel')
            duplicate = db.scalar(select(Telemetry.id).where(Telemetry.device_id == frame.device_id,
                                                           Telemetry.message_id == frame.message_id))
            if duplicate is not None:
                self.metrics['duplicates'] += 1
                return {'status': 'duplicate', 'accepted': False, 'message_id': frame.message_id}
            if panel.last_seen and frame.timestamp <= aware(panel.last_seen):
                self.metrics['out_of_order'] += 1
                raise HTTPException(409, 'Out-of-order or equal-time telemetry rejected; last accepted frame is preserved')
            rows = list(reversed(db.scalars(select(Telemetry).where(Telemetry.panel_id == panel.id)
                                           .order_by(Telemetry.timestamp.desc()).limit(12)).all()))
            history = [{'measurements': row.payload['measurements'], 'quality': row.payload['quality'],
                        'timestamp': aware(row.timestamp).isoformat()} for row in rows]
            values, quality = normalize_quality(frame)
            # Exact repeated analog channels over 12 prior accepted frames are suspicious, not definitive failures.
            for name in ('temperature_c', 'humidity_pct', 'current_l1'):
                previous = [h['measurements'].get(name) for h in history]
                if len(previous) == 12 and quality[name] == 'good' and all(v == values[name] for v in previous):
                    quality[name] = 'stuck'
            arc = frame.arc.model_dump(mode='json')
            fresh = (now - frame.timestamp).total_seconds() <= self.settings.stale_seconds
            communication_ok = frame.communication_ok and fresh
            result = evaluate(values, quality, arc, communication_ok, history)
            result.update(measurements=values, quality=quality,
                          provenance={name: frame.provenance.get(name, 'generated_synthetic') for name in CHANNELS},
                          source=frame.source, arc=arc, communication_ok=communication_ok,
                          status='live' if communication_ok else 'stale_or_offline',
                          simulation_step=frame.simulation_step, accelerated=frame.accelerated,
                          source_row=frame.source_row, replay_offset_seconds=frame.replay_offset_seconds)
            if panel.snapshot.get('state') != result['state']:
                db.add(Event(panel_id=panel.id, type='state_changed',
                             message=f'{panel.snapshot.get("state", "UNKNOWN")} → {result["state"]}; risk {result["risk_score"]}/100. Synthetic demo.'))
            self.alarms(db, panel, result)
            payload = frame.model_dump(mode='json', exclude={'device_key'})
            payload.update(measurements=values, quality=quality, provenance=result['provenance'])
            db.add(Telemetry(device_id=frame.device_id, panel_id=panel.id, message_id=frame.message_id,
                             timestamp=frame.timestamp, received_at=now, payload=payload, result=result))
            panel.last_seen, panel.received_at, panel.snapshot = frame.timestamp, now, result
            # Selected scenario stays API-owned; telemetry reports its producing scenario separately.
            panel.snapshot = {**result, 'telemetry_scenario': frame.scenario}
            db_started = time.perf_counter()
            db.flush()
        db_elapsed = (time.perf_counter() - db_started) * 1000
        elapsed = (time.perf_counter() - started) * 1000
        self.metrics['accepted'] += 1
        self.metrics['ingestion_latency_ms_total'] += elapsed
        self.metrics['db_write_ms_total'] += db_elapsed
        self.metrics['ingestion_latency_ms_max'] = max(self.metrics['ingestion_latency_ms_max'], elapsed)
        return {'status': 'accepted', 'accepted': True, 'message_id': frame.message_id,
                'risk_score': result['risk_score'], 'health_score': result['health_score'], 'state': result['state']}

    def mark_stale(self):
        now = utcnow()
        with self.lock, self.sessions.begin() as db:
            panels = db.scalars(select(Panel).where(Panel.received_at.is_not(None),
                       Panel.received_at < now - timedelta(seconds=self.settings.stale_seconds)).with_for_update()).all()
            for panel in panels:
                if not panel.snapshot.get('communication_ok'):
                    continue
                previous = panel.snapshot
                quality = previous.get('quality', {})
                result = evaluate(previous.get('measurements', {}), quality, previous.get('arc', {}), False)
                result = {**previous, **result, 'communication_ok': False, 'status': 'stale'}
                result['quality'] = {name: ('stale' if value == 'good' else value) for name, value in quality.items()}
                self.alarms(db, panel, result)
                panel.snapshot = result
                db.add(Event(panel_id=panel.id, type='communication_stale',
                             message=f'No accepted telemetry for {self.settings.stale_seconds}s; displayed measurements are last known, not live.'))

    def panel_dict(self, panel):
        return {'id': panel.id, 'name': panel.name, 'region': panel.region, 'substation': panel.substation,
                'transformer': panel.transformer, 'device_id': panel.device_id, 'scenario': panel.scenario,
                'last_seen': aware(panel.last_seen).isoformat() if panel.last_seen else None,
                **panel.snapshot}

    def tick(self):
        while not self.stop.wait(2):
            try:
                self.mark_stale()
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Staleness maintenance failed')
