"""V2 addressing boundaries and actual sockets; no physical SCADA involved."""
from contextlib import ExitStack
from datetime import datetime, timezone
import socket
import struct
import threading
import pytest
from services.scada_bridge.banks import BankFleetCache, panel_bank_mapping, validate_bank_configuration
from services.scada_bridge.master import ModbusException, read_registers, receive_exact
from services.scada_bridge.server import ReadOnlyModbusServer


def fleet(count=500):
    return [{'id': f'PNL-{n:03d}', 'risk_score': n % 101, 'health_score': 96,
             'state': 'NORMAL', 'communication_ok': True, 'arc': {'event': False},
             'last_seen': datetime.fromtimestamp(1700000000 + n, timezone.utc).isoformat(),
             'explanation': {'data_quality': [], 'contributions': []}}
            for n in range(1, count + 1)]


@pytest.mark.parametrize('number,bank,port,unit', [
    (1, 1, 1502, 1), (247, 1, 1502, 247), (248, 2, 1503, 1),
    (494, 2, 1503, 247), (495, 3, 1504, 1), (500, 3, 1504, 6)])
def test_source_panel_bank_boundaries(number, bank, port, unit):
    mapping = panel_bank_mapping(list(reversed(fleet())))
    result = mapping[f'PNL-{number:03d}']
    assert (result.bank, result.port, result.unit_id) == (bank, port, unit)


def test_configuration_capacity_and_duplicates():
    custom = panel_bank_mapping(fleet(250), bank_size=100, port_base=1600)
    assert (custom['PNL-250'].bank, custom['PNL-250'].port, custom['PNL-250'].unit_id) == (3, 1602, 50)
    for args in ((248, 1502, 3), (0, 1502, 3), (247, 65535, 3), (247, 1502, 0)):
        with pytest.raises(ValueError):
            validate_bank_configuration(*args)
    with pytest.raises(ValueError, match='Duplicate'):
        panel_bank_mapping([fleet(1)[0], fleet(1)[0]])
    with pytest.raises(ValueError, match='complete fleet'):
        BankFleetCache(bank_count=2).update(fleet())


@pytest.fixture
def banks():
    cache = BankFleetCache()
    cache.update(fleet())
    with ExitStack() as resources:
        servers = [resources.enter_context(ReadOnlyModbusServer(('127.0.0.1', 0), c)) for c in cache.caches]
        workers = [threading.Thread(target=s.serve_forever, kwargs={'poll_interval': .01}, daemon=True) for s in servers]
        for worker in workers:
            worker.start()
        try:
            yield cache, [s.server_address for s in servers]
        finally:
            for server in servers:
                server.shutdown()
            for worker in workers:
                worker.join(1)


def test_every_one_of_500_panels_has_a_distinct_actual_tcp_roundtrip(banks):
    _, endpoints = banks
    mapping = panel_bank_mapping(fleet())
    for number in range(1, 501):
        address = mapping[f'PNL-{number:03d}']
        host, port = endpoints[address.bank - 1]
        values = read_registers(host, port, address.unit_id)
        assert values[1] == number % 101
        assert (values[10] << 16) | values[11] == 1700000000 + number
    assert len({(a.bank, a.unit_id) for a in mapping.values()}) == 500


@pytest.mark.parametrize('bank', [0, 1, 2])
def test_each_bank_invalid_register_and_all_write_functions(banks, bank):
    _, endpoints = banks
    host, port = endpoints[bank]
    before = read_registers(host, port, 1)
    with pytest.raises(ModbusException) as caught:
        read_registers(host, port, 1, address=60000, count=1)
    assert caught.value.code == 2
    for function in (5, 6, 15, 16, 22, 23):
        with socket.create_connection((host, port), 2) as connection:
            connection.sendall(struct.pack('>HHHBBHH', 9, 0, 6, 1, function, 0, 0))
            assert receive_exact(connection, 9)[-2:] == bytes((function | 0x80, 1))
    assert read_registers(host, port, 1) == before


def test_all_banks_mark_unavailable_together_and_recover(banks):
    cache, endpoints = banks
    cache.mark_failed('explicit synthetic API outage')
    for host, port in endpoints:
        assert read_registers(host, port, 1)[7:9] == [0, 0]
    cache.update(fleet())
    for host, port in endpoints:
        assert read_registers(host, port, 1)[7:9] == [1, 100]


def test_unallocated_unit_of_partial_final_bank_is_rejected(banks):
    _, endpoints = banks
    with pytest.raises(ModbusException) as caught:
        read_registers(*endpoints[2], 7)
    assert caught.value.code == 2
def test_pending_run_closes_scada_validity_gate_without_fabricating_new_values():
    from services.scada_bridge.registers import encode_panel
    panel = {'id': 'PNL-001', 'health_score': 12, 'risk_score': 88, 'state': 'CRITICAL',
             'communication_ok': True, 'pending_current_run': True, 'sensor_health': 100,
             'last_seen': '2026-09-11T00:00:00+00:00'}
    values = encode_panel(panel)
    assert values[:3] == [12, 88, 3]  # Last observation remains explicitly historical.
    assert values[7:9] == [0, 0]     # Consumers cannot treat it as a current healthy run.
