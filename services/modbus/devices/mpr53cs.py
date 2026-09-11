"""MPR-53CS supplied map 01.12.2019, page 1; read-only.

The source does NOT specify multi-register word order. 'big' is a configurable,
unverified integration default. Device values already include configured CT/VT.
"""
from datetime import datetime, timezone
from typing import Mapping

from .common import Register, read_value, words_checked

SOURCE = "MPR-53CS_Modbus_Register_Map_EN.pdf"
REGISTERS: dict[str, Register] = {}


def _add(name, address, scale, unit, signed=False, width=2, note=""):
    REGISTERS[name] = Register(name, address, width, scale, signed, unit, SOURCE, 1,
                              "source ADDRESS used as PDU zero-based; field verification required", note)


for phase in range(1, 4):
    offset = (phase - 1) * 2
    _add(f"voltage_l{phase}", offset, .1, "V")
    _add(f"current_l{phase}", 6 + offset, .001, "A")
    _add(f"active_power_l{phase}", 20 + offset, .1, "W", True)
    _add(f"reactive_power_l{phase}", 26 + offset, .1, "var", True)
    _add(f"apparent_power_l{phase}", 32 + offset, .1, "VA")
    _add(f"power_factor_l{phase}", 38 + offset, .001, "ratio", True)
    _add(f"voltage_angle_l{phase}", 60 + offset, 1, "degree")
    _add(f"current_angle_l{phase}", 66 + offset, 1, "degree")
    _add(f"thd_voltage_l{phase}", 72 + offset, .1, "%")
    _add(f"thd_current_l{phase}", 78 + offset, .1, "%")
_add("current_neutral", 12, .001, "A")
for address, name in [(14, "voltage_l1_l2"), (16, "voltage_l2_l3"), (18, "voltage_l3_l1")]:
    _add(name, address, .1, "V")
for address, name, unit in [(44, "active_power_import_total", "W"), (46, "active_power_export_total", "W"),
                            (48, "reactive_power_inductive_total", "var"), (50, "reactive_power_capacitive_total", "var")]:
    _add(name, address, .1, unit, True)
_add("apparent_power_total", 52, .1, "VA")
_add("power_factor_inductive_average", 54, .001, "ratio", True)
_add("power_factor_capacitive_average", 56, .001, "ratio", True)
_add("frequency_hz", 58, .01, "Hz")
_add("digital_output_status", 84, 1, "raw", width=1,
     note="Source explicitly R; format and bit meanings unspecified; uint16 raw only")
_add("digital_input_status", 85, 1, "raw", width=1,
     note="Source explicitly R; format and bit meanings unspecified; uint16 raw only")
for index, name in enumerate(("import_active_energy_1", "export_active_energy_1", "inductive_reactive_energy_1",
                              "capacitive_reactive_energy_1", "import_active_energy_2", "export_active_energy_2",
                              "inductive_reactive_energy_2", "capacitive_reactive_energy_2")):
    _add(name, 86 + index * 4, 1, "Wh" if "active_energy" in name and "reactive" not in name else "varh", width=4,
         note="4 words from address stride; source says long int but range 0..FFFFFFFFFFFFFFFF; unsigned by range")

# Min/max and demand ranges are available for diagnostics; no setpoint/configuration writes.
for start, label in [(118, "min"), (164, "max")]:
    for index, phase in enumerate(range(1, 4)):
        _add(f"voltage_l{phase}_{label}", start + index * 2, .1, "V")
        _add(f"current_l{phase}_{label}", start + 12 + index * 2, .001, "A")
        _add(f"active_power_l{phase}_{label}", start + 18 + index * 2, .1, "W", True)
        _add(f"reactive_power_l{phase}_{label}", start + 24 + index * 2, .1, "var", True)
        _add(f"apparent_power_l{phase}_{label}", start + 30 + index * 2, .1, "VA")
    for offset, name, unit, signed in [(36, "active_power_import_total", "W", True),
                                     (38, "active_power_export_total", "W", True),
                                     (40, "reactive_power_import_total", "var", True),
                                     (42, "reactive_power_export_total", "var", True),
                                     (44, "apparent_power_total", "VA", False),
                                     (6, "voltage_l1_l2", "V", False),
                                     (8, "voltage_l2_l3", "V", False),
                                     (10, "voltage_l3_l1", "V", False)]:
        _add(f"{name}_{label}", start + offset, .1, unit, signed)
for phase in range(1, 4):
    delta = 2 * (phase - 1)
    _add(f"current_l{phase}_demand", 210 + delta, .001, "A")
    _add(f"active_power_l{phase}_import_demand", 216 + delta, .1, "W", True)
    _add(f"active_power_l{phase}_export_demand", 222 + delta, .1, "W", True)
    _add(f"reactive_power_l{phase}_import_demand", 228 + delta, .1, "var", True)
    _add(f"reactive_power_l{phase}_export_demand", 234 + delta, .1, "var", True)
    _add(f"apparent_power_l{phase}_demand", 240 + delta, .1, "VA")
for index, (name, unit) in enumerate((("active_power_import_total", "W"), ("active_power_export_total", "W"),
                                      ("reactive_power_import_total", "var"), ("reactive_power_export_total", "var"),
                                      ("apparent_power_total", "VA"))):
    _add(f"{name}_demand", 246 + index * 2, .1, unit, unit != "VA")


class MPR53CS:
    def __init__(self, word_order: str = "big"):
        if word_order not in ("big", "little"):
            raise ValueError("word_order must be big or little")
        self.word_order = word_order

    def decode(self, registers: Mapping[int, int], names=None) -> dict:
        measurements, quality = {}, {}
        for name in names or REGISTERS:
            spec = REGISTERS[name]
            try:
                measurements[name] = read_value(registers, spec, self.word_order)
                quality[name] = "good"
            except KeyError:
                measurements[name], quality[name] = None, "missing"
            except ValueError:
                measurements[name], quality[name] = None, "invalid"
        return {"measurements": measurements, "quality": quality, "mapping_source": "source_derived",
                "word_order": self.word_order, "word_order_verified": False,
                "ct_vt_applied_again": False}

    def poll(self, reader, unit_id: int = 1, timeout: float = 2.0) -> dict:
        """reader.read_registers performs ONLY FC03/04; default fast frame avoids address gaps."""
        sampled_at = datetime.now(timezone.utc).isoformat()
        names = [name for name, spec in REGISTERS.items() if spec.address <= 85]
        try:
            words = words_checked(reader.read_registers(unit_id, 0, 86, timeout=timeout), 86)
            result = self.decode(dict(enumerate(words)), names)
            result.update(communication_ok=True, timestamp=sampled_at)
        except (OSError, TimeoutError, ValueError) as exc:
            result = self.decode({}, names)
            result.update(communication_ok=False, timestamp=sampled_at, error=str(exc))
        return result
