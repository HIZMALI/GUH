"""Generate private local configuration once; never overwrite existing secrets."""
from pathlib import Path
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]


def bootstrap() -> Path:
    target = ROOT / '.env'
    if target.exists():
        return target
    password = secrets.token_hex(24)
    entries = {
        'COMPOSE_PROJECT_NAME':'gridsentinel',
        'POSTGRES_DB':'gridsentinel', 'POSTGRES_USER':'gridsentinel',
        'POSTGRES_PASSWORD':password,
        'DATABASE_URL':f'postgresql+psycopg://gridsentinel:{password}@db:5432/gridsentinel',
        'ADMIN_USERNAME':'admin', 'ADMIN_PASSWORD':secrets.token_urlsafe(20),
        'OPERATOR_PASSWORD':secrets.token_urlsafe(20), 'VIEWER_PASSWORD':secrets.token_urlsafe(20),
        'AUTH_SECRET':secrets.token_hex(32), 'SERVICE_TOKEN':secrets.token_hex(32), 'DEVICE_TOKEN':secrets.token_hex(32),
        'MQTT_USERNAME':'gridsentinel', 'MQTT_PASSWORD':secrets.token_hex(24),
        'MQTT_HOST':'mqtt', 'MQTT_PORT':'1883', 'PANEL_COUNT':'100',
        'SIMULATOR_INTERVAL':'3', 'SIMULATOR_MAX_FPS':'50', 'SCADA_HOST':'scada', 'SCADA_PORT':'1502',
        'API_URL':'http://api:8000',
        'SCADA_PORT_BASE':'1502', 'SCADA_PORT_END':'1504', 'SCADA_BANK_SIZE':'247', 'SCADA_BANK_COUNT':'3',
        'SIMULATOR_FOCUS_INTERVAL':'1.5',
        'DB_CONNECT_TIMEOUT_SECONDS':'3', 'DB_POOL_TIMEOUT_SECONDS':'3',
        'DB_STATEMENT_TIMEOUT_MS':'5000', 'DB_LOCK_TIMEOUT_MS':'2000',
        'DB_SOCKET_TIMEOUT_MS':'5000', 'WRITE_LOCK_TIMEOUT_SECONDS':'3',
    }
    with target.open('x',encoding='utf-8',newline='\n') as f:
        f.write('# Generated locally. Private, ignored by Git.\n')
        f.write(''.join(f'{k}={v}\n' for k,v in entries.items()))
    if os.name != 'nt':
        target.chmod(0o600)
    return target


if __name__ == '__main__':
    print(f'Local configuration ready: {bootstrap()}')
    print('Login with ADMIN_USERNAME and ADMIN_PASSWORD from this file. Keep it private.')
