import math
import re
import threading
import time
from datetime import datetime, timezone

UNKNOWN = 0xFFFF
REGISTER_MAP = (
    (0, "health_score", "score"), (1, "risk_score", "score"),
    (2, "state", "enum"), (3, "alarm_active", "bool"),
    (4, "thermal_alarm", "bool"), (5, "pd_alarm", "bool"),
    (6, "arc_event", "bool"), (7, "communication_ok", "bool"),
    (8, "sensor_health", "score"), (9, "schema_version", "version"),
    (10, "timestamp_high", "unix_s_high"), (11, "timestamp_low", "unix_s_low"),
)
STATE_CODES = {"NORMAL": 0, "ATTENTION": 1, "WARNING": 2, "CRITICAL": 3}


def panel_sort_key(panel):
    identifier = str(panel["id"])
    suffix = re.search(r"(\d+)$", identifier)
    return (int(suffix.group(1)) if suffix else 2**63, identifier)


def panel_unit_mapping(panels):
    ordered = sorted(panels, key=panel_sort_key)
    identifiers = [str(panel["id"]) for panel in ordered]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate panel IDs in fleet")
    return {identifier: index + 1 for index, identifier in enumerate(identifiers[:247])}


def _score(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        return UNKNOWN
    return int(round(value))


def _flag(value):
    return int(value) if isinstance(value, bool) else UNKNOWN


def encode_panel(panel, *, stale=False):
    state = STATE_CODES.get(str(panel.get("state", "")).upper(), UNKNOWN)
    explanation = panel.get("explanation") or {}
    contributions = [item for item in explanation.get("contributions", []) if isinstance(item, dict)]
    rules = {str(item.get("rule", "")).lower() for item in contributions
             if isinstance(item.get("points"), (int, float)) and item["points"] > 0}
    # Match the backend explanation rule names; no independent protection thresholds here.
    thermal = any("thermal" in rule or "temperature" in rule or "hotspot" in rule for rule in rules)
    pd_alarm = any("pd" in rule or "discharge" in rule for rule in rules)
    quality = explanation.get("data_quality")
    sensor_health = panel.get("sensor_health")
    if sensor_health is None:
        # This deliberately coarse schema1 indicator is not the overall condition health.
        sensor_health = 100 if quality == [] else (0 if quality else None)
    timestamp = panel.get("last_seen")
    try:
        when = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("Naive timestamp")
        seconds = int(when.astimezone(timezone.utc).timestamp())
        if not 0 <= seconds < 2**32:
            raise ValueError("Timestamp outside uint32")
        clock_words = [seconds >> 16, seconds & 0xFFFF]
    except (ValueError, TypeError, OverflowError):
        clock_words = [UNKNOWN, UNKNOWN]
    active = panel.get("alarm_active")
    if active is None:
        active = state != 0 if state != UNKNOWN else None
    communication = panel.get("communication_ok")
    if stale or communication is False:
        communication, sensor_health = False, 0
    arc = panel.get("arc") or {}
    return [_score(panel.get("health_score")), _score(panel.get("risk_score")), state,
            _flag(active), _flag(panel.get("thermal_alarm", thermal)), _flag(panel.get("pd_alarm", pd_alarm)),
            _flag(arc.get("event")), _flag(communication), _score(sensor_health), 1, *clock_words]


class RegisterCache:
    """Replace a whole snapshot atomically; stale data stays visibly unavailable."""
    def __init__(self, stale_seconds=15.0):
        if stale_seconds <= 0:
            raise ValueError("stale_seconds must be positive")
        self.stale_seconds = stale_seconds
        self._lock = threading.Lock()
        self._units = {}
        self._updated_at = None
        self._failed = False
        self.last_error = None

    def update(self, panels):
        mapping = panel_unit_mapping(panels)
        units = {mapping[panel["id"]]: encode_panel(panel) for panel in panels if panel["id"] in mapping}
        with self._lock:
            self._units, self._updated_at, self._failed, self.last_error = units, time.monotonic(), False, None

    def mark_failed(self, error):
        with self._lock:
            self._failed, self.last_error = True, str(error)

    def read(self, unit_id, address, count):
        with self._lock:
            if unit_id not in self._units or address < 0 or count < 1 or address + count > len(REGISTER_MAP):
                raise KeyError("Unsupported unit or register range")
            values = list(self._units[unit_id])
            stale = self._failed or self._updated_at is None or time.monotonic() - self._updated_at > self.stale_seconds
            if stale:
                values[7], values[8] = 0, 0
            return values[address:address + count]
