"use client";

import { scaleLinear } from "d3-scale";
import { area } from "d3-shape";
import { type KeyboardEvent, useMemo, useState } from "react";

import { formatValue } from "@/lib/format";

import { PATTERN } from "./Defs";
import { Legend, type LegendItem } from "./Legend";
import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { fitTicks, textWidth, useWidth } from "./useWidth";

export interface AreaSeries {
  key: string;
  name: string;
  points: { x: number; y: number | null }[];
  color: string;
  opacity?: number;
  hatched?: boolean;
}
export interface AreaMark {
  x: number;
  y: number;
  label: string;
}

/**
 * Stacked areas on one axis: each series is drawn from the top of the one below, so the stack's
 * height is the total. Negative values stack downward. Hover or arrow keys walk the x values and read
 * every part and the total at that point.
 */
export function StackedArea({
  series,
  xFmt,
  yFmt,
  xLabel,
  yLabel,
  height = 300,
  marks = [],
  shades = [],
  highlight = [],
  testId,
}: {
  series: AreaSeries[];
  xFmt: string;
  yFmt: string;
  xLabel: string;
  yLabel: string;
  height?: number;
  marks?: AreaMark[];
  shades?: { from: number; to: number; label: string }[];
  highlight?: string[];
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const xs = useMemo(() => [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort((a, b) => a - b), [series]);
  // Stack per x: positives build up from zero, negatives build down, so a part that pulls the payment down reads below the axis.
  const stacked = useMemo(() => {
    const up = new Map<number, number>();
    const down = new Map<number, number>();
    return series.map((s) => {
      const bands = s.points.map((p) => {
        const v = p.y ?? 0;
        const base = v >= 0 ? (up.get(p.x) ?? 0) : (down.get(p.x) ?? 0);
        const top = base + v;
        if (v >= 0) up.set(p.x, top);
        else down.set(p.x, top);
        return { x: p.x, y0: base, y1: top, value: v };
      });
      return { ...s, bands };
    });
  }, [series]);
  const ys = stacked.flatMap((s) => s.bands.flatMap((b) => [b.y0, b.y1])).concat(marks.map((m) => m.y));
  const yLo = Math.min(0, ...ys);
  const yHi = Math.max(0, ...ys);
  const y0 = scaleLinear()
    .domain([yLo, yHi === yLo ? yLo + 1 : yHi])
    .nice(5);
  const yTicks = y0.ticks(5).filter((t, i, arr) => i === 0 || formatValue(t, yFmt) !== formatValue(arr[i - 1], yFmt));
  const tickW = Math.max(...yTicks.map((t) => textWidth(formatValue(t, yFmt), 11)), 20);
  const margin = { top: marks.length || shades.length ? 24 : 12, right: 16, bottom: 42, left: Math.ceil(tickW) + 12 };
  const innerW = Math.max(width - margin.left - margin.right, 80);
  const innerH = height - margin.top - margin.bottom;
  const y = y0.range([innerH, 0]);
  const xLo = xs[0] ?? 0;
  const xHi = xs[xs.length - 1] ?? 1;
  const x = scaleLinear()
    .domain([xLo, xHi === xLo ? xLo + 1 : xHi])
    .range([0, innerW]);
  const xTicks = fitTicks(x, innerW, (t) => formatValue(t, xFmt), width < 480 ? 4 : 6).filter((t, i, arr) => i === 0 || formatValue(t, xFmt) !== formatValue(arr[i - 1], xFmt));
  const path = area<{ x: number; y0: number; y1: number }>()
    .x((d) => x(d.x))
    .y0((d) => y(d.y0))
    .y1((d) => y(d.y1));

  const showAt = (index: number, px?: number, py?: number) => {
    const at = xs[index];
    if (at === undefined) return;
    setHover(index);
    const lines = [`${xLabel}: ${formatValue(at, xFmt)}`];
    let total = 0;
    for (const s of stacked) {
      const b = s.bands.find((p) => p.x === at);
      if (b) {
        lines.push(`${s.name}: ${formatValue(b.value, yFmt)}`);
        total += b.value;
      }
    }
    lines.push(`Total: ${formatValue(total, yFmt)}`);
    setTip({ x: px ?? x(at) + margin.left, y: py ?? margin.top + 8, lines });
  };
  const onMove = (e: Parameters<typeof pointIn>[1]) => {
    const at = pointIn(ref.current, e);
    const value = x.invert(at.x - margin.left);
    let index = 0;
    let gap = Infinity;
    xs.forEach((v, i) => {
      const d = Math.abs(v - value);
      if (d < gap) {
        gap = d;
        index = i;
      }
    });
    showAt(index, at.x, at.y);
  };
  const onKey = (e: KeyboardEvent<SVGRectElement>) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const next = Math.min(Math.max((hover ?? (e.key === "ArrowRight" ? -1 : xs.length)) + (e.key === "ArrowRight" ? 1 : -1), 0), xs.length - 1);
      showAt(next);
    } else if (e.key === "Escape") {
      setHover(null);
      setTip(null);
    }
  };
  const legend: LegendItem[] = series.map((s) => ({ label: s.name, color: s.color, kind: "bar", opacity: s.opacity }));
  const hoverX = hover !== null ? xs[hover] : undefined;
  return (
    <div
      ref={ref}
      className="relative w-full overflow-hidden"
      onMouseLeave={() => {
        setTip(null);
        setHover(null);
      }}
      data-testid={testId}
    >
      <p className="text-[11px] text-ink2 mb-1">{yLabel}</p>
      <svg width={width} height={height} role="img" aria-label={`${yLabel} by ${xLabel}, stacked`}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {shades.map((s) => (
            <g key={s.label}>
              <rect x={x(s.from)} y={0} width={Math.max(x(s.to) - x(s.from), 1)} height={innerH} fill={PATTERN.window} />
              <text x={x(s.from) + 4} y={-8} className="fill-[var(--ink2)] text-[10.5px]">
                {s.label}
              </text>
            </g>
          ))}
          {yTicks.map((t) => (
            <g key={t} transform={`translate(0,${y(t)})`}>
              <line x2={innerW} stroke="var(--hairline)" strokeDasharray={t === 0 ? undefined : "2 3"} />
              <text x={-8} dy="0.32em" textAnchor="end" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, yFmt)}
              </text>
            </g>
          ))}
          {xTicks.map((t) => (
            <text key={t} x={x(t)} y={innerH + 17} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
              {formatValue(t, xFmt)}
            </text>
          ))}
          <text x={innerW / 2} y={innerH + 34} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            {xLabel}
          </text>
          {stacked.map((s) => {
            const lifted = highlight.length === 0 || highlight.includes(s.key) || highlight.includes(s.name);
            return (
              <g key={s.key} data-area={s.name}>
                <path d={path(s.bands) ?? ""} fill={s.color} opacity={(s.opacity ?? 0.78) * (lifted ? 1 : 0.35)} />
                {s.hatched ? <path d={path(s.bands) ?? ""} fill={PATTERN.hatch} opacity={lifted ? 1 : 0.35} /> : null}
                <path
                  d={area<{ x: number; y0: number; y1: number }>().x((d) => x(d.x)).y0((d) => y(d.y1)).y1((d) => y(d.y1))(s.bands) ?? ""}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={1.5}
                />
              </g>
            );
          })}
          <line x1={0} x2={innerW} y1={y(0)} y2={y(0)} stroke="var(--ink2)" strokeWidth={1} />
          {marks.map((m) => (
            <g key={m.label} data-mark={m.label}>
              <line x1={x(m.x)} x2={x(m.x)} y1={-6} y2={innerH} stroke="var(--ink)" strokeWidth={1.2} strokeDasharray="3 3" />
              <circle cx={x(m.x)} cy={y(m.y)} r={5} fill="var(--ink)" stroke="var(--chart-bg)" strokeWidth={1.5} />
              <text x={x(m.x) + (x(m.x) > innerW * 0.7 ? -6 : 6)} y={-10} textAnchor={x(m.x) > innerW * 0.7 ? "end" : "start"} className="fill-[var(--ink)] text-[10.5px] font-semibold">
                {m.label}
              </text>
            </g>
          ))}
          {hoverX !== undefined ? <line x1={x(hoverX)} x2={x(hoverX)} y1={0} y2={innerH} stroke="var(--control)" pointerEvents="none" /> : null}
          <rect
            x={0}
            y={0}
            width={innerW}
            height={innerH}
            fill="transparent"
            tabIndex={0}
            aria-label={`Read ${yLabel} by ${xLabel}; use the arrow keys`}
            onMouseMove={onMove}
            onKeyDown={onKey}
            onBlur={() => {
              setHover(null);
              setTip(null);
            }}
            className="outline-none focus-visible:stroke-[var(--lead)]"
          />
        </g>
      </svg>
      <Legend items={legend} />
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
