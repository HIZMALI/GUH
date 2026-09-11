# Shared API contract — V1 compatibility and V2 extensions

JSON keys English, UI Turkish. All timestamps UTC ISO8601; synthetic source always visible. `/api` prefix. Frontend same-origin proxy. API bearer token from `POST /api/auth/login` `{username,password}` -> `{access_token,token_type,role,username}`; store token in sessionStorage only. `/health` unauthenticated; all `/api` except login require bearer. Service token from env accepted for simulator/bridge with restricted role.

## Telemetry
`POST /api/telemetry` accepts `{message_id,device_id,panel_id,timestamp,source:'generated_synthetic'|'organizer_synthetic_replay',scenario,measurements:{current_l1,current_l2,current_l3,current_neutral,voltage_l1,voltage_l2,voltage_l3,active_power_kw,reactive_power_kvar,apparent_power_kva,power_factor,frequency_hz,thd_current,thd_voltage,temperature_c,ambient_temperature_c,humidity_pct,pd_pulse_count,pd_peak,pd_rms,pd_activity_rate,pd_baseline_ratio,battery_pct},quality:{measurement_name:'good'|'missing'|'invalid'|'stuck'},arc:{event:boolean,detectors:string[],trip_relays:string[],timestamp:string|null,system_state:number,active_errors:number[],communication_ok:boolean},communication_ok:boolean}`. Measurements nullable; invalid range => quality failure visible (not healthy). Source per measurement is available in optional `provenance` dict. MQTT topic `gridsentinel/telemetry/{device_id}`, same payload. Device ID bound to configured key/allowlist; broker credentials generated at bootstrap.

## Read APIs
- `GET /api/fleet` -> `{panels:Panel[],summary:{total,normal,attention,warning,critical,fleet_health,open_alarms,offline},timestamp,mode:'synthetic_demo'}`.
- Panel `{id,name,region,substation,transformer,device_id,scenario,source,state,risk_score,health_score,communication_ok,last_seen,measurements,arc,explanation:{observed:string[],possible_cause:string,recommended_action:string,contributions:[{rule,points,detail}],data_quality:string[]}}`.
- `GET /api/panels/{id}` -> Panel plus `{history:[{timestamp,risk_score,health_score,state,measurements}],alarms:Alarm[],events:Event[]}` (history max120).
- `GET /api/alarms` -> `{items:Alarm[]}`. Alarm `{id,panel_id,panel_name,severity,title,message,status,created_at,acknowledged_at?,resolved_at?}`.
- `POST /api/alarms/{id}/acknowledge` operator/admin -> Alarm.
- `GET /api/notifications` -> `{items:[{id,alarm_id,panel_id,channel,recipient,status:'simulated',timestamp,message}]}`.
- `GET /api/events` -> `{items:[{id,panel_id,type,message,timestamp}]}`.
- `GET /api/audit` -> `{items:[...]}` admin.
- `GET /api/scenarios` -> `{items:[{id,name,description,duration_steps,expected_state}]}`.
- `POST /api/demo/scenario` operator/admin `{scenario,panel_id:'PNL-001'}` -> `{ok:true,...}`. Backend controls simulator shared selection via DB/API or MQTT; explain integration choices to root.
- `POST /api/demo/reset` admin: reset demo state explicitly; no physical device writes.
- `GET /api/scada/registers?panel_id=PNL-001` -> `{panel_id,host,port,unit_id,transport:'modbus_tcp',connected:boolean,registers:[{address,name,value,unit}],timestamp,error?}`. Must actually read bridge over TCP, not just echo database. Bridge polls fleet using service token; backend endpoint uses bridge master. Modbus library agent provides shared pure register encoder and TCP read client.
- `GET /api/metrics` -> ingestion counts/latency, DB write and MQTT connection counters for tests.

