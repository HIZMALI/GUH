export type Severity = "NORMAL" | "ATTENTION" | "WARNING" | "CRITICAL";
export type Session = {
  access_token: string;
  role: "viewer" | "operator" | "admin";
  username: string;
};
export type Measurements = Record<string, number | null>;
export type Alarm = {
  id: string;
  panel_id: string;
  panel_name: string;
  severity: Severity;
  title: string;
  message: string;
  status: "active" | "acknowledged" | "resolved";
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
};
export type Event = {
  id: string;
  panel_id: string;
  type: string;
  message: string;
  timestamp: string;
};
export type History = {
  timestamp: string;
  risk_score: number;
  health_score: number;
  state: Severity;
  measurements: Measurements;
  quality?: Record<string, string>;
  communication_ok?: boolean;
};
export type Panel = {
  id: string;
  name: string;
  region: string;
  substation: string;
  transformer: string;
  device_id: string;
  scenario: string;
  telemetry_scenario?: string;
  source: string;
  state: Severity;
  risk_score: number;
  health_score: number;
  communication_ok: boolean;
  last_seen: string;
  measurements: Measurements;
  quality?: Record<string, string>;
  provenance?: Record<string, string>;
  arc: {
    event: boolean;
    detectors: string[];
    trip_relays: string[];
    timestamp: string | null;
    system_state: number;
    active_errors: number[];
    communication_ok: boolean;
  };
  explanation: {
    observed: string[];
    possible_cause: string;
    recommended_action: string;
    contributions: { rule: string; points: number; detail: string }[];
    data_quality: string[];
  };
  history?: History[];
  alarms?: Alarm[];
  events?: Event[];
};
export type Fleet = {
  panels: Panel[];
  summary: {
    total: number;
    normal: number;
    attention: number;
    warning: number;
    critical: number;
    fleet_health: number;
    open_alarms: number;
    offline: number;
  };
  timestamp: string;
  mode: string;
};
export type Notification = {
  id: string;
  alarm_id: string;
  panel_id: string;
  channel: string;
  recipient: string;
  status: "simulated";
  timestamp: string;
  message: string;
};
export type Scenario = {
  id: string;
  name: string;
  description: string;
  duration_steps: number;
  expected_state: Severity;
};
export type Registers = {
  panel_id: string;
  host: string;
  port: number;
  unit_id: number;
  transport: string;
  connected: boolean;
  registers: {
    address: number;
    name: string;
    value: number | null;
    unit: string;
  }[];
  timestamp: string;
  error?: string;
};
