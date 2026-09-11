# Edge Gateway integration seam

Runnable center demo uses synthetic simulator→MQTT→API; no physical gateway is commissioned. Vendor decoders and read-only TCP-to-RTU transport are implemented in `services/modbus`. This directory describes the field gateway seam, not certified firmware.

`ReadOnlyTCPGateway(host,port,function=3)` has only `read_registers`; MPR/TVOC polling accepts this interface with bounded timeout. It speaks ordinary Modbus TCP to an approved local gateway that routes unit IDs to RS485 RTU devices. **MPR/TVOC themselves are RTU devices in the supplied sources**. Native serial-port/RTU framing and serial discovery are not implemented here. A future serial adapter must satisfy the same read-only interface, wire settings, single-master ownership and commissioning controls.

```python
from services.modbus.devices.mpr53cs import MPR53CS
from services.modbus.devices.tvoc2 import TVOC2
from services.modbus.transport import ReadOnlyTCPGateway
from datetime import timezone

# Placeholder requires authorized local endpoint and verified unit/wire configuration.
# transport = ReadOnlyTCPGateway(approved_local_gateway, 502)
# electrical = MPR53CS(word_order=verified_word_order).poll(transport, unit_id=1, timeout=2)
# arc = TVOC2(device_timezone=commissioned_timezone).poll(transport, unit_id=2, timeout=2)
```

No endpoint is auto-scanned or polled by importing these modules. Source register metadata is `source_derived`; measurements produced by an actual future device call require separate observed-data provenance and commissioning checks. Do not relabel them organizer replay or generated synthetic. The current API intentionally accepts only the two synthetic demo sources; enabling live data ingestion is outside this demo and requires explicit schema/security/commissioning work.

Normalization requirements: timezone-aware observed/received timestamps; immutable message ID and device identity; per-channel value+quality+provenance; cached value never presented as fresh; MPR CT/VT not applied twice; W/kW conversions explicit; ABB historical trips separate from current state; ABB communication health separate from electrical meter health. Restart/out-of-order processing must preserve message identities. Backend handles durable deduplication and quality in the running demo.
