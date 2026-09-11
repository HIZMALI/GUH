import json
import socket
import struct
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from services.scada_bridge.master import ModbusException, read_panel_registers, read_registers, receive_exact
from services.scada_bridge.registers import RegisterCache, UNKNOWN, encode_panel, panel_unit_mapping
from services.scada_bridge.server import ReadOnlyModbusServer, poll_fleet


def panel(identifier="PNL-001", **changes):
    value = {"id": identifier, "health_score": 96, "risk_score": 8, "state": "NORMAL",
             "communication_ok": True, "last_seen": "2026-09-11T00:00:00+00:00",
             "arc": {"event": False}, "explanation": {"data_quality": [], "contributions": []}}
    value.update(changes)
    return value


class TCPBridgeTests(unittest.TestCase):
    def setUp(self):
        self.cache = RegisterCache(stale_seconds=30)
        self.cache.update([panel()])
        self.server = ReadOnlyModbusServer(("127.0.0.1", 0), self.cache)
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        self.worker.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(1)

    def test_actual_tcp_fc03_fc04_and_master_labels(self):
        for function in (3, 4):
            values = read_registers(self.host, self.port, 1, function=function)
            self.assertEqual(values[:10], [96, 8, 0, 0, 0, 0, 0, 1, 100, 1])
        rows = read_panel_registers(self.host, self.port, 1)
        self.assertEqual(rows[1], {"address": 1, "name": "risk_score", "value": 8, "unit": "score"})

    def test_actual_tcp_alarm_transition(self):
        self.cache.update([panel(state="CRITICAL", health_score=10, risk_score=100, arc={"event": True})])
        values = read_registers(self.host, self.port, 1)
        self.assertEqual(values[1:4], [100, 3, 1])
        self.assertEqual(values[6], 1)

    def test_invalid_address_and_unknown_unit_exception02(self):
        for unit, address, count in ((1, 11, 2), (1, 12, 1), (2, 0, 1)):
            with self.assertRaises(ModbusException) as result:
                read_registers(self.host, self.port, unit, address, count)
            self.assertEqual(result.exception.code, 2)

    def test_all_write_functions_rejected_and_state_unchanged(self):
        before = read_registers(self.host, self.port, 1)
        for function in (5, 6, 15, 16, 22, 23):
            packet = struct.pack(">HHHBBHH", 7, 0, 6, 1, function, 0, 0)
            with socket.create_connection((self.host, self.port), timeout=1) as connection:
                connection.sendall(packet)
                response = receive_exact(connection, 9)
            self.assertEqual(response[-2:], bytes([function | 0x80, 1]))
        self.assertEqual(read_registers(self.host, self.port, 1), before)

    def test_fragmented_request_and_persistent_connection(self):
        packet = struct.pack(">HHHBBHH", 44, 0, 6, 1, 3, 0, 2)
        with socket.create_connection((self.host, self.port), timeout=1) as connection:
            connection.sendall(packet[:5])
            connection.sendall(packet[5:])
            self.assertEqual(receive_exact(connection, 13)[-4:], struct.pack(">HH", 96, 8))
            connection.sendall(packet)
            self.assertEqual(receive_exact(connection, 13)[-4:], struct.pack(">HH", 96, 8))

    def test_zero_count_exception03_and_malformed_mbap_closed(self):
        with socket.create_connection((self.host, self.port), timeout=1) as connection:
            connection.sendall(struct.pack(">HHHBBHH", 1, 0, 6, 1, 3, 0, 0))
            self.assertEqual(receive_exact(connection, 9)[-2:], b"\x83\x03")
        with socket.create_connection((self.host, self.port), timeout=1) as connection:
            connection.sendall(struct.pack(">HHHB", 1, 0, 65535, 1))
            self.assertEqual(connection.recv(1), b"")

    def test_staleness_and_api_failure_never_silent_healthy(self):
        self.cache.stale_seconds = .001
        time.sleep(.005)
        self.assertEqual(read_registers(self.host, self.port, 1)[7:9], [0, 0])
        self.cache.update([panel()])
        self.cache.mark_failed("API offline")
        values = read_registers(self.host, self.port, 1)
        self.assertEqual(values[7:9], [0, 0])
        self.assertEqual(values[0], 96)  # Last score retained; validity at7 must be checked.

    def test_map_timestamp_unknown_and_numeric_panel_sort(self):
        values = encode_panel(panel(state="MYSTERY", last_seen="2026-09-11T00:00:00", risk_score=None))
        self.assertEqual(values[1:4], [UNKNOWN, UNKNOWN, UNKNOWN])
        self.assertEqual(values[10:12], [UNKNOWN, UNKNOWN])
        self.assertEqual(panel_unit_mapping([panel("PNL-010"), panel("PNL-2"), panel("PNL-1")]),
                         {"PNL-1": 1, "PNL-2": 2, "PNL-010": 3})
        self.assertEqual(len(panel_unit_mapping([panel(f"PNL-{n:03d}") for n in range(1, 501)])), 247)
        self.assertRaises(ValueError, panel_unit_mapping, [panel(), panel()])

    def test_authenticated_http_poll_to_tcp_roundtrip(self):
        seen = []
        class FleetHandler(BaseHTTPRequestHandler):
            def do_GET(handler):
                seen.append((handler.path, handler.headers.get("Authorization")))
                body = json.dumps({"mode": "synthetic_demo", "panels": [panel(risk_score=81, state="CRITICAL")]}).encode()
                handler.send_response(200)
                handler.end_headers()
                handler.wfile.write(body)
            def log_message(*args):
                pass
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), FleetHandler)
        http_thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        http_thread.start()
        stop = threading.Event()
        poller = threading.Thread(target=poll_fleet, args=(self.cache, f"http://127.0.0.1:{httpd.server_port}", "fixture-token", .01, stop), daemon=True)
        poller.start()
        try:
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline and read_registers(self.host, self.port, 1)[1] != 81:
                time.sleep(.01)
            self.assertEqual(read_registers(self.host, self.port, 1)[1], 81)
            self.assertEqual(seen[0], ("/api/fleet", "Bearer fixture-token"))
        finally:
            stop.set()
            poller.join(1)
            httpd.shutdown()
            httpd.server_close()

    def test_actual_tcp_timeout_and_offline(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        silent_port = listener.getsockname()[1]
        try:
            with self.assertRaises(TimeoutError):
                read_registers("127.0.0.1", silent_port, 1, timeout=.03)
        finally:
            listener.close()
        with self.assertRaises(OSError):
            read_registers("127.0.0.1", silent_port, 1, timeout=.03)


if __name__ == "__main__":
    unittest.main()
