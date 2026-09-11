"""Read-only current-run and historical projections; v1 aliases retain their original scope."""
from sqlalchemy import func, or_, select
from apps.api.database import Alarm, Event, Telemetry, aware, as_dict
from services.anomaly_engine.timeline import early_warning_timeline
from services.simulator.scenarios import SCENARIOS

def history_item(row):
    return {'id': row.id, 'timestamp': aware(row.timestamp).isoformat(), 'risk_score': row.result['risk_score'],
            'health_score': row.result['health_score'], 'state': row.result['state'],
            'measurements': row.payload['measurements'], 'quality': row.payload['quality'],
            'provenance': row.payload.get('provenance', {}), 'source': row.payload['source'],
            'demo_run_id': row.demo_run_id, 'scenario_revision': row.scenario_revision,
            'simulation_step': row.simulation_step if row.simulation_step is not None else row.payload.get('simulation_step', 0)}

def history_page(db, panel_id, run_id, scope='all', before_id=None, limit=120):
    conditions = [Telemetry.panel_id == panel_id]
    if scope == 'current':
        conditions.append(Telemetry.demo_run_id == run_id)
    total = db.scalar(select(func.count()).select_from(Telemetry).where(*conditions))
    if before_id is not None:
        conditions.append(Telemetry.id < before_id)
    rows = db.scalars(select(Telemetry).where(*conditions).order_by(Telemetry.id.desc()).limit(limit + 1)).all()
    has_more, rows = len(rows) > limit, rows[:limit]
    return {'items': [history_item(row) for row in reversed(rows)],
            'next_before_id': rows[-1].id if rows and has_more else None, 'total': total, 'scope': scope}

def panel_history(db, panel, run_id):
    full = history_page(db, panel.id, run_id)
    current = history_page(db, panel.id, run_id, scope='current')
    alarms = db.scalars(select(Alarm).where(Alarm.panel_id == panel.id).order_by(Alarm.id.desc()).limit(100)).all()
    current_alarms = db.scalars(select(Alarm).where(Alarm.panel_id == panel.id, Alarm.demo_run_id == run_id)
                               .order_by(Alarm.id.desc()).limit(100)).all()
    historical = db.scalars(select(Alarm).where(Alarm.panel_id == panel.id,
                            or_(Alarm.demo_run_id != run_id, Alarm.demo_run_id.is_(None)))
                            .order_by(Alarm.id.desc()).limit(100)).all()
    full_events = db.scalars(select(Event).where(Event.panel_id == panel.id).order_by(Event.id.desc()).limit(100)).all()
    current_events = db.scalars(select(Event).where(Event.panel_id == panel.id, Event.demo_run_id == run_id)
                               .order_by(Event.id.desc()).limit(100)).all()
    transitions = [event.details for event in db.scalars(select(Event).where(Event.panel_id == panel.id,
                   Event.demo_run_id == run_id, Event.type == 'state_changed').order_by(Event.id)) if event.details]
    duration = next(item['duration_steps'] for item in SCENARIOS if item['id'] == panel.scenario)
    last_step = current['items'][-1]['simulation_step'] if current['items'] else -1

    def alarm_item(alarm):
        return {**as_dict(alarm), 'is_current_run': alarm.demo_run_id == run_id}

    return {'history': full['items'], 'full_history': full['items'], 'current_run_history': current['items'],
            'full_history_total': full['total'], 'full_history_has_more': full['next_before_id'] is not None,
            'full_history_next_before_id': full['next_before_id'],
            'current_run_history_total': current['total'],
            'alarms': [alarm_item(alarm) for alarm in alarms],
            'current_run_alarms': [alarm_item(alarm) for alarm in current_alarms],
            'historical_alarms': [alarm_item(alarm) for alarm in historical],
            'events': [as_dict(event) for event in full_events],
            'full_events': [as_dict(event) for event in full_events],
            'current_run_events': [as_dict(event) for event in current_events],
            'early_warning': early_warning_timeline(transitions, complete=last_step >= duration - 1)}
