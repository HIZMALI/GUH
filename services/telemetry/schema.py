"""Strict wire contract. Missing and impossible measurements never become zeros."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

CHANNELS = {
    'current_l1': (0, 10000), 'current_l2': (0, 10000), 'current_l3': (0, 10000),
    'current_neutral': (0, 10000), 'voltage_l1': (0, 1000), 'voltage_l2': (0, 1000),
    'voltage_l3': (0, 1000), 'active_power_kw': (-20000, 20000),
    'reactive_power_kvar': (-20000, 20000), 'apparent_power_kva': (0, 30000),
    'power_factor': (-1, 1), 'frequency_hz': (0, 100), 'thd_current': (0, 500),
    'thd_voltage': (0, 500), 'temperature_c': (-50, 200),
    'ambient_temperature_c': (-50, 100), 'humidity_pct': (0, 100),
    'pd_pulse_count': (0, 10000000), 'pd_peak': (0, 1000000), 'pd_rms': (0, 1000000),
    'pd_activity_rate': (0, 1000000), 'pd_baseline_ratio': (0, 10000), 'battery_pct': (0, 100),
}
Source = Literal['generated_synthetic', 'organizer_synthetic_replay']
Quality = Literal['good', 'missing', 'invalid', 'stuck']

class Arc(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event: bool = False
    detectors: list[str] = Field(default_factory=list, max_length=30)
    trip_relays: list[str] = Field(default_factory=list, max_length=3)
    timestamp: datetime | None = None
    system_state: int = Field(default=0, ge=0, le=65535)
    active_errors: list[int] = Field(default_factory=list, max_length=32)
    communication_ok: bool = True

    @field_validator('timestamp')
    @classmethod
    def utc_timestamp(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError('timezone-aware UTC timestamp required')
        return value.astimezone(timezone.utc) if value else value

class TelemetryFrame(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    message_id: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.:-]+$')
    device_id: str = Field(pattern=r'^EDGE-[0-9]{3,6}$')
    panel_id: str = Field(pattern=r'^PNL-[0-9]{3,6}$')
    timestamp: datetime
    source: Source = 'generated_synthetic'
    scenario: str = Field(default='normal_operation', max_length=64)
    measurements: dict[str, float | None] = Field(max_length=len(CHANNELS))
    quality: dict[str, Quality] = Field(default_factory=dict, max_length=len(CHANNELS))
    provenance: dict[str, Source] = Field(default_factory=dict, max_length=len(CHANNELS))
    arc: Arc = Field(default_factory=Arc)
    communication_ok: bool = True
    device_key: str | None = Field(default=None, max_length=128)
    source_row: int | None = Field(default=None, ge=7, le=158)
    replay_offset_seconds: int | None = Field(default=None, ge=0)
    simulation_step: int = Field(default=0, ge=0, le=1000000000)
    accelerated: bool = True

    @field_validator('timestamp')
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('timezone-aware timestamp required')
        return value.astimezone(timezone.utc)

    @field_validator('measurements', 'quality', 'provenance')
    @classmethod
    def known_channels(cls, value):
        unknown = set(value) - set(CHANNELS)
        if unknown:
            raise ValueError(f'unknown channels: {sorted(unknown)}')
        return value

def normalize_quality(frame: TelemetryFrame) -> tuple[dict, dict]:
    values, quality = {}, {}
    for name, (low, high) in CHANNELS.items():
        value = frame.measurements.get(name)
        q = frame.quality.get(name, 'good')
        if value is None:
            q = 'missing'
        elif not low <= value <= high:
            q = 'invalid'
        values[name] = value
        quality[name] = q
    return values, quality
