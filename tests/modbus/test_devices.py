import unittest
from datetime import timedelta, timezone

from services.modbus.devices.common import decode_integer
from services.modbus.devices.mpr53cs import MPR53CS, REGISTERS as MPR_REGISTERS
from services.modbus.devices.tvoc2 import (TVOC2, REGISTERS as TVOC_REGISTERS, decode_detectors,
                                          decode_dtc, decode_firmware, decode_relays,
                                          decode_system_state, decode_timestamp, decode_trip)
from services.modbus.transport import ReadOnlyTCPGateway


class DeviceDecoderTests(unittest.TestCase):
    def test_mpr_literal_source_addresses_and_scale(self):
        # Independent source-page vector: phase voltage0, current6, power20, PF38, Hz58, THD78.
        raw = {0: 0, 1: 2310, 6: 4, 7: 55856, 20: 0xFFFF, 21: 0xFC18,
               38: 0xFFFF, 39: 0xFC7C, 58: 0, 59: 5000, 78: 0, 79: 73,
               60: 0, 61: 120, 84: 0x25, 85: 2}
        names = ["voltage_l1", "current_l1", "active_power_l1", "power_factor_l1",
                 "frequency_hz", "thd_current_l1", "voltage_angle_l1", "digital_output_status", "digital_input_status"]
        result = MPR53CS().decode(raw, names)
        expected = [231.0, 318.0, -100.0, -.900, 50.0, 7.3, 120, 0x25, 2]
        for name, value in zip(names, expected):
            self.assertAlmostEqual(result["measurements"][name], value)
        self.assertTrue(all(value == "good" for value in result["quality"].values()))
        self.assertFalse(result["word_order_verified"])
        self.assertFalse(result["ct_vt_applied_again"])

    def test_mpr_total_power_semantics_are_distinct(self):
        names = ["active_power_import_total", "active_power_export_total", "reactive_power_inductive_total",
                 "reactive_power_capacitive_total", "apparent_power_total"]
        self.assertEqual([MPR_REGISTERS[name].address for name in names], [44, 46, 48, 50, 52])
        self.assertEqual(MPR_REGISTERS["frequency_hz"].address, 58)
        self.assertEqual(MPR_REGISTERS["current_l1_demand"].address, 210)
        self.assertEqual(MPR_REGISTERS["voltage_l1_min"].address, 118)

    def test_unsigned_current_and_64_bit_energy(self):
        name = "import_active_energy_1"
        value = MPR53CS().decode({86: 0x8000, 87: 0, 88: 1, 89: 2}, [name])["measurements"][name]
        self.assertEqual(value, 0x8000000000010002)
        self.assertEqual(MPR_REGISTERS[name].width, 4)
        self.assertEqual(decode_integer([0xFFFF, 0xFFFF]), 2**32 - 1)
        self.assertEqual(decode_integer([0x8000, 0], signed=True), -(2**31))

    def test_mpr_little_word_order(self):
        reading = MPR53CS("little").decode({58: 5000, 59: 0}, ["frequency_hz"])
        self.assertEqual(reading["measurements"]["frequency_hz"], 50)
        self.assertRaises(ValueError, MPR53CS, "guess")

    def test_missing_invalid_registers_do_not_become_zero(self):
        result = MPR53CS().decode({0: 0, 6: -1, 7: 2}, ["voltage_l1", "current_l1"])
        self.assertEqual(result["measurements"], {"voltage_l1": None, "current_l1": None})
        self.assertEqual(result["quality"], {"voltage_l1": "missing", "current_l1": "invalid"})
        self.assertRaises(ValueError, decode_integer, [False, 3])

    def test_mpr_poll_timeout(self):
        class Offline:
            def read_registers(self, *args, **kwargs):
                raise TimeoutError("fixture timeout")
        result = MPR53CS().poll(Offline())
        self.assertFalse(result["communication_ok"])
        self.assertIsNone(result["measurements"]["current_l1"])

    def test_tvoc_detector_boundaries_and_reserved_bits(self):
        self.assertEqual(decode_detectors(0xC601, 0xC231),
                         ["X1:1", "X1:10", "X2:1", "X2:5", "X2:6", "X2:10", "X3:1", "X3:5", "X3:10"])
        self.assertEqual(decode_detectors(0x8000, 0x8000), [])
        self.assertEqual(len(decode_detectors(0x7FFF, 0x7FFF)), 30)
        self.assertEqual(decode_relays(0x8005), ["K4", "K6"])

    def test_tvoc_manual_timestamp_example_and_configured_zone(self):
        self.assertEqual(decode_timestamp(17078, 0x0922, 12), "2016-10-04T09:34:12+00:00")
        self.assertEqual(decode_timestamp(17078, 0x0922, 12, timezone(timedelta(hours=3))), "2016-10-04T06:34:12+00:00")
        for values in ((17078, 0x1822, 12), (17078, 0x093C, 12), (17078, 0x0922, 60), (0xFFFF, 0, 0)):
            self.assertRaises(ValueError, decode_timestamp, *values)

    def test_tvoc_unused_and_partial_sentinel(self):
        empty = decode_trip([0xFFFF] * 6)
        self.assertFalse(empty["present"])
        self.assertEqual(empty["quality"], "missing")
        self.assertEqual(decode_trip([1, 0, 1, 17078, 0xFFFF, 12])["quality"], "invalid")
        trip = decode_trip([1, 0, 5, 17078, 0x0922, 12])
        self.assertEqual(trip["detectors"], ["X1:1"])
        self.assertEqual(trip["trip_relays"], ["K4", "K6"])
        self.assertEqual(TVOC2().decode({100: -1, 101: 0, 102: 0, 103: 0, 104: 0, 105: 0})["quality"]["trip"], "invalid")

    def test_tvoc_firmware_dtc_and_state(self):
        self.assertEqual(decode_firmware([0x0300, 0]), (3, 0, 0))
        self.assertEqual(decode_firmware([0x0003, 0x002B]), (0, 3, 43))
        self.assertEqual(decode_dtc([0, 2, 0x4000]), [0, 0, 2, 0, 0, 64])
        self.assertEqual(decode_system_state(0x0F), {"active_trip": True, "active_error": True,
                                                 "startup": True, "diagnostics_running": True, "reserved_bits": 0})

    def test_tvoc_sensor_bit_polarity_context_and_module_presence(self):
        raw = {800: 0x0300, 801: 0, 1300: 2, 500: 4, 222: 0x3FE, 223: 0,
               224: 0x3FD, 225: 0}
        result = TVOC2().decode(raw)
        self.assertEqual(result["sensor_status"]["X2"]["X2:1"], "error")
        self.assertEqual(result["sensor_status"]["X2"]["X2:2"], "ok")
        self.assertEqual(result["ambient_light_warning"]["X2"]["X2:2"], "warning")
        self.assertNotIn("X3", result["sensor_status"])
        raw[1300] = 0
        self.assertIsNone(TVOC2().decode(raw)["sensor_status"])
        self.assertEqual(TVOC2().decode(raw)["quality"]["sensor_status"], "no_active_error")

    def test_tvoc_poll_firmware_gate_and_read_ranges(self):
        class Reader:
            def __init__(self, version):
                self.version, self.calls = version, []
            def read_registers(self, unit_id, address, count, timeout):
                self.calls.append((address, count, timeout))
                return self.version if address == 800 else [0] * count
        for version, should_poll in (([0x0209, 10], False), ([0x0300, 0], True)):
            reader = Reader(version)
            result = TVOC2().poll(reader, timeout=.5)
            self.assertEqual(any(call[0] == 222 for call in reader.calls), should_poll)
            self.assertEqual(reader.calls[0], (800, 2, .5))
            self.assertTrue(result["communication_ok"])
            self.assertTrue(all(address != 213 and address != 1000 for address, _, _ in reader.calls))
            self.assertTrue(all(not (address <= 106 < address + count) for address, count, _ in reader.calls))

    def test_tvoc_unknown_firmware_and_offline(self):
        class Offline:
            def read_registers(self, *args, **kwargs):
                raise TimeoutError("device offline")
        result = TVOC2().poll(Offline())
        self.assertFalse(result["communication_ok"])
        self.assertIsNone(result["event"])
        self.assertEqual(result["quality"]["sensor_status"], "firmware_unknown")

    def test_source_metadata_and_write_absence(self):
        self.assertTrue(all(spec.source and spec.page and spec.width and spec.scale and spec.convention for spec in MPR_REGISTERS.values()))
        self.assertTrue(all(spec.width == 1 and not spec.signed for spec in TVOC_REGISTERS.values()))
        self.assertNotIn(213, [spec.address for spec in TVOC_REGISTERS.values()])
        self.assertNotIn(1000, [spec.address for spec in TVOC_REGISTERS.values()])
        self.assertRaises(ValueError, ReadOnlyTCPGateway, "127.0.0.1", 502, 16)


if __name__ == "__main__":
    unittest.main()
