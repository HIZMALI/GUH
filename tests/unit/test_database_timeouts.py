"""Real socket/pool boundaries without external PostgreSQL or Docker mutations."""
import socket
import threading
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, TimeoutError
from apps.api.database import database_options


def test_postgresql_silent_peer_connection_fails_within_configured_deadline():
    # Accept TCP but never answer PostgreSQL/SSL startup. This catches a missing
    # connect_timeout; testing only a closed port would fail immediately anyway.
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    server.settimeout(5)
    stop = threading.Event()

    def silent_peer():
        try:
            with server.accept()[0]:
                stop.wait(5)
        except OSError:
            pass

    worker = threading.Thread(target=silent_peer)
    worker.start()
    engine = create_engine(f'postgresql+psycopg://probe:unused@127.0.0.1:{server.getsockname()[1]}/probe',
                           **database_options('postgresql+psycopg://', connect_timeout=2))
    began = time.monotonic()
    try:
        with pytest.raises(OperationalError):
            engine.connect()
        assert 1.5 < time.monotonic() - began < 4
    finally:
        stop.set()
        server.close()
        worker.join(1)
        engine.dispose()


def test_postgresql_pool_checkout_uses_short_timeout(tmp_path):
    # Exercise QueuePool's real checkout behavior with SQLite connections so
    # this test is independent of a running database service.
    configured = database_options('postgresql+psycopg://', pool_timeout=.05)
    engine = create_engine(f'sqlite:///{tmp_path / "pool.db"}', pool_size=1, max_overflow=0,
                           pool_timeout=configured['pool_timeout'])
    try:
        with engine.connect():
            began = time.monotonic()
            with pytest.raises(TimeoutError):
                engine.connect()
            assert .04 < time.monotonic() - began < .5
    finally:
        engine.dispose()