## GridSentinel SCADA map (PDU base0, uint16 read-only FC03/04)
Each panel has a bank-local Modbus unit ID, 1..247. Base0 health,1 risk,2 state (0normal1attention2warning3critical),3 alarm_active,4 thermal_alarm,5 pd_alarm,6 arc_event,7 communication_ok,8 sensor_health,9 schema_version=1,10..11 timestamp UNIX uint32 high/low. V2 serves all500 panels through three banks:1502/units1..247,1503/units1..247,1504/units1..6, in numeric panel order. `GET /api/scada/registers?panel_id=PNL-500` returns `bank:3,port:1504,unit_id:6,host:'scada',connected:true,transport:'modbus_tcp',registers:[...]` only after a real master read. Configurable bank size/base/count and capacity errors are in [the map](scada/register-map.md). Unsupported registers return exception02 and writes exception01. Invalid state is never coerced to NORMAL; pending current-run or stale observations close validity registers7/8 to0.

Agents may add fields/endpoints compatibly. Coordinate breaking changes before editing. Unit/e2e tests should consume this exact contract.

## V2 additive demo-run, focused timing and action contract

V1 field names, auth/RBAC, enums and legacy payload acceptance remain supported. No telemetry, alarm, event, notification or audit history is deleted. The additive startup migration records schema version 2, adds nullable run metadata to existing tables and creates run/time and unique run/step indexes. Existing v1 rows stay unassigned (`demo_run_id=null`, `scenario_revision=null`); their historical identity is never guessed.

### Wire identity and run selection

Telemetry optionally adds `scenario_revision:int>=1`, `demo_run_id:string` (`PNL-001-r2`), `demo_interval_seconds:positive number`, and `focused_demo:boolean`. The simulator supplies both identities. At least one explicit identity makes the payload run-bound: the revision/run ID and scenario must match the selected panel run or ingestion returns HTTP409. `simulation_step` must advance within an explicit run; a second message ID for the same run/step is rejected. Existing duplicate message IDs remain idempotent, including retries after a scenario change. Legacy frames without either identity are accepted as unassigned, excluded from current-run projections and analyzed separately from explicit runs. Their legacy scenario windows do not establish precise historical run boundaries.

Simulator `message_id` is stable across process restarts: `<demo_run_id>-s<simulation_step>`. A replay caused by an uncommitted MQTT/state-poll race therefore retains the same durable idempotency key. The database additionally enforces unique `(device_id,demo_run_id,simulation_step)` for explicit runs.

`POST /api/demo/scenario` accepts `{scenario,panel_id:'PNL-001',focus:true}`; `focus` defaults to true and `focused` is accepted as an alias. There is at most one focused panel. Response adds `scenario_revision`, `demo_run_id`, `focused_demo`, `pending_current_run:true`, and `scenario_started_at`. A scenario change/reset increments the persisted panel revision. Previously open synthetic alarms are retained and resolved with `resolution_reason:'demo_run_superseded'`, with event/audit records; this does not claim an equipment fault was physically cleared. Reset removes focus and preserves all records.

### Focus scheduler

`GET /api/demo/state` adds top-level `focus_panel_id`, `focus_interval_seconds`, `background_interval_seconds`, `max_fps`, `background_fps_budget`, and `timing_mode:'accelerated_synthetic'`. Each existing panel entry adds `scenario_revision`, `demo_run_id`, `focused_demo`, `last_step`, and `arc_event_timestamp`; `revision` and `started_at` remain. Accepted explicit progress persists independently of the displayed snapshot, so a simulator restart resumes at `last_step+1` within the same run.

`SIMULATOR_FOCUS_INTERVAL` / `--focus-interval` defaults to 1.5 seconds. The single focus panel reserves `1/focus_interval` frames/s from `SIMULATOR_MAX_FPS` (default50). At500panels, the499background panels receive49.3333frames/s and about10.1149seconds per panel. A shared monotonic publication gate also limits the total stream to50frames/s. Per-panel deadlines, staggered background starts and bounded sleeps prevent busy loops and catch-up bursts. The original no-focus pacing remains. These are synthetic scheduling assumptions, not real equipment sampling claims. Metrics add process counters `focused_frames`, `background_frames`, `legacy_frames`, and `run_rejected`.

### Panel and history projections

