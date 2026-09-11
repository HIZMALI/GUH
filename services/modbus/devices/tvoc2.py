"""ABB TVOC-2-COM Rev D read-only monitoring; protection remains in ABB equipment."""
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Mapping

from .common import Register, words_checked

SOURCE = "1SFC170017M0201_Rev_D_TVOC-2_Modbus_Manual.pdf"
REGISTERS: dict[str, Register] = {}


def _add(name, address, page, unit="raw", note=""):
    REGISTERS[name] = Register(name, address, 1, 1, False, unit, SOURCE, page, note=note)


for trip in range(1, 8):
    for offset, field in enumerate(("detector_low", "detector_high", "relay", "date", "time_hhmm", "time_ss")):
        _add(f"trip_{trip}_{field}", 100 + (trip - 1) * 7 + offset, 21 if trip <= 6 else 22,
             note="0xFFFF when unused; register gap every 7 words must not be read")
_add("number_of_trips", 149, 22)
for offset, field in enumerate(("error_date", "error_time_hhmm", "error_time_ss", "dtc_2_1", "dtc_4_3",
                                "dtc_6_5", "trip", "trip_date", "trip_time_hhmm", "trip_time_ss",
                                "detector_low", "detector_high", "relay")):
    _add(f"diagnostics_{field}", 200 + offset, 22)
for name, address in (("last_diagnostics_date", 220), ("last_diagnostics_time_hhmm", 221),
                      ("sensor_status_x2", 222), ("sensor_status_x3", 223),
                      ("ambient_light_warning_x2", 224), ("ambient_light_warning_x3", 225)):
    _add(name, address, 22, note="firmware >=03.00.00" if address >= 222 else "")
for index in range(1, 10):
    for offset, field in enumerate(("date", "time_hhmm", "time_ss", "dtc_2_1", "dtc_4_3", "dtc_6_5")):
        _add(f"error_{index}_{field}", 300 + (index - 1) * 7 + offset, 22 if index <= 3 else 23,
             note="entries7..9 only firmware<03.00.00" if index >= 7 else "0xFFFF when unused")
_add("number_of_errors", 368, 23)
for index in range(1, 7):
    for offset, name in enumerate(("sensor_status_x2", "sensor_status_x3", "ambient_light_warning_x2", "ambient_light_warning_x3")):
        _add(f"error_{index}_{name}", 370 + (index - 1) * 4 + offset, 23 if index == 1 else 24,
             note="firmware>=03.00.00")
for name, address, page in (("installed_modules", 500, 24), ("dip_switches", 600, 24),
                            ("firmware_xxyy", 800, 24), ("firmware_zz", 801, 24),
                            ("modbus_failure_register", 1200, 26), ("system_state", 1300, 26)):
    _add(name, address, page)
for index in range(1, 7):
    _add(f"active_dtc_{index}", 1300 + index, 26, note="one DTC byte in low byte, not separate fault IDs")


def decode_detectors(low: int, high: int) -> list[str]:
    words_checked([low, high])
    return ([f"X1:{bit + 1}" for bit in range(10) if low & (1 << bit)]
            + [f"X2:{bit - 9}" for bit in range(10, 15) if low & (1 << bit)]
            + [f"X2:{bit + 6}" for bit in range(5) if high & (1 << bit)]
            + [f"X3:{bit - 4}" for bit in range(5, 15) if high & (1 << bit)])


def decode_relays(word: int) -> list[str]:
    words_checked([word])
    return [f"K{bit + 4}" for bit in range(3) if word & (1 << bit)]


def decode_timestamp(days: int, hhmm: int, seconds: int, device_timezone: tzinfo = timezone.utc) -> str:
    """Manual defines date/time format, not zone. Device zone must be commissioned separately."""
    words_checked([days, hhmm, seconds])
    hour, minute = hhmm >> 8, hhmm & 0xFF
    if days == 0xFFFF or hour > 23 or minute > 59 or seconds > 59:
        raise ValueError("Invalid or unused TVOC device timestamp")
    if device_timezone is None:
        raise ValueError("Device timezone required")
    value = datetime(1970, 1, 1, tzinfo=device_timezone) + timedelta(days=days, hours=hour, minutes=minute, seconds=seconds)
    return value.astimezone(timezone.utc).isoformat()


def decode_trip(words, device_timezone: tzinfo = timezone.utc) -> dict:
    values = words_checked(words, 6)
    if all(word == 0xFFFF for word in values):
        return {"present": False, "quality": "missing", "detectors": [], "trip_relays": [], "timestamp": None}
    if any(word == 0xFFFF for word in values):
        return {"present": None, "quality": "invalid", "detectors": [], "trip_relays": [], "timestamp": None}
    try:
        timestamp = decode_timestamp(*values[3:], device_timezone)
    except ValueError:
        return {"present": None, "quality": "invalid", "detectors": [], "trip_relays": [], "timestamp": None}
    return {"present": True, "quality": "good", "detectors": decode_detectors(*values[:2]),
            "trip_relays": decode_relays(values[2]), "timestamp": timestamp,
            "unused_bits_set": bool(values[0] & 0x8000 or values[1] & 0x8000 or values[2] & 0xFFF8)}


def decode_firmware(words) -> tuple[int, int, int]:
    first, last = words_checked(words, 2)
    return first >> 8, first & 0xFF, last & 0xFF


def decode_dtc(words) -> list[int]:
    """Return n1..n6. HMI text reverses that list, n6-n5-...-n1."""
    return [byte for word in words_checked(words, 3) for byte in (word & 0xFF, word >> 8)]


