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
    rate_limit: int = 1200
    session_seconds: int = 28800

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
                   rate_limit=int(os.getenv('API_RATE_LIMIT', '1200')))
