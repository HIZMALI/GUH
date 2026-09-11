from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint, create_engine
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
    scenario_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

class Telemetry(Base):
    __tablename__ = 'telemetry'
    __table_args__ = (UniqueConstraint('device_id', 'message_id', name='uq_telemetry_identity'),
                      Index('ix_telemetry_panel_timestamp', 'panel_id', 'timestamp'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(24), index=True)
    panel_id: Mapped[str] = mapped_column(String(20), index=True)
    message_id: Mapped[str] = mapped_column(String(128))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)

class Alarm(Base):
    __tablename__ = 'alarms'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[str] = mapped_column(String(20), index=True)
    panel_name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(32), index=True)
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
    message: Mapped[str] = mapped_column(String(3000))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alarm_id: Mapped[int] = mapped_column(Integer, index=True)
    panel_id: Mapped[str] = mapped_column(String(20))
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

def make_database(url):
    options = {'pool_pre_ping': True}
    if url.startswith('sqlite'):
        options['connect_args'] = {'check_same_thread': False, 'timeout': 30}
        if ':memory:' in url:
            options['poolclass'] = StaticPool
    engine = create_engine(url, **options)
    Base.metadata.create_all(engine)
    # create_all skips index additions on existing tables; this idempotent additive
    # migration upgrades earlier prototype databases without deleting telemetry.
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(engine, checkfirst=True)
    return engine, sessionmaker(engine, expire_on_commit=False)

def as_dict(model):
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        result[column.name] = aware(value).isoformat() if isinstance(value, datetime) else value
    return result
