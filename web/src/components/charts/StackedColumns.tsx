"use client";

import { scaleBand, scaleLinear } from "d3-scale";
import { useState } from "react";

import { formatValue } from "@/lib/format";

import { PATTERN } from "./Defs";
import { Legend, type LegendItem } from "./Legend";
import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { textWidth, useWidth } from "./useWidth";

export interface ColumnSeries {
  key: string;
  name: string;
  values: Record<string, number | null>;
  color: string;
  hatched?: boolean;
}
export interface ColumnMark {
  x: string;
  label: string;
}

/** Stacked columns by category (a year), each stack a share summing to one, with the parts in the committed order. */
export function StackedColumns({
  categories,
  series,
  yFmt,
  xLabel,
  yLabel,
  height = 300,
  hRules = [],
  marks = [],
  highlight = [],
  testId,
}: {
  categories: string[];
  series: ColumnSeries[];
  yFmt: string;
  xLabel: string;
  yLabel: string;
  height?: number;
  hRules?: { y: number; label: string; color?: string }[];
  marks?: ColumnMark[];
  highlight?: string[];
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const totals = categories.map((c) => series.reduce((a, s) => a + (s.values[c] ?? 0), 0));
  const hi = Math.max(1e-9, ...totals, ...hRules.map((r) => r.y));
  const y0 = scaleLinear()
    .domain([0, hi])
    .nice(5);
  const yTicks = y0.ticks(5);
  const tickW = Math.max(...yTicks.map((t) => textWidth(formatValue(t, yFmt), 11)), 20);
  const margin = { top: marks.length ? 24 : 12, right: 12, bottom: 42, left: Math.ceil(tickW) + 12 };
  const innerW = Math.max(width - margin.left - margin.right, 80);
  const innerH = height - margin.top - margin.bottom;
  const y = y0.range([innerH, 0]);
  const x = scaleBand<string>().domain(categories).range([0, innerW]).paddingInner(0.18).paddingOuter(0.05);
  const every = Math.max(1, Math.ceil((categories.length * 34) / innerW));
  const onMove = (e: Parameters<typeof pointIn>[1]) => {
    const at = pointIn(ref.current, e);
    const px = at.x - margin.left;
    const index = Math.min(categories.length - 1, Math.max(0, Math.floor(px / (innerW / categories.length))));
    const c = categories[index];
    if (c === undefined) return;
    const lines = [`${xLabel}: ${c}`, ...series.map((s) => `${s.name}: ${formatValue(s.values[c] ?? null, yFmt)}`)];
    setTip({ x: at.x, y: at.y, lines });
  };
  const legend: LegendItem[] = series.map((s) => ({ label: s.name, color: s.color, kind: "bar", pattern: s.hatched ? PATTERN.hatch : undefined }));
  return (
    <div ref={ref} className="relative w-full overflow-hidden" data-testid={testId} onMouseLeave={() => setTip(null)}>
      <p className="text-[11px] text-ink2 mb-1">{yLabel}</p>
      <svg width={width} height={height} role="img" aria-label={`${yLabel} by ${xLabel}, stacked`}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {yTicks.map((t) => (
            <g key={t} transform={`translate(0,${y(t)})`}>
              <line x2={innerW} stroke="var(--hairline)" strokeDasharray={t === 0 ? undefined : "2 3"} />
              <text x={-8} dy="0.32em" textAnchor="end" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, yFmt)}
              </text>
            </g>
          ))}
          {categories.map((c, i) => {
            let base = 0;
            const bw = x.bandwidth();
            const left = x(c) ?? 0;
            return (
              <g key={c} data-column={c}>
                {series.map((s) => {
                  const v = s.values[c];
                  if (v === null || v === undefined || !Number.isFinite(v)) return null;
                  const top = base + v;
                  const lifted = highlight.length === 0 || highlight.includes(s.name) || highlight.includes(s.key);
                  const rect = (
                    <g key={s.key}>
                      <rect x={left} y={y(top)} width={bw} height={Math.max(y(base) - y(top), 0)} fill={s.color} opacity={lifted ? 0.9 : 0.35} />
                      {s.hatched ? <rect x={left} y={y(top)} width={bw} height={Math.max(y(base) - y(top), 0)} fill={PATTERN.hatch} /> : null}
                    </g>
                  );
                  base = top;
                  return rect;
                })}
                {i % every === 0 ? (
                  <text x={left + bw / 2} y={innerH + 17} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
                    {c}
                  </text>
                ) : null}
              </g>
            );
          })}
          {hRules.map((r) => (
            <g key={r.label || String(r.y)}>
              <line x1={0} x2={innerW} y1={y(r.y)} y2={y(r.y)} stroke={r.color ?? "var(--ink)"} strokeWidth={1.5} strokeDasharray="4 3" />
              <text x={innerW - 2} y={y(r.y) - 5} textAnchor="end" className="fill-[var(--ink2)] text-[10.5px]">
                {r.label}
              </text>
            </g>
          ))}
          {marks.map((m) => {
            const left = (x(m.x) ?? 0) + x.bandwidth() / 2;
            return (
              <g key={m.label} data-mark={m.label}>
                <line x1={left} x2={left} y1={-6} y2={innerH} stroke="var(--ink)" strokeWidth={1.2} strokeDasharray="3 3" />
                <text x={left + 4} y={-10} className="fill-[var(--ink)] text-[10.5px] font-semibold">
                  {m.label}
                </text>
              </g>
            );
          })}
          <text x={innerW / 2} y={innerH + 34} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            {xLabel}
          </text>
          <rect x={0} y={0} width={innerW} height={innerH} fill="transparent" onMouseMove={onMove} aria-label={`Read ${yLabel} by ${xLabel}`} />
        </g>
      </svg>
      <Legend items={legend} />
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
