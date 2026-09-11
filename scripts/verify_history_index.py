"""Capture real PostgreSQL query plans before/after the additive legacy index.

Run in the API container, with the simulator paused. Output contains no credentials.
The after phase also reopens the database twice to check migration idempotency.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select, text
from apps.api.database import Telemetry, make_database


def main():
    phase = sys.argv[1]
    assert phase in {'before', 'after'}
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as connection:
        count_before = connection.scalar(select(func.count()).select_from(Telemetry))
    if phase == 'after':
        for _ in range(2):
            reopened, _ = make_database(os.environ['DATABASE_URL'])
            reopened.dispose()
    checks = []
    with engine.connect() as connection:
        count_after = connection.scalar(select(func.count()).select_from(Telemetry))
        assert count_before == count_after, 'Telemetry count changed during migration check'
        for panel in ['PNL-001', 'PNL-010']:
            for scenario in ['normal_operation', 'arc_event']:
                query = select(Telemetry.payload['measurements'].label('measurements'),
                               Telemetry.payload['quality'].label('quality'),
                               Telemetry.timestamp, Telemetry.simulation_step).where(
                    Telemetry.panel_id == panel, Telemetry.demo_run_id.is_(None),
                    Telemetry.payload['scenario'].as_string() == scenario
                ).order_by(Telemetry.timestamp.desc()).limit(12)
                sql = str(query.compile(engine, compile_kwargs={'literal_binds': True}))
                rows = [dict(row._mapping) for row in connection.execute(query)]
                digest = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
                plan = connection.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + sql)).scalar_one()[0]
                nodes = []
                def visit(node):
                    nodes.append({k: node[k] for k in ['Node Type', 'Index Name', 'Actual Rows',
                        'Rows Removed by Filter', 'Actual Loops', 'Actual Total Time'] if k in node})
                    for child in node.get('Plans', []):
                        visit(child)
                visit(plan['Plan'])
                ordered = any(n.get('Index Name') == 'ix_telemetry_legacy_scenario_timestamp'
                              and n['Node Type'] == 'Index Scan' for n in nodes)
                no_sort = not any(n['Node Type'] == 'Sort' for n in nodes)
                if phase == 'after':
                    assert ordered and no_sort and len(rows) == 12, nodes
                checks.append({'panel': panel, 'scenario': scenario, 'sql': sql, 'rows': len(rows),
                               'result_sha256': digest, 'execution_ms': plan['Execution Time'],
                               'ordered_scenario_index': ordered, 'no_sort': no_sort,
                               'nodes': nodes, 'plan': plan})
    print(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'phase': phase,
                      'telemetry_count': count_after, 'migration_reopened_twice': phase == 'after',
                      'checks': checks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