Panel responses add `scenario_revision`, `demo_run_id`, `scenario_started_at`, `demo_step`, `snapshot_demo_run_id`, `pending_current_run`, `focused_demo`, `focus_interval_seconds`, and `accelerated_demo:true`. **If `pending_current_run=true`, the UI must show “Bu çalışma için ölçüm bekleniyor” and must not present the old/legacy snapshot as the new run's current measurements, score or arc status.** Legacy raw fields remain for v1 compatibility; `actions` is empty until a current-run snapshot exists.

Panel detail adds:

- `current_run_history`, `full_history`: latest120records in ascending order. V1 `history` retains its full-scope meaning.
- `full_history_total`, `full_history_has_more`, `full_history_next_before_id`, `current_run_history_total`.
- `current_run_alarms`, `historical_alarms`, `current_run_events`, `full_events`. V1 `alarms` and `events` remain full-scope, latest100records.
- History records add `id`, `demo_run_id`, `scenario_revision`, `simulation_step`. Alarm/Event/Notification add nullable run identity; alarms add `is_current_run` and nullable `resolution_reason`.

`GET /api/panels/{id}/history?scope=all|current&before_id=<id>&limit=120` provides older measurements. `limit` is1–1000; response `{items,next_before_id,total,scope}` returns ascending items and a nullable cursor for older records. `GET /api/alarms` additionally accepts `scope=all|current`, `status=active|acknowledged|resolved`, and `severity=ATTENTION|WARNING|CRITICAL`; defaults preserve v1 scope.

### Structured early warning

`early_warning` is computed from persisted state-transition events belonging only to the current explicit run:

`{transitions:[{state,step,timestamp,risk_score}],warning_step:null|int,critical_step:null|int,lead_steps:null|int,status,unit:'synthetic_demo_steps',message}`.

Statuses are `pending`, `before_critical`, `demonstrated`, `critical_without_prior_warning`, and `no_critical`. Positive `lead_steps` exists only when an observed WARNING precedes CRITICAL in that run. The message is Turkish and identifies synthetic steps; it never claims real-field minutes/hours of predictive lead time. Transitions are retained independently of the120-point chart window.

### Central action policy

`services/anomaly_engine/actions.py` is the policy source used by result actions and mock notification channel selection. `GET /api/action-policy` returns the six trigger policies (`NORMAL`, `ATTENTION`, `WARNING`, `CRITICAL`, `ARC_EVENT`, `COMMUNICATION_LOSS`) for authenticated readers. Panel `actions` entries are `{type,trigger,automatic,status,channel,description,safety_boundary}`; descriptions and boundaries are Turkish. Statuses include `active`, `available`, `eligible` (policy template), `simulated` (new mock records), `deduplicated` (no repeated record), `recommended`, and `external`. A SCADA action marked available means the read-only output is available, not proof that an external client consumed it.

For v1 compatibility, ATTENTION also creates local simulated SMS/WhatsApp records. New/escalated alarms drive notification creation; repeated frames do not resend. ARC adds a durable audit record. Provider adapters cannot contact an external SMS/WhatsApp service. There is no breaker, protection trip/reset, TVOC reset or Modbus-write action.
### V2 bounded recovery behavior

PostgreSQL connection/pool waits default to3s, statement/socket to5s, SQL lock to2s; application write-lock waits at most3s before HTTP503. The MQTT consumer retains retry semantics without acknowledging a failed transaction. GET fleet/panel reads do not acquire the maintenance writer lock. The same risk/action policy projects stale observations as unavailable immediately; the maintenance tick persists the matching alarm/event transition. A read projection never claims a mock notification was already emitted. `DB_*_TIMEOUT_*` and `WRITE_LOCK_TIMEOUT_SECONDS` are documented in `.env.example`; Compose also bounds API resolver attempts.

Metrics now include `http_requests`, `http_request_ms_total`, `http_request_ms_max` and `write_lock_timeouts`, scoped to the current API process. Sanitized slow-route logs contain method/path/status/duration, never bearer tokens or query credentials. The final real DB recovery test also measures the first panel read after health recovers; it must complete within8s and preserve the last observation.
