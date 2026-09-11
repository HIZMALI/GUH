"""Local synthetic-demo Modbus TCP server; FC03/04 only, NO passthrough or writes."""
import json
import logging
import os
import socket
import socketserver
import struct
import threading
import time
import urllib.request

from .master import receive_exact
from .registers import RegisterCache

LOG = logging.getLogger("gridsentinel.scada")


class ReadOnlyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(3.0)
        window, requests = time.monotonic(), 0
        while True:
            try:
                header = receive_exact(self.request, 7)
                transaction, protocol, length, unit = struct.unpack(">HHHB", header)
                if protocol != 0 or not 2 <= length <= 254:
                    return
                pdu = receive_exact(self.request, length - 1)
                now = time.monotonic()
                if now - window >= 1:
                    window, requests = now, 0
                requests += 1
                if requests > 120:
                    return
                function = pdu[0]
                if function not in (3, 4):
                    response = bytes((function | 0x80, 1))
                elif len(pdu) != 5:
                    response = bytes((function | 0x80, 3))
                else:
                    address, count = struct.unpack(">HH", pdu[1:])
                    if not 1 <= count <= 125:
                        response = bytes((function | 0x80, 3))
                    else:
                        try:
                            values = self.server.cache.read(unit, address, count)
                            response = bytes((function, count * 2)) + struct.pack(f">{count}H", *values)
                        except KeyError:
                            response = bytes((function | 0x80, 2))
                self.request.sendall(struct.pack(">HHHB", transaction, 0, len(response) + 1, unit) + response)
            except (OSError, TimeoutError, ValueError):
                return


class ReadOnlyModbusServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, server_address, cache):
        self.cache = cache
        self._connections = threading.BoundedSemaphore(64)
        super().__init__(server_address, ReadOnlyHandler)

    def process_request(self, request, client_address):
        if not self._connections.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connections.release()


def poll_fleet(cache, api_url, token, interval, stop):
    if interval <= 0:
        raise ValueError("poll interval must be positive")
    while not stop.is_set():
        started = time.monotonic()
        try:
            request = urllib.request.Request(api_url.rstrip("/") + "/api/fleet", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise ValueError("Fleet response too large")
                payload = json.loads(raw)
            if payload.get("mode") != "synthetic_demo":
                raise ValueError("This bridge is restricted to synthetic_demo fleet")
            cache.update(payload["panels"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            cache.mark_failed(exc)
            LOG.warning("Fleet unavailable; communication registers set to 0: %s", type(exc).__name__)
        stop.wait(max(.05, interval - (time.monotonic() - started)))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.environ.get("SERVICE_TOKEN")
    if not token:
        raise SystemExit("SERVICE_TOKEN is required; no default credential")
    cache = RegisterCache(float(os.environ.get("SCADA_STALE_SECONDS", "15")))
    stop = threading.Event()
    interval = float(os.environ.get("SCADA_POLL_INTERVAL", "1"))
    if interval <= 0:
        raise SystemExit("SCADA_POLL_INTERVAL must be positive")
    poller = threading.Thread(target=poll_fleet, args=(cache, os.environ.get("API_URL", "http://api:8000"), token, interval, stop), daemon=True)
    poller.start()
    host, port = os.environ.get("SCADA_HOST", "127.0.0.1"), int(os.environ.get("SCADA_PORT", "1502"))
    with ReadOnlyModbusServer((host, port), cache) as server:
        LOG.info("Synthetic demo read-only bridge listening on %s:%s", host, port)
        try:
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()


if __name__ == "__main__":
    main()
