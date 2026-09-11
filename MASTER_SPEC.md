# GridSentinel · master specification

## Objective and boundaries
Build an on-premise, demonstrable early-warning platform for Grid Up Hackathon's panel/cell anomaly challenge. Combine existing MPR-53CS and ABB TVOC-2-COM monitoring with proposed retrofit environmental sensors and derived PD features. No field installation, real SCADA connection, certified hardware claim or breaker control. All demonstrations are synthetic.

## Source baseline
See docs/source-analysis.md and data/source/manifest.json. The workbook contains 152 synthetic L1 current samples at 15-minute offsets (90–540 A, median 297 A), not a complete multisensor dataset. L2/L3, voltage, thermal, environmental and PD/arc streams must be explicit generated channels. Replay preserves original relative timing and source row; accelerated demo clocks are labeled.

Panel: TEDAŞ EK-II/14 indoor 1250–1600 kVA drawing, width 1600 mm (+100/-0), height 1500 (+100/-0), depth 450 (+50/-0). Upper incoming conductors/CTs, middle outgoing DSYA bank, right metering/auxiliaries, bottom cable space >=400 mm. Added sensor placement is a proposal, not original installed equipment. Panel main bus rating 2312 A per specification; workbook example sensor ratio is not main incomer rating.

## Runtime
- Next.js/TypeScript at localhost:3000; same-origin /api proxy to FastAPI:8000.
- Python 3.12 container, PostgreSQL 16 durable telemetry/risk/alarms/audit/notification/device identity; SQLite permitted solely for isolated tests/local fallback, explicitly labeled.
- Mosquitto 2 MQTT authenticated internal broker. Simulator -> MQTT -> subscriber -> ingestion/risk -> DB -> API/dashboard.
- Separate read-only Modbus TCP bridge at port 1502, real TCP master verification; emits locally invented GridSentinel register map, never confused with ABB/MPR maps.
- Compose services db, mqtt, api, web, simulator, scada. Local only, expose UI/API on loopback; other network listeners restricted to Compose networks.
- One bootstrap/demo command creates random .env secrets and runs Compose. No Redis/ML required for prototype; explainable rules + trends are the useful core.

## Core behavior
Telemetry identity, timezone-aware timestamp, message ID, measurements, per-channel quality/provenance and Arc Guard event metadata. Ingestion deduplicates across restarts and rejects or quarantines out-of-order frames. Persistence and analytics are consistent; stale timeout never looks healthy. Missing/impossible/stuck sensors and independent Arc Guard communication are visible.

Risk score 0–100 and independent health 0–100; NORMAL <20, ATTENTION 20–44, WARNING 45–79, CRITICAL >=80. Arc event immediately CRITICAL; data faults generate availability alerts and reduce confidence. Explanations expose observed values, rules, possible cause, recommended action, assumptions. Use deterministic rule contributions and moving/trend statistics, not an accuracy claim. Alarm lifecycle active -> acknowledged -> resolved, deduplicated notification on new/escalated events; mock status explicitly simulated.

## Demo scenarios
normal_operation, gradual_overload, thermal_hotspot, high_humidity, loose_connection_signature, pd_degradation, combined_thermal_pd, arc_event, sensor_failure, communication_loss. Each has timeline, changed channels and expected outcome in data/scenarios. Combined scenario starts near risk 8/health96 and advances through attention/warning; severe late stage may reach critical; arc separately demonstrates certified-device event metadata. Demo can run accelerated or replay organizer L1 samples.

## UI
Industrial operations desk with dark graphite/navy, cool cyan accents and severity amber/red, readable typography, restrained motion. Fleet summary, hierarchy/filter/search, ranked panels, event feed. Panel detail with schematic based on original geometry, clickable monitoring points, current/electrical/thermal/PD charts, risk explanation, live alarms and event history. Separate SCADA register/master, notifications, source/architecture surfaces. Never display fabricated real-world installation locations as real assets; fleet sites are simulated.

## Security and validation
Env-provided user passwords/tokens, PBKDF2 or equivalent password hashing, secure session or bearer auth, RBAC, audit trail, input validation, device key binding, bounded requests/rate limiting. Network segmentation and TLS deployment recommendations. Notification mock is default; SMS/WhatsApp adapters must not transmit without explicit authorization.

Acceptance: Docker stack healthy, all 10 scenarios work, source-based device decoders tested, actual Modbus TCP roundtrip, dashboard browser E2E, auth/validation/failure tests, 100/250/500-panel load records with throughput/API/DB/alarms/MQTT metrics, restart tests and documentation. Mark unavailable environment checks as unverified; do not claim full completion until actual acceptance evidence exists.
