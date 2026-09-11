from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

def utcnow():
    return datetime.now(timezone.utc)

def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(256))

class Panel(Base):
    __tablename__ = 'panels'
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(80))
    substation: Mapped[str] = mapped_column(String(80))
    transformer: Mapped[str] = mapped_column(String(80))
    device_id: Mapped[str] = mapped_column(String(24), unique=True)
    device_key_hash: Mapped[str] = mapped_column(String(64))
    scenario: Mapped[str] = mapped_column(String(64), default='normal_operation')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    focused_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    last_explicit_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_explicit_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_explicit_arc_timestamp: Mapped[str | None] = mapped_column(String(48), nullable=True)
    scenario_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

class Telemetry(Base):
    __tablename__ = 'telemetry'
    __table_args__ = (UniqueConstraint('device_id', 'message_id', name='uq_telemetry_identity'),
                      Index('ix_telemetry_panel_timestamp', 'panel_id', 'timestamp'),
                      Index('ix_telemetry_panel_run_timestamp', 'panel_id', 'demo_run_id', 'timestamp'),
                      Index('uq_telemetry_run_step', 'device_id', 'demo_run_id', 'simulation_step', unique=True))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(24), index=True)
    panel_id: Mapped[str] = mapped_column(String(20), index=True)
    message_id: Mapped[str] = mapped_column(String(128))
    scenario_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demo_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    simulation_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)

# Legacy frames remain unassigned to a demo run, but their history must still
# match the producing scenario. Match the exact JSON scalar expression used by
# ingestion so LIMIT 12 can stop an ordered index scan instead of filtering and
# sorting every historical observation for the panel.
Index('ix_telemetry_legacy_scenario_timestamp', Telemetry.panel_id,
      Telemetry.payload['scenario'].as_string(), Telemetry.timestamp,
      postgresql_where=Telemetry.demo_run_id.is_(None), sqlite_where=Telemetry.demo_run_id.is_(None))

class Alarm(Base):
    __tablename__ = 'alarms'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[str] = mapped_column(String(20), index=True)
    panel_name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(32), index=True)
    scenario_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demo_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(String(3000))
    status: Mapped[str] = mapped_column(String(20), default='active', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[str] = mapped_column(String(20), index=True)
    type: Mapped[str] = mapped_column(String(40))
    scenario_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demo_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message: Mapped[str] = mapped_column(String(3000))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alarm_id: Mapped[int] = mapped_column(Integer, index=True)
    panel_id: Mapped[str] = mapped_column(String(20))
    scenario_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demo_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32))
    recipient: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    message: Mapped[str] = mapped_column(String(3000))

class Audit(Base):
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(180))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SchemaMigration(Base):
    __tablename__ = 'schema_migrations'
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(180))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

def migrate_v2_columns(engine):
    """Add only nullable provenance columns; never guess a run for historical v1 data."""
    changes = {
        'panels': {'focused_demo': 'BOOLEAN NOT NULL DEFAULT FALSE', 'last_explicit_run_id': 'VARCHAR(80)',
                   'last_explicit_step': 'INTEGER', 'last_explicit_arc_timestamp': 'VARCHAR(48)'},
        'telemetry': {'scenario_revision': 'INTEGER', 'demo_run_id': 'VARCHAR(80)', 'simulation_step': 'INTEGER'},
        'alarms': {'scenario_revision': 'INTEGER', 'demo_run_id': 'VARCHAR(80)', 'resolution_reason': 'VARCHAR(80)'},
        'events': {'scenario_revision': 'INTEGER', 'demo_run_id': 'VARCHAR(80)', 'details': 'JSON'},
        'notifications': {'scenario_revision': 'INTEGER', 'demo_run_id': 'VARCHAR(80)'},
    }
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, additions in changes.items():
            if table not in existing:
                continue
            columns = {column['name'] for column in inspector.get_columns(table)}
            for name, definition in additions.items():
                if name not in columns:
                    # Identifiers and SQL types are fixed source constants, never user input.
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))

def database_options(url, *, connect_timeout=3, pool_timeout=3, statement_timeout_ms=5000,
                     lock_timeout_ms=2000, socket_timeout_ms=5000):
    options = {'pool_pre_ping': True}
    if url.startswith('sqlite'):
        options['connect_args'] = {'check_same_thread': False, 'timeout': 30}
        if ':memory:' in url:
            options['poolclass'] = StaticPool
    elif url.startswith('postgresql'):
        # connect_timeout bounds connection establishment, not DNS resolution.
        # Deployment also bounds resolver retries. Socket limits cover stale
        # pooled connections whose peer disappears before pre_ping or a query.
        options.update(pool_timeout=pool_timeout, connect_args={
            'connect_timeout': connect_timeout,
            'options': f'-c statement_timeout={statement_timeout_ms} -c lock_timeout={lock_timeout_ms}',
            'keepalives': 1, 'keepalives_idle': 2, 'keepalives_interval': 1, 'keepalives_count': 2,
            'tcp_user_timeout': socket_timeout_ms,
        })
    return options

def make_database(url, **timeouts):
    options = database_options(url, **timeouts)
    engine = create_engine(url, **options)
    migrate_v2_columns(engine)
    Base.metadata.create_all(engine)
    # create_all skips index additions on existing tables; this idempotent additive
    # migration upgrades earlier prototype databases without deleting telemetry.
    # SQLAlchemy's SQLite reflection omits expression indexes. Read their names
    # directly for idempotency; index.create(checkfirst=True) alone misses them.
    sqlite_indexes = set()
    if engine.dialect.name == 'sqlite':
        with engine.connect() as connection:
            sqlite_indexes = set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type='index'")))
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            if index.name not in sqlite_indexes:
                index.create(engine, checkfirst=True)
    with sessionmaker(engine).begin() as db:
        if not db.get(SchemaMigration, 2):
            db.add(SchemaMigration(version=2, description='Nullable demo-run identity, scoped indexes and single focused panel'))
    return engine, sessionmaker(engine, expire_on_commit=False)

def as_dict(model):
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        result[column.name] = aware(value).isoformat() if isinstance(value, datetime) else value
    return result
