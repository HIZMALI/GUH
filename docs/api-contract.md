# Shared API contract v1

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
Each panel is one Modbus unit ID, 1..247. Base0 health,1 risk,2 state (0normal1attention2warning3critical),3 alarm_active,4 thermal_alarm,5 pd_alarm,6 arc_event,7 communication_ok,8 sensor_health,9 schema_version=1,10..11 timestamp UNIX uint32 high/low. Bridge supports first247 panel IDs sorted numeric; API/fleet scales beyond, document multiple bridges needed for500. Unsupported register reads must return exception02, write FCs exception01. No coercing unsupported state to normal.

Agents may add fields/endpoints compatibly. Coordinate breaking changes before editing. Unit/e2e tests should consume this exact contract.
