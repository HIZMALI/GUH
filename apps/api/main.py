from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import timedelta
import hmac
import logging
import os
import threading
import time
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from apps.api.database import Panel, Telemetry, Alarm, Event, Notification, Audit, User, utcnow, aware, as_dict
from apps.api.runtime import Runtime
from apps.api.security import decode_token, issue_token, verify_password, hash_password
from apps.api.settings import Settings
from services.telemetry.schema import TelemetryFrame
from services.simulator.scenarios import SCENARIOS, SCENARIO_IDS
from apps.api.history import history_page, panel_history
from services.anomaly_engine.actions import policy_catalog
from services.simulator.scheduler import publication_interval

log = logging.getLogger(__name__)

class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

class ScenarioSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scenario: str = Field(max_length=64)
    panel_id: str = Field(default='PNL-001', pattern=r'^PNL-[0-9]{3,6}$')
    focused: bool = Field(default=True, validation_alias=AliasChoices('focus', 'focused'))

class FleetSize(BaseModel):
    model_config = ConfigDict(extra='forbid')
    count: int = Field(ge=1, le=10000)

def create_app(settings=None):
    @asynccontextmanager
    async def lifespan(app):
        actual = settings or Settings.from_env()
        runtime = Runtime(actual)
        app.state.runtime = runtime
        if actual.mqtt_enabled:
            from services.telemetry.mqtt import start_subscriber
            runtime.mqtt = start_subscriber(runtime)
        worker = threading.Thread(target=runtime.tick, name='stale-quality', daemon=True)
        worker.start()
        yield
        runtime.stop.set()
        worker.join(timeout=3)
        if runtime.mqtt:
            runtime.mqtt.disconnect()
            runtime.mqtt.loop_stop()
        runtime.engine.dispose()

    app = FastAPI(title='GridSentinel', version='1.0.0', lifespan=lifespan,
                  description='On-premise synthetic condition monitoring. No protection commands.',
                  docs_url=None, redoc_url=None, openapi_url=None)
    rates, rate_lock = defaultdict(deque), threading.Lock()

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(request, exc):
        log.error('Database operation unavailable: %s', type(exc).__name__)
        return JSONResponse({'detail': 'Database temporarily unavailable; no successful persistence is claimed',
                             'status': 'degraded', 'database': 'unavailable'}, status_code=503,
                            headers={'Retry-After': '5'})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        if request.url.path == '/api/telemetry':
            request.app.state.runtime.metrics['invalid'] += 1
        # Do not reflect credentials or entire telemetry payloads in error bodies.
        return JSONResponse({'detail': [{'loc': list(error['loc']), 'msg': error['msg'], 'type': error['type']}
                                        for error in exc.errors()]}, status_code=422)

    @app.middleware('http')
    async def limits(request, call_next):
        try:
            declared_length = int(request.headers.get('content-length', '0') or 0)
        except ValueError:
            return JSONResponse({'detail': 'Invalid Content-Length'}, 400)
        if declared_length > 32768:
            return JSONResponse({'detail': 'Request exceeds 32768-byte limit'}, 413)
        if request.method in {'POST', 'PUT', 'PATCH'}:
            chunks, length = [], 0
            async for chunk in request.stream():
                length += len(chunk)
                if length > 32768:
                    return JSONResponse({'detail': 'Request exceeds 32768-byte limit'}, 413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        # Do not trust X-Forwarded-For from callers; key local socket identity.
        if request.url.path != '/health':
            identity = request.client.host if request.client else 'unknown'
            login = request.url.path == '/api/auth/login'
            key = (identity, 'login' if login else 'api')
            limit = 20 if login else app.state.runtime.settings.rate_limit
            now = time.monotonic()
            with rate_lock:
                bucket = rates[key]
                while bucket and bucket[0] <= now - 60:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return JSONResponse({'detail': 'Rate limit exceeded'}, 429, headers={'Retry-After': '60'})
                bucket.append(now)
        began = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - began) * 1000
        metrics = app.state.runtime.metrics
        metrics['http_requests'] += 1
        metrics['http_request_ms_total'] += elapsed_ms
        metrics['http_request_ms_max'] = max(metrics['http_request_ms_max'], elapsed_ms)
        if elapsed_ms >= 1000:
            log.warning('Slow request method=%s path=%s status=%s elapsed_ms=%.1f',
                        request.method, request.scope.get('route').path if request.scope.get('route') else request.url.path,
                        response.status_code, elapsed_ms)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def runtime(request: Request):
        return request.app.state.runtime

    def principal(request: Request, rt=Depends(runtime)):
        auth = request.headers.get('authorization', '')
        if not auth.startswith('Bearer '):
            raise HTTPException(401, 'Bearer authentication required')
        token = auth[7:]
        if hmac.compare_digest(token, rt.settings.service_token):
            return {'sub': 'service', 'role': 'service'}
        identity = decode_token(token, rt.settings.auth_secret)
        with rt.sessions() as db:
            user = db.get(User, identity['sub'])
            if not user or user.role != identity['role']:
                raise HTTPException(401, 'Unknown or changed identity')
        return identity

    def roles(*allowed):
        def check(identity=Depends(principal)):
            if identity['role'] not in allowed:
                raise HTTPException(403, 'Role not permitted')
            return identity
        return check

    @app.get('/health')
    def health(rt=Depends(runtime)):
        with rt.sessions() as db:
            db.execute(text('SELECT 1'))
        return {'status': 'ok', 'database': 'postgresql' if rt.engine.dialect.name == 'postgresql' else 'sqlite_local_fallback',
                'mqtt_connected': rt.metrics['mqtt_connected'], 'mode': 'synthetic_demo', 'timestamp': utcnow().isoformat()}

    @app.post('/api/auth/login')
    def login(body: Login, rt=Depends(runtime)):
        with rt.sessions() as db:
            user = db.get(User, body.username)
            # Fixed PBKDF2 work for unknown accounts prevents easy username timing enumeration.
            encoded = user.password_hash if user else rt.dummy_password_hash
            valid = verify_password(body.password, encoded)
        rt.audit(body.username, 'login_success' if user and valid else 'login_failed')
        if not user or not valid:
            raise HTTPException(401, 'Invalid username or password')
        return {'access_token': issue_token(user.username, user.role, rt.settings.auth_secret, rt.settings.session_seconds),
                'token_type': 'bearer', 'role': user.role, 'username': user.username}

    @app.get('/api/auth/me')
    def me(identity=Depends(principal)):
        return {'username': identity['sub'], 'role': identity['role']}

    @app.post('/api/telemetry')
    def telemetry(body: TelemetryFrame, request: Request, identity=Depends(roles('service', 'admin')), rt=Depends(runtime)):
        try:
            return rt.ingest(body, request.headers.get('x-device-key'))
        except HTTPException as exc:
            if exc.status_code == 403:
                rt.audit(identity['sub'], 'device_identity_rejected', body.device_id)
            raise

    @app.get('/api/fleet')
    def fleet(identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            panels = [rt.panel_dict(panel) for panel in db.scalars(select(Panel).order_by(Panel.id))]
            open_alarms = db.scalar(select(func.count()).select_from(Alarm).where(Alarm.status != 'resolved'))
        panels.sort(key=lambda panel: (-panel['risk_score'], panel['id']))
        count = len(panels)
        summary = {'total': count, 'fleet_health': round(sum(p['health_score'] for p in panels) / count, 1) if count else 0,
                   'open_alarms': open_alarms, 'offline': sum(not p['communication_ok'] for p in panels)}
        summary.update({state.lower(): sum(p['state'] == state for p in panels) for state in ['NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL']})
        return {'panels': panels, 'summary': summary, 'timestamp': utcnow().isoformat(), 'mode': 'synthetic_demo'}

    @app.get('/api/panels/{panel_id}')
    def panel_detail(panel_id: str, identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            panel = db.get(Panel, panel_id)
            if not panel:
                raise HTTPException(404, 'Panel not found')
            result = rt.panel_dict(panel)
            result.update(panel_history(db, panel, rt.run_id(panel)))
            return result

    @app.get('/api/panels/{panel_id}/history')
    def paginated_history(panel_id: str, scope: Literal['all', 'current'] = 'all',
                          before_id: int | None = Query(default=None, ge=1), limit: int = Query(default=120, ge=1, le=1000),
                          identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            panel = db.get(Panel, panel_id)
            if not panel:
                raise HTTPException(404, 'Panel not found')
            return history_page(db, panel_id, rt.run_id(panel), scope, before_id, limit)

    @app.get('/api/alarms')
    def alarms(status: Literal['active', 'acknowledged', 'resolved'] | None = None,
               severity: Literal['ATTENTION', 'WARNING', 'CRITICAL'] | None = None,
               scope: Literal['all', 'current'] = 'all', identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            current_runs = {panel.id: f'{panel.id}-r{panel.revision}' for panel in db.execute(select(Panel.id, Panel.revision))}
            query = select(Alarm)
            if status:
                query = query.where(Alarm.status == status)
            if severity:
                query = query.where(Alarm.severity == severity)
            if scope == 'current':
                query = query.where(Alarm.demo_run_id.in_(list(current_runs.values())))
            return {'items': [{**as_dict(alarm), 'is_current_run': alarm.demo_run_id == current_runs.get(alarm.panel_id)}
                              for alarm in db.scalars(query.order_by(Alarm.id.desc()).limit(500))]}

    @app.post('/api/alarms/{alarm_id}/acknowledge')
    def acknowledge(alarm_id: int, identity=Depends(roles('operator', 'admin')), rt=Depends(runtime)):
        with rt.write_lock(), rt.sessions.begin() as db:
            alarm = db.get(Alarm, alarm_id)
            if not alarm:
                raise HTTPException(404, 'Alarm not found')
            if alarm.status == 'resolved':
                raise HTTPException(409, 'Resolved alarm cannot be acknowledged')
            alarm.status, alarm.acknowledged_at = 'acknowledged', utcnow()
            db.add(Audit(username=identity['sub'], action='alarm_acknowledged', target=str(alarm_id), details={}))
            db.add(Event(panel_id=alarm.panel_id, type='alarm_acknowledged', demo_run_id=alarm.demo_run_id,
                         scenario_revision=alarm.scenario_revision, message=f'Alarm {alarm_id} acknowledged by {identity["sub"]}.'))
            db.flush()
            return as_dict(alarm)

    @app.get('/api/notifications')
    def notifications(identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            return {'items': [as_dict(n) for n in db.scalars(select(Notification).order_by(Notification.id.desc()).limit(500))]}

    @app.get('/api/events')
    def events(identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            return {'items': [as_dict(e) for e in db.scalars(select(Event).order_by(Event.id.desc()).limit(200))]}

    @app.get('/api/audit')
    def audit(identity=Depends(roles('admin')), rt=Depends(runtime)):
        with rt.sessions() as db:
            return {'items': [as_dict(a) for a in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(200))]}

    @app.get('/api/scenarios')
    def scenarios(identity=Depends(principal)):
        return {'items': SCENARIOS}

    @app.get('/api/action-policy')
    def action_matrix(identity=Depends(principal)):
        return policy_catalog()

    @app.get('/api/demo/state')
    def demo_state(identity=Depends(roles('service', 'admin', 'operator')), rt=Depends(runtime)):
        with rt.sessions() as db:
            panels = []
            for panel in db.execute(select(Panel.id, Panel.device_id, Panel.scenario, Panel.revision, Panel.scenario_started_at,
                          Panel.focused_demo, Panel.last_explicit_run_id.label('snapshot_run_id'),
                          Panel.last_explicit_step.label('last_step'),
                          Panel.last_explicit_arc_timestamp.label('arc_event_timestamp')).order_by(Panel.id)):
                run_id = f'{panel.id}-r{panel.revision}'
                matches = panel.snapshot_run_id == run_id
                panels.append({'id': panel.id, 'device_id': panel.device_id, 'scenario': panel.scenario,
                               'revision': panel.revision, 'scenario_revision': panel.revision, 'demo_run_id': run_id,
                               'started_at': aware(panel.scenario_started_at).isoformat(), 'focused_demo': panel.focused_demo,
                               'last_step': panel.last_step if matches else None,
                               'arc_event_timestamp': panel.arc_event_timestamp if matches else None})
            focus = next((panel['id'] for panel in panels if panel['focused_demo']), None)
            focus_interval = float(os.getenv('SIMULATOR_FOCUS_INTERVAL', '1.5'))
            max_fps = float(os.getenv('SIMULATOR_MAX_FPS', '50'))
            background_budget = max_fps - (1 / focus_interval if focus else 0)
            background_interval = publication_interval(len(panels) - int(bool(focus)),
                                  float(os.getenv('SIMULATOR_INTERVAL', '3')), background_budget)
            return {'panels': panels, 'focus_panel_id': focus,
                    'focus_interval_seconds': focus_interval, 'background_interval_seconds': background_interval,
                    'max_fps': max_fps, 'background_fps_budget': background_budget,
                    'timing_mode': 'accelerated_synthetic',
                    'mode': 'synthetic_demo', 'timestamp': utcnow().isoformat()}

    @app.post('/api/demo/scenario')
    def scenario(body: ScenarioSelection, identity=Depends(roles('operator', 'admin')), rt=Depends(runtime)):
        if body.scenario not in SCENARIO_IDS:
            raise HTTPException(422, 'Unknown scenario')
        with rt.write_lock(), rt.sessions.begin() as db:
            panel = db.get(Panel, body.panel_id)
            if not panel:
                raise HTTPException(404, 'Panel not found')
            if body.focused:
                for selected in db.scalars(select(Panel).where(Panel.focused_demo.is_(True))):
                    selected.focused_demo = False
            rt.start_run(db, panel, body.scenario, identity['sub'], body.focused)
            db.add(Audit(username=identity['sub'], action='demo_scenario_selected', target=panel.id, details={'scenario': body.scenario}))
            return {'ok': True, 'panel_id': panel.id, 'scenario': panel.scenario, 'revision': panel.revision,
                    'scenario_revision': panel.revision, 'demo_run_id': rt.run_id(panel), 'focused_demo': panel.focused_demo,
                    'pending_current_run': True, 'scenario_started_at': aware(panel.scenario_started_at).isoformat()}

    @app.post('/api/demo/fleet')
    def fleet_size(body: FleetSize, identity=Depends(roles('admin')), rt=Depends(runtime)):
        # Expansion only; preserve existing durable telemetry and identity history.
        rt.settings.panel_count = body.count
        with rt.write_lock():
            rt.seed()
        rt.audit(identity['sub'], 'demo_fleet_expanded', str(body.count))
        with rt.sessions() as db:
            total = db.scalar(select(func.count()).select_from(Panel))
        return {'ok': True, 'count': total, 'requested': body.count, 'behavior': 'expand_only'}

    @app.post('/api/demo/reset')
    def reset(identity=Depends(roles('admin')), rt=Depends(runtime)):
        with rt.write_lock(), rt.sessions.begin() as db:
            panels = db.scalars(select(Panel)).all()
            for panel in panels:
                rt.start_run(db, panel, 'normal_operation', identity['sub'], focused=False)
            db.add(Audit(username=identity['sub'], action='demo_reset', target='fleet', details={'preserves_history': True}))
        return {'ok': True, 'message': 'Sentetik çalışmalar normal senaryoyla yeniden başlatıldı. Telemetri, alarmlar ve audit korundu; önceki çalışma alarmları demo_run_superseded gerekçesiyle kapatıldı.'}

    @app.get('/api/scada/registers')
    def scada(panel_id: str = 'PNL-001', identity=Depends(principal), rt=Depends(runtime)):
        with rt.sessions() as db:
            ids = list(db.scalars(select(Panel.id)))
        from services.scada_bridge.banks import panel_bank_mapping, validate_bank_configuration
        base = rt.settings.scada_port_base if rt.settings.scada_port_base is not None else rt.settings.scada_port
        validate_bank_configuration(rt.settings.scada_bank_size, base, rt.settings.scada_bank_count)
        mapping = panel_bank_mapping([{'id': identifier} for identifier in ids], rt.settings.scada_bank_size, base)
        if panel_id not in mapping:
            raise HTTPException(404, 'Panel not found')
        address = mapping[panel_id]
        if address.bank > rt.settings.scada_bank_count:
            raise HTTPException(422, 'Panel exceeds the configured SCADA bank capacity')
        result = {'panel_id': panel_id, 'host': rt.settings.scada_host, 'port': address.port,
                  'bank': address.bank, 'bank_size': rt.settings.scada_bank_size,
                  'unit_id': address.unit_id, 'transport': 'modbus_tcp', 'connected': False, 'registers': [], 'timestamp': utcnow().isoformat()}
        try:
            from services.scada_bridge.master import read_panel_registers
            result['registers'] = read_panel_registers(rt.settings.scada_host, address.port, address.unit_id)
            result['connected'] = True
        except (OSError, TimeoutError, ValueError, ImportError) as exc:
            result['error'] = f'Read-only Modbus TCP master failed: {type(exc).__name__}: {exc}'
        return result

    @app.get('/api/metrics')
    def metrics(identity=Depends(roles('service', 'admin')), rt=Depends(runtime)):
        with rt.sessions() as db:
            durable = db.scalar(select(func.count()).select_from(Telemetry))
            alarms = db.scalar(select(func.count()).select_from(Alarm))
        metrics = dict(rt.metrics)
        accepted = metrics['accepted']
        metrics.update(telemetry_rows=durable, alarm_rows=alarms,
                       ingestion_latency_ms_mean=round(metrics['ingestion_latency_ms_total'] / accepted, 3) if accepted else 0,
                       db_write_ms_mean=round(metrics['db_write_ms_total'] / accepted, 3) if accepted else 0,
                       metrics_scope='Counters and timing since API process start; telemetry_rows/alarm_rows durable.',
                       timestamp=utcnow().isoformat())
        return metrics

    return app

app = create_app()
