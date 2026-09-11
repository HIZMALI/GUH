export const componentKeys = [
  "gateway",
  "isolated_interfaces",
  "sensors",
  "installation",
  "commissioning",
  "planned_outage",
  "optional_pd",
  "shared_server",
  "maintenance_annual",
  "battery_annual",
] as const;
export type ComponentKey = (typeof componentKeys)[number];
export type TcoInput = Record<ComponentKey | string, string>;
export function parseCost(value: string | undefined): number | null {
  if (value === undefined || value.trim() === "") return null;
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}
export function calculateTco(input: TcoInput) {
  const count = parseCost(input.panel_count),
    years = parseCost(input.period_years);
  const costs = Object.fromEntries(
    componentKeys.map((key) => [key, parseCost(input[key])]),
  ) as Record<ComponentKey, number | null>;
  const missing = componentKeys.filter((key) => costs[key] === null);
  if (
    count === null ||
    !Number.isInteger(count) ||
    count < 1 ||
    years === null ||
    years <= 0 ||
    missing.length ||
    !input.currency?.trim()
  )
    return { ready: false as const, missing };
  const c = costs as Record<ComponentKey, number>;
  const perPanelInitial =
    c.gateway +
    c.isolated_interfaces +
    c.sensors +
    c.installation +
    c.commissioning +
    c.planned_outage +
    c.optional_pd +
    c.shared_server / count;
  const perPanelAnnual = c.maintenance_annual + c.battery_annual;
  const perPanelTotal = perPanelInitial + years * perPanelAnnual;
  const fleetTotal = count * perPanelTotal;
  if (
    ![perPanelInitial, perPanelAnnual, perPanelTotal, fleetTotal].every(
      Number.isFinite,
    )
  )
    return { ready: false as const, missing };
  const benefitKeys = [
    "outage_hour_cost",
    "maintenance_visit_cost",
    "avoided_hours",
    "avoided_visits",
  ] as const;
  const b = benefitKeys.map((key) => parseCost(input[key]));
  const annualGross = b.every((value) => value !== null)
    ? b[0]! * b[2]! + b[1]! * b[3]!
    : null;
  const annualNet =
    annualGross === null || !Number.isFinite(annualGross)
      ? null
      : annualGross - perPanelAnnual;
  const paybackYears =
    annualNet !== null && annualNet > 0 ? perPanelInitial / annualNet : null;
  return {
    ready: true as const,
    perPanelInitial,
    perPanelAnnual,
    perPanelTotal,
    fleetTotal,
    annualGross,
    annualNet,
    paybackYears,
    years,
    count,
  };
}
