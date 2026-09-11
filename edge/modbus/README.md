# Read-only device integration

Implementation: `services/modbus/devices/mpr53cs.py`, `tvoc2.py`, common typed register metadata and `services/modbus/transport.py`. Maps are documented in `docs/modbus`. FC03/04-only transport has no generic raw/write request method. Modbus device identity and endpoint must be provisioned; no auto-discovery on an OT network.

Testing from the repository root works on Windows and Linux:

```text
python -m unittest discover -s tests/modbus -v
```

Tests use independent supplied-source vectors and localhost fake peers. The separate GridSentinel SCADA server is not a vendor-device emulator: its unit register0..11 is the invented demo output map. Production gateway RTU validation (wiring, timeout strategy, poll load, actual word order, firmware, calibration/timezone) remains unverified.
