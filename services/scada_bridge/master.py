"""Small synchronous Modbus TCP read-only master; validates complete MBAP and PDU."""
import argparse
import json
import secrets
import socket
import struct

from .registers import REGISTER_MAP


class ModbusException(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"Modbus exception {code:02d}")


def receive_exact(sock, count):
    chunks = bytearray()
    while len(chunks) < count:
        fragment = sock.recv(count - len(chunks))
        if not fragment:
            raise ConnectionError("Modbus peer closed an incomplete frame")
        chunks.extend(fragment)
    return bytes(chunks)


def read_registers(host, port, unit_id, address=0, count=12, *, timeout=2.0, function=3):
    if function not in (3, 4):
        raise ValueError("Only read functions FC03/FC04 are permitted")
    if not 1 <= unit_id <= 247 or not 0 <= address <= 65535 or not 1 <= count <= 125 or address + count > 65536:
        raise ValueError("Invalid unit/address/count")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    transaction = secrets.randbelow(65536)
    request = struct.pack(">HHHBBHH", transaction, 0, 6, unit_id, function, address, count)
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(request)
        rx_id, protocol, length, rx_unit = struct.unpack(">HHHB", receive_exact(sock, 7))
        if rx_id != transaction or protocol != 0 or rx_unit != unit_id or not 2 <= length <= 254:
            raise ValueError("Invalid Modbus MBAP response")
        pdu = receive_exact(sock, length - 1)
    if pdu[0] == function | 0x80:
        if len(pdu) != 2:
            raise ValueError("Malformed exception response")
        raise ModbusException(pdu[1])
    if pdu[0] != function or len(pdu) != 2 + 2 * count or pdu[1] != 2 * count:
        raise ValueError("Invalid Modbus function/byte count response")
    return list(struct.unpack(f">{count}H", pdu[2:]))


def read_panel_registers(host: str, port: int, unit_id: int, timeout: float = 2.0) -> list[dict]:
    values = read_registers(host, port, unit_id, timeout=timeout)
    return [{"address": address, "name": name, "value": values[address], "unit": unit}
            for address, name, unit in REGISTER_MAP]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only GridSentinel SCADA demo master")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1502)
    parser.add_argument("--unit", type=int, default=1)
    arguments = parser.parse_args()
    print(json.dumps(read_panel_registers(arguments.host, arguments.port, arguments.unit), indent=2))
