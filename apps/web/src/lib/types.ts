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
  demo_run_id?: string | null;
  scenario_revision?: number | null;
  is_current_run?: boolean;
};
export type Event = {
  id: string;
  panel_id: string;
  type: string;
  message: string;
  timestamp: string;
  demo_run_id?: string | null;
  scenario_revision?: number | null;
};
export type History = {
  id?: number;
  demo_run_id?: string | null;
  scenario_revision?: number | null;
  simulation_step?: number;
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
  scenario_revision?: number;
  demo_run_id?: string;
  scenario_started_at?: string;
  demo_step?: number | null;
  pending_current_run?: boolean;
  snapshot_demo_run_id?: string | null;
  focused_demo?: boolean;
  focus_interval_seconds?: number;
  accelerated_demo?: boolean;
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
  current_run_history?: History[];
  full_history?: History[];
  full_history_total?: number;
  full_history_has_more?: boolean;
  current_run_alarms?: Alarm[];
  historical_alarms?: Alarm[];
  current_run_events?: Event[];
  full_events?: Event[];
  early_warning?: EarlyWarning;
  actions?: Action[];
};
export type EarlyWarning = {
  transitions: {
    state: Severity;
    step: number;
    timestamp: string;
    risk_score: number;
  }[];
  warning_step: number | null;
  critical_step: number | null;
  lead_steps: number | null;
  status:
    | "pending"
    | "before_critical"
    | "demonstrated"
    | "critical_without_prior_warning"
    | "no_critical";
  unit: "synthetic_demo_steps";
  message: string;
};
export type Action = {
  type: string;
  trigger: string;
  automatic: boolean;
  status: string;
  channel: string | null;
  description: string;
  safety_boundary: string;
};
export type HistoryPage = {
  items: History[];
  next_before_id: number | null;
  total: number;
  scope: string;
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
  demo_run_id?: string | null;
  scenario_revision?: number | null;
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
  bank?: number;
  bank_size?: number;
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
