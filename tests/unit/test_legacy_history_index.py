"""Legacy scenario history stays bounded by its ordered partial index."""
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import func, select, text
from apps.api.database import Telemetry, make_database


@pytest.mark.parametrize('scenario', ['normal_operation', 'arc_event'])
def test_existing_database_adds_legacy_index_and_avoids_history_sort(tmp_path, scenario):
    url = f'sqlite:///{tmp_path / "history.db"}'
    engine, sessions = make_database(url)
    start = datetime.now(timezone.utc)
    with sessions.begin() as db:
        for i in range(800):
            db.add(Telemetry(device_id='EDGE-001', panel_id='PNL-001', message_id=f'preserved-{i}',
                             timestamp=start + timedelta(seconds=i), demo_run_id=None if i < 400 else 'PNL-001-r2',
                             simulation_step=i, payload={'scenario': 'arc_event' if i % 10 == 0 else 'normal_operation',
                                                        'measurements': {'current_l1': i}, 'quality': {'current_l1': 'good'}},
                             result={'state': 'NORMAL', 'risk_score': 8}))
    # Represent an already populated v2 database from before this additive index.
    with engine.begin() as connection:
        connection.execute(text('DROP INDEX ix_telemetry_legacy_scenario_timestamp'))
    engine.dispose()
    for _ in range(2):  # Migration and another restart must both preserve history.
        engine, sessions = make_database(url)
        with sessions() as db:
            assert db.scalar(select(func.count()).select_from(Telemetry)) == 800
            query = select(Telemetry.payload['measurements'].label('measurements'),
                           Telemetry.payload['quality'].label('quality'), Telemetry.timestamp,
                           Telemetry.simulation_step).where(Telemetry.panel_id == 'PNL-001',
                               Telemetry.demo_run_id.is_(None), Telemetry.payload['scenario'].as_string() == scenario
                           ).order_by(Telemetry.timestamp.desc()).limit(12)
            sql = str(query.compile(engine, compile_kwargs={'literal_binds': True}))
            plan = ' '.join(str(row[-1]) for row in db.execute(text('EXPLAIN QUERY PLAN ' + sql)))
            assert 'ix_telemetry_legacy_scenario_timestamp' in plan
            assert 'TEMP B-TREE' not in plan
            expected = [i for i in range(399, -1, -1) if (i % 10 == 0) == (scenario == 'arc_event')][:12]
            assert [row.simulation_step for row in db.execute(query)] == expected
        engine.dispose()
