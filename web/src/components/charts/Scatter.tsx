"use client";

import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";
import { useState } from "react";

import { formatValue } from "@/lib/format";

import { Legend, type LegendItem } from "./Legend";
import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { fitTicks, textWidth, useWidth } from "./useWidth";

export interface ScatterPoint {
  x: number;
  y: number;
  label?: string;
}
export interface FitLine {
  key: string;
  name: string;
  points: { x: number; y: number | null }[];
  color: string;
  dash?: string;
  band?: { x: number; low: number | null; high: number | null }[];
}

/**
 * Points on two value axes with fitted lines drawn through them, each with its interval band where
 * one exists. Hover reads the nearest point by name. Points share one hue; the lines carry the roles.
 */
export function Scatter({
  points,
  lines,
  xFmt,
  yFmt,
  xLabel,
  yLabel,
  pointColor,
  pointName = "metro",
  height = 300,
  hRules = [],
  highlight = [],
  testId,
}: {
  points: ScatterPoint[];
  lines: FitLine[];
  xFmt: string;
  yFmt: string;
  xLabel: string;
  yLabel: string;
  pointColor: string;
  pointName?: string;
  height?: number;
  hRules?: { y: number; label: string; color?: string }[];
  highlight?: string[];
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const [near, setNear] = useState<number | null>(null);
  const xsAll = points.map((p) => p.x).concat(lines.flatMap((l) => l.points.map((p) => p.x)));
  const ysAll = points
    .map((p) => p.y)
    .concat(lines.flatMap((l) => [...l.points.map((p) => p.y ?? NaN), ...(l.band ?? []).flatMap((b) => [b.low ?? NaN, b.high ?? NaN])]))
    .concat(hRules.map((r) => r.y))
    .filter((v) => Number.isFinite(v));
  const y0 = scaleLinear()
    .domain([Math.min(...ysAll), Math.max(...ysAll)])
    .nice(5);
  const yTicks = y0.ticks(5).filter((t, i, arr) => i === 0 || formatValue(t, yFmt) !== formatValue(arr[i - 1], yFmt));
  const tickW = Math.max(...yTicks.map((t) => textWidth(formatValue(t, yFmt), 11)), 20);
  const margin = { top: 12, right: 18, bottom: 42, left: Math.ceil(tickW) + 12 };
  const innerW = Math.max(width - margin.left - margin.right, 80);
  const innerH = height - margin.top - margin.bottom;
  const y = y0.range([innerH, 0]);
  const x = scaleLinear()
    .domain([Math.min(...xsAll), Math.max(...xsAll)])
    .nice(5)
    .range([0, innerW]);
  const xTicks = fitTicks(x, innerW, (t) => formatValue(t, xFmt), width < 480 ? 4 : 6);
  const path = line<{ x: number; y: number | null }>()
    .defined((d) => d.y !== null && Number.isFinite(d.y))
    .x((d) => x(d.x))
    .y((d) => y(d.y ?? 0));
  const bandPath = area<{ x: number; low: number | null; high: number | null }>()
    .defined((d) => d.low !== null && d.high !== null)
    .x((d) => x(d.x))
    .y0((d) => y(d.low ?? 0))
    .y1((d) => y(d.high ?? 0));
  const onMove = (e: Parameters<typeof pointIn>[1]) => {
    const at = pointIn(ref.current, e);
    const px = at.x - margin.left;
    const py = at.y - margin.top;
    let best = -1;
    let gap = Infinity;
    points.forEach((p, i) => {
      const d = (x(p.x) - px) ** 2 + (y(p.y) - py) ** 2;
      if (d < gap) {
        gap = d;
        best = i;
      }
    });
    const p = points[best];
    if (!p || gap > 30 * 30) {
      setNear(null);
      setTip(null);
      return;
    }
    setNear(best);
    setTip({ x: at.x, y: at.y, lines: [p.label ?? pointName, `${xLabel}: ${formatValue(p.x, xFmt)}`, `${yLabel}: ${formatValue(p.y, yFmt)}`] });
  };
  const legend: LegendItem[] = [{ label: pointName, color: pointColor, kind: "dot" }, ...lines.map((l) => ({ label: l.name, color: l.color, kind: "line" as const, dash: l.dash }))];
  return (
    <div
      ref={ref}
      className="relative w-full overflow-hidden"
      onMouseLeave={() => {
        setTip(null);
        setNear(null);
      }}
      data-testid={testId}
    >
      <p className="text-[11px] text-ink2 mb-1">{yLabel}</p>
      <svg width={width} height={height} role="img" aria-label={`${yLabel} against ${xLabel}`}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {yTicks.map((t) => (
            <g key={t} transform={`translate(0,${y(t)})`}>
              <line x2={innerW} stroke="var(--hairline)" strokeDasharray={t === 0 ? undefined : "2 3"} />
              <text x={-8} dy="0.32em" textAnchor="end" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, yFmt)}
              </text>
            </g>
          ))}
          {xTicks.map((t) => (
            <g key={t} transform={`translate(${x(t)},0)`}>
              <line y1={0} y2={innerH} stroke="var(--hairline)" strokeDasharray="2 3" />
              <text y={innerH + 17} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, xFmt)}
              </text>
            </g>
          ))}
          <text x={innerW / 2} y={innerH + 34} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            {xLabel}
          </text>
          {hRules.map((r) => (
            <g key={r.label || String(r.y)}>
              <line x1={0} x2={innerW} y1={y(r.y)} y2={y(r.y)} stroke={r.color ?? "var(--control)"} strokeWidth={1.5} strokeDasharray="4 3" />
              {r.label ? (
                <text x={innerW - 2} y={y(r.y) - 5} textAnchor="end" className="fill-[var(--ink2)] text-[10.5px]">
                  {r.label}
                </text>
              ) : null}
            </g>
          ))}
          {points.map((p, i) => (
            <circle
              key={`${p.label ?? ""}-${i}`}
              cx={x(p.x)}
              cy={y(p.y)}
              r={near === i ? 5.5 : 3.5}
              fill={pointColor}
              opacity={highlight.length && !highlight.includes(pointName) ? 0.3 : 0.65}
              stroke="var(--chart-bg)"
              strokeWidth={0.8}
              data-point={p.label}
            />
          ))}
          {lines.map((l) => {
            const lifted = highlight.length === 0 || highlight.includes(l.name) || highlight.includes(l.key);
            return (
              <g key={l.key} data-line={l.name}>
                {l.band ? <path d={bandPath(l.band) ?? ""} fill={l.color} opacity={lifted ? 0.16 : 0.06} /> : null}
                <path d={path(l.points) ?? ""} fill="none" stroke={l.color} strokeWidth={lifted ? 2.5 : 1.5} strokeDasharray={l.dash} opacity={lifted ? 1 : 0.4} />
              </g>
            );
          })}
          <rect x={0} y={0} width={innerW} height={innerH} fill="transparent" onMouseMove={onMove} aria-label={`Read ${yLabel} against ${xLabel}`} />
        </g>
      </svg>
      <Legend items={legend} />
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
