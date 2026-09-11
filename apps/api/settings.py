from dataclasses import dataclass
import os

@dataclass
class Settings:
    database_url: str
    auth_secret: str
    service_token: str
    device_token: str
    admin_username: str
    passwords: dict[str, str]
    panel_count: int = 100
    stale_seconds: int = 20
    mqtt_enabled: bool = True
    scada_host: str = 'scada'
    scada_port: int = 1502
    scada_port_base: int | None = None
    scada_bank_size: int = 247
    scada_bank_count: int = 3
    rate_limit: int = 1200
    session_seconds: int = 28800
    db_connect_timeout_seconds: int = 3
    db_pool_timeout_seconds: float = 3
    db_statement_timeout_ms: int = 5000
    db_lock_timeout_ms: int = 2000
    db_socket_timeout_ms: int = 5000
    write_lock_timeout_seconds: float = 3

    @classmethod
    def from_env(cls):
        required = ['DATABASE_URL', 'AUTH_SECRET', 'SERVICE_TOKEN', 'DEVICE_TOKEN', 'ADMIN_PASSWORD',
                    'OPERATOR_PASSWORD', 'VIEWER_PASSWORD']
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise RuntimeError('Missing bootstrap environment: ' + ', '.join(missing))
        if any(len(os.environ[key]) < 24 for key in ['AUTH_SECRET', 'SERVICE_TOKEN', 'DEVICE_TOKEN']):
            raise RuntimeError('AUTH_SECRET, SERVICE_TOKEN and DEVICE_TOKEN must each be at least 24 characters')
        return cls(database_url=os.environ['DATABASE_URL'], auth_secret=os.environ['AUTH_SECRET'],
                   service_token=os.environ['SERVICE_TOKEN'], device_token=os.environ['DEVICE_TOKEN'],
                   admin_username=os.getenv('ADMIN_USERNAME', 'admin'),
                   passwords={role: os.environ[f'{role.upper()}_PASSWORD'] for role in ('admin', 'operator', 'viewer')},
                   panel_count=max(1, min(10000, int(os.getenv('PANEL_COUNT', '100')))),
                   stale_seconds=max(5, int(os.getenv('STALE_SECONDS', '20'))),
                   mqtt_enabled=os.getenv('MQTT_ENABLED', 'true').lower() == 'true',
                   scada_host=os.getenv('SCADA_HOST', 'scada'), scada_port=int(os.getenv('SCADA_PORT', '1502')),
                   scada_port_base=int(os.getenv('SCADA_PORT_BASE', os.getenv('SCADA_PORT', '1502'))),
                   scada_bank_size=int(os.getenv('SCADA_BANK_SIZE', '247')),
                   scada_bank_count=int(os.getenv('SCADA_BANK_COUNT', '3')),
                   rate_limit=int(os.getenv('API_RATE_LIMIT', '1200')),
                   db_connect_timeout_seconds=max(2, int(os.getenv('DB_CONNECT_TIMEOUT_SECONDS', '3'))),
                   db_pool_timeout_seconds=max(.1, float(os.getenv('DB_POOL_TIMEOUT_SECONDS', '3'))),
                   db_statement_timeout_ms=max(100, int(os.getenv('DB_STATEMENT_TIMEOUT_MS', '5000'))),
                   db_lock_timeout_ms=max(100, int(os.getenv('DB_LOCK_TIMEOUT_MS', '2000'))),
                   db_socket_timeout_ms=max(1000, int(os.getenv('DB_SOCKET_TIMEOUT_MS', '5000'))),
                   write_lock_timeout_seconds=max(.1, float(os.getenv('WRITE_LOCK_TIMEOUT_SECONDS', '3'))))