def decode_system_state(word: int) -> dict:
    words_checked([word])
    return {"active_trip": bool(word & 1), "active_error": bool(word & 2),
            "startup": bool(word & 4), "diagnostics_running": bool(word & 8),
            "reserved_bits": word & 0xFFF0}


class TVOC2:
    def __init__(self, device_timezone: tzinfo = timezone.utc):
        self.device_timezone = device_timezone

    def decode(self, registers: Mapping[int, int]) -> dict:
        output = {"mapping_source": "source_derived", "timestamp_timezone_assumption": str(self.device_timezone),
                  "event": None, "system_state": None, "active_errors": [], "sensor_status": None,
                  "ambient_light_warning": None, "quality": {}, "diagnostics": None}
        try:
            state = words_checked([registers[1300]])[0]
            state_info = decode_system_state(state)
            output.update(system_state=state, state=state_info, event=state_info["active_trip"])
            output["quality"]["system_state"] = "good"
        except (KeyError, ValueError):
            state_info = None
            output["quality"]["system_state"] = "missing" if 1300 not in registers else "invalid"
        try:
            firmware = decode_firmware([registers[800], registers[801]])
            output["firmware"] = ".".join(f"{v:02d}" for v in firmware)
        except (KeyError, ValueError):
            firmware = None
            output["firmware"] = None
        try:
            trip = decode_trip([registers[a] for a in range(100, 106)], self.device_timezone)
        except (KeyError, ValueError):
            trip = {"present": None, "quality": "missing" if any(a not in registers for a in range(100, 106)) else "invalid",
                    "detectors": [], "trip_relays": [], "timestamp": None}
        output["latest_trip"] = trip
        output.update({key: trip[key] for key in ("detectors", "trip_relays", "timestamp")})
        output["quality"]["trip"] = trip["quality"]
        try:
            errors = words_checked([registers[a] for a in range(1301, 1307)])
            if any(word > 255 for word in errors):
                raise ValueError("DTC must fit low byte")
            output["active_errors"] = errors if state_info and state_info["active_error"] else []
            output["active_dtc_hmi"] = "-".join(str(v) for v in reversed(errors))
            output["quality"]["active_errors"] = "good"
        except (KeyError, ValueError):
            output["quality"]["active_errors"] = "missing" if any(a not in registers for a in range(1301, 1307)) else "invalid"
        try:
            diagnostics = words_checked([registers[a] for a in range(200, 213)], 13)
            output["diagnostics"] = {"raw": diagnostics, "dtc": decode_dtc(diagnostics[3:6]),
                                     "active_trip_indicator": diagnostics[6],
                                     "detectors": decode_detectors(diagnostics[10], diagnostics[11]),
                                     "trip_relays": decode_relays(diagnostics[12]),
                                     "error_timestamp": decode_timestamp(*diagnostics[:3], self.device_timezone) if state_info and state_info["active_error"] else None,
                                     "trip_timestamp": decode_timestamp(*diagnostics[7:10], self.device_timezone) if state_info and state_info["active_trip"] else None}
            output["quality"]["diagnostics"] = "good"
        except (KeyError, ValueError):
            output["quality"]["diagnostics"] = "missing" if any(a not in registers for a in range(200, 213)) else "invalid"
        # Source p27: zero blocks can mean no active error, NOT ten failed detectors.
        if firmware is None or firmware < (3, 0, 0):
            output["quality"]["sensor_status"] = "unsupported_firmware" if firmware else "firmware_unknown"
        elif state_info is None:
            output["quality"]["sensor_status"] = "missing_state_context"
        elif not state_info["active_error"]:
            output["quality"]["sensor_status"] = "no_active_error"
        else:
            try:
                values = words_checked([registers[a] for a in range(222, 226)], 4)
                modules = words_checked([registers[500]])[0]
                output["sensor_status"], output["ambient_light_warning"] = {}, {}
                for index, extension in enumerate(("X2", "X3")):
                    if modules & (1 << (index + 2)):
                        output["sensor_status"][extension] = {f"{extension}:{bit + 1}": "ok" if values[index] & (1 << bit) else "error" for bit in range(10)}
                        output["ambient_light_warning"][extension] = {f"{extension}:{bit + 1}": "ok" if values[index + 2] & (1 << bit) else "warning" for bit in range(10)}
                output["quality"]["sensor_status"] = "good"
            except (KeyError, ValueError):
                output["quality"]["sensor_status"] = "missing_or_invalid"
        for name, address in (("number_of_trips", 149), ("number_of_errors", 368), ("installed_modules", 500),
                              ("dip_switches", 600), ("modbus_failure_register", 1200)):
            try:
                output[name] = words_checked([registers[address]])[0]
            except (KeyError, ValueError):
                output[name] = None
        return output

    def poll(self, reader, unit_id=1, timeout=2.0) -> dict:
        registers, errors = {}, []
        def read(address, count):
            try:
                values = words_checked(reader.read_registers(unit_id, address, count, timeout=timeout), count)
                registers.update({address + offset: word for offset, word in enumerate(values)})
            except (OSError, TimeoutError, ValueError) as exc:
                errors.append({"address": address, "error": str(exc)})
        read(800, 2)  # Version MUST precede optional range.
        for address, count in ((1300, 7), (100, 6), (149, 1), (200, 13), (220, 2),
                               (368, 1), (500, 1), (600, 1), (1200, 1)):
            read(address, count)
        if 800 in registers and 801 in registers and decode_firmware([registers[800], registers[801]]) >= (3, 0, 0):
            read(222, 4)
        result = self.decode(registers)
        result.update(communication_ok=not errors, polling_errors=errors,
                      polled_at=datetime.now(timezone.utc).isoformat())
        return result
