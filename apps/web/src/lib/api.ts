import type { Measurements } from "./types";
export function measuredValue(
  record: {
    measurements: Measurements;
    quality?: Record<string, string>;
    communication_ok?: boolean;
  },
  key: string,
): number | null {
  const quality = record.quality?.[key];
  if (record.communication_ok === false || (quality && quality !== "good"))
    return null;
  const value = record.measurements[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
export function qualityLabel(
  record: { quality?: Record<string, string>; communication_ok?: boolean },
  key: string,
) {
  if (record.communication_ok === false) return "İletişim yok / güncel değil";
  const labels: Record<string, string> = {
    missing: "Eksik veri",
    invalid: "Geçersiz veri",
    stuck: "Sensör sabit kaldı",
    stale: "Güncel değil",
    good: "Sentetik",
  };
  return (
    labels[record.quality?.[key] || "good"] ||
    `Kalite: ${record.quality?.[key]}`
  );
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  token?: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    signal: options.signal || AbortSignal.timeout(18000),
  });
  const result = await response
    .json()
    .catch(() => ({ detail: "API yanıtı okunamadı" }));
  if (!response.ok)
    throw new ApiError(
      typeof result.detail === "string"
        ? result.detail
        : `İstek tamamlanamadı (${response.status})`,
      response.status,
    );
  return result;
}
export const number = (value: number | null | undefined, digits = 0) =>
  value === null || value === undefined || !Number.isFinite(value)
    ? "—"
    : value.toLocaleString("tr-TR", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      });
export const time = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    : "Veri yok";
export const dateTime = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleString("tr-TR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    : "Veri yok";
