"use client";
import { useId } from "react";
import { measuredValue, number, time } from "@/lib/api";
import type { History } from "@/lib/types";
export function TrendChart({
  history,
  channels,
  title,
  unit,
}: {
  history: History[];
  channels: { key: string; label: string; color: string }[];
  title: string;
  unit: string;
}) {
  const id = useId().replace(/:/g, "");
  const values = history
    .flatMap((h) =>
      channels.map((c) =>
        c.key === "risk_score" ? h.risk_score : measuredValue(h, c.key),
      ),
    )
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!history.length || !values.length)
    return (
      <div className="trend-card">
        <div className="card-heading">
          <h3>{title}</h3>
          <span>{unit}</span>
        </div>
        <div className="empty-chart">
          Trend için geçerli telemetri bekleniyor.
        </div>
      </div>
    );
  const fixedRiskDomain = channels.every(
    (channel) => channel.key === "risk_score",
  );
  const min = Math.min(...values),
    max = Math.max(...values),
    pad = Math.max((max - min) * 0.18, 1),
    low = fixedRiskDomain ? 0 : min < 0 ? min - pad : Math.max(0, min - pad),
    high = fixedRiskDomain ? 100 : max + pad;
  const start = Date.parse(history[0].timestamp),
    end = Date.parse(history[history.length - 1].timestamp);
  const x = (i: number) =>
      48 +
      (end > start
        ? (Date.parse(history[i].timestamp) - start) / (end - start)
        : i / Math.max(history.length - 1, 1)) *
        486,
    y = (v: number) => 138 - ((v - low) / (high - low)) * 112;
  return (
    <div className="trend-card">
      <div className="card-heading">
        <h3>{title}</h3>
        <div className="chart-legend">
          {channels.map((c) => (
            <span key={c.key}>
              <i style={{ background: c.color }} />
              {c.label}
            </span>
          ))}
        </div>
      </div>
      <svg
        viewBox="0 0 550 180"
        role="img"
        aria-label={`${title}, ${history.length} sentetik örnek, ${unit}`}
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={channels[0].color} stopOpacity=".12" />
            <stop offset="1" stopColor={channels[0].color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line
              x1="48"
              y1={26 + t * 112}
              x2="534"
              y2={26 + t * 112}
              stroke="#253242"
              strokeDasharray="3 5"
            />
            <text x="2" y={30 + t * 112} fill="#77899b" fontSize="10">
              {number(high - t * (high - low), high < 10 ? 1 : 0)}
            </text>
          </g>
        ))}
        {channels.map((c) => {
          let path = "";
          let pen = false;
          history.forEach((h, i) => {
            const v =
              c.key === "risk_score" ? h.risk_score : measuredValue(h, c.key);
            if (typeof v !== "number" || !Number.isFinite(v)) {
              pen = false;
              return;
            }
            path += `${pen ? "L" : "M"}${x(i)},${y(v)} `;
            pen = true;
          });
          return (
            <path
              key={c.key}
              d={path}
              fill="none"
              stroke={c.color}
              strokeWidth="2.2"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          );
        })}
        <text x="48" y="167" fill="#77899b" fontSize="10">
          {time(history[0].timestamp)}
        </text>
        <text x="534" y="167" textAnchor="end" fill="#77899b" fontSize="10">
          {time(history[history.length - 1].timestamp)}
        </text>
        <text x="534" y="12" textAnchor="end" fill="#77899b" fontSize="10">
          {unit}
        </text>
      </svg>
      <div className="chart-foot">
        {history.length} örnek <span>UTC · Sentetik zaman serisi</span>
      </div>
    </div>
  );
}
export function MiniTrend({
  values,
  color = "#49dcb7",
}: {
  values: (number | null)[];
  color?: string;
}) {
  const valid = values.filter(
    (v): v is number => v !== null && Number.isFinite(v),
  );
  if (valid.length < 2) return <span className="muted">—</span>;
  const min = Math.min(...valid),
    max = Math.max(...valid);
  let drawing = "";
  let pen = false;
  values.forEach((v, i) => {
    if (v === null || !Number.isFinite(v)) {
      pen = false;
      return;
    }
    drawing += `${pen ? "L" : "M"}${(i / Math.max(values.length - 1, 1)) * 80},${24 - ((v - min) / Math.max(max - min, 1)) * 20} `;
    pen = true;
  });
  return (
    <svg
      className="sparkline"
      viewBox="0 0 80 28"
      role="img"
      aria-label="Son risk örnekleri"
    >
      <path d={drawing} stroke={color} strokeWidth="1.8" fill="none" />
    </svg>
  );
}
