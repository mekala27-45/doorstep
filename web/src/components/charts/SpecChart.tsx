"use client";

import type { ChartSpec, SpecPanel, SpecRule, SpecState } from "@/lib/charts";
import { roleColor, xNumber } from "@/lib/charts";
import { formatValue } from "@/lib/format";

import { Columns } from "./Columns";
import { type HRule, LineChart, type LineSeries, type PointMark, type Shade, type VRule } from "./LineChart";
import { Scatter } from "./Scatter";
import { Slope } from "./Slope";
import { StackedArea } from "./StackedArea";
import { StackedColumns } from "./StackedColumns";
import { DASHES } from "./useWidth";

/** Which annotation and rule groups a state shows, and which series it lifts. No state shows all. */
function visibility(spec: ChartSpec, stateId: string | null): { show: (group: string | null | undefined) => boolean; highlight: string[] } {
  if (!stateId) return { show: () => true, highlight: [] };
  const index = spec.states.findIndex((s) => s.id === stateId);
  const state: SpecState | undefined = spec.states[index];
  if (!state) return { show: () => true, highlight: [] };
  // A group is shown once its state has been reached: states build on each other as the reader scrolls.
  const reached = new Set(spec.states.slice(0, index + 1).flatMap((s) => s.show));
  return { show: (group) => !group || reached.has(group), highlight: state.highlight };
}

function lineSeries(panel: SpecPanel, highlight: string[]): LineSeries[] {
  return panel.series.map((s, i) => {
    const lifted = highlight.length === 0 || highlight.includes(s.name);
    const points = s.points.map(([x, y]) => ({ x: xNumber(x), y }));
    const band =
      s.low && s.high
        ? s.points.map(([x], j) => ({ x: xNumber(x), low: s.low?.[j] ?? null, high: s.high?.[j] ?? null }))
        : undefined;
    return {
      key: `${s.name}-${i}`,
      name: s.label ?? s.name,
      points,
      color: roleColor(s.role),
      dash: s.dashed ? DASHES[1] : DASHES[i % DASHES.length],
      width: lifted && highlight.length > 0 ? 3 : 2,
      opacity: lifted ? 1 : 0.28,
      band,
    };
  });
}

function rulesOf(rules: SpecRule[], show: (g: string | null | undefined) => boolean): { v: VRule[]; h: HRule[] } {
  const v: VRule[] = [];
  const h: HRule[] = [];
  for (const r of rules) {
    if (!show(r.state)) continue;
    const color = r.role ? roleColor(r.role) : "var(--control)";
    if (r.x !== undefined) v.push({ x: r.x, label: r.label ?? "", color, dash: r.faint ? "2 3" : undefined });
    if (r.y !== undefined) h.push({ y: r.y, label: r.label ?? "", color, dash: "5 3" });
  }
  return { v, h };
}

export function SpecChart({ spec, state = null, height }: { spec: ChartSpec; state?: string | null; height?: number }) {
  const { show, highlight } = visibility(spec, state);
  if (spec.kind === "histogram") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const series = panel.series[0];
    const points = (series?.points ?? []).map(([x, y]) => ({ x: xNumber(x), y: y ?? 0 }));
    const rules = panel.rules
      .filter((r) => r.x !== undefined && show(r.state))
      .map((r) => ({ x: r.x ?? 0, label: r.faint ? undefined : r.label, color: r.role ? roleColor(r.role) : undefined, faint: r.faint }));
    return (
      <Columns
        points={points}
        xFmt={spec.x_format}
        yFmt={spec.y_format}
        xLabel={spec.x_label}
        yLabel={spec.y_label}
        rules={rules}
        split={0}
        height={height ?? 320}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "slope") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const lines = panel.series.map((s) => ({
      key: s.name,
      label: s.label ?? s.name,
      left: Number(s.points[0]?.[1] ?? 0),
      right: Number(s.points[1]?.[1] ?? 0),
      color: roleColor(s.role),
    }));
    return (
      <Slope
        lines={lines}
        leftLabel="Ranked by price"
        rightLabel="Ranked by payment share of local income"
        highlight={highlight}
        showRight={show("adjusted")}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "bars") {
    // Stacked columns by category: every series has one point per category and the parts sum to the stack.
    const panel = spec.panels[0];
    if (!panel) return null;
    const categories = [...new Set(panel.series.flatMap((s) => s.points.map(([x]) => String(x))))];
    const series = panel.series.map((s) => ({
      key: s.name,
      name: s.label ?? s.name,
      values: Object.fromEntries(s.points.map(([x, y]) => [String(x), y])),
      color: roleColor(s.role),
      hatched: s.role === "control",
    }));
    const marks = panel.annotations.filter((a) => show(a.state)).map((a) => ({ x: String(a.x), label: a.text }));
    const rules = panel.rules.filter((r) => r.y !== undefined && show(r.state)).map((r) => ({ y: r.y ?? 0, label: r.label ?? "", color: r.role ? roleColor(r.role) : undefined }));
    return (
      <StackedColumns
        categories={categories}
        series={series}
        yFmt={panel.y_format ?? spec.y_format}
        xLabel={spec.x_label}
        yLabel={panel.y_label ?? spec.y_label}
        hRules={rules}
        marks={marks}
        highlight={highlight.map((h) => panel.series.find((s) => s.name === h)?.label ?? h)}
        height={height ?? 320}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "area") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const series = panel.series.map((s) => ({
      key: s.name,
      name: s.label ?? s.name,
      points: s.points.map(([x, y]) => ({ x: xNumber(x), y })),
      color: roleColor(s.role),
      hatched: s.role === "control",
    }));
    const shown = series.filter((s) => show(s.key));
    const marks = panel.annotations.filter((a) => show(a.state) && a.y !== null && a.y !== undefined).map((a) => ({ x: xNumber(a.x), y: a.y ?? 0, label: a.text }));
    const shades = panel.bands.map((b) => ({ from: xNumber(b.from), to: xNumber(b.to), label: b.label }));
    return (
      <StackedArea
        series={shown.length ? shown : series}
        xFmt={spec.x_format}
        yFmt={panel.y_format ?? spec.y_format}
        xLabel={spec.x_label}
        yLabel={panel.y_label ?? spec.y_label}
        marks={marks}
        shades={shades}
        highlight={highlight.map((h) => panel.series.find((s) => s.name === h)?.label ?? h)}
        height={height ?? 320}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "scatter") {
    // The first panel is the scatter with its fitted lines; further panels are lines on their own axes.
    const [first, ...rest] = spec.panels;
    if (!first) return null;
    const dots = first.series[0];
    // The table rows are written in the points' order, so a point's name is its row's first column.
    const points = (dots?.points ?? []).map(([x, y], i) => ({ x: xNumber(x), y: y ?? 0, label: `${dots?.label ?? dots?.name ?? "point"} ${i + 1}` }));
    const named = points.map((p, i) => ({ ...p, label: spec.table_rows.length === points.length ? String(spec.table_rows[i]?.[0] ?? p.label) : p.label }));
    const fits = first.series.slice(1).filter((s) => show(s.name)).map((s, i) => ({
      key: s.name,
      name: s.label ?? s.name,
      points: s.points.map(([x, y]) => ({ x: xNumber(x), y })),
      color: roleColor(s.role),
      dash: s.dashed ? DASHES[1] : i === 0 ? "" : DASHES[(i + 1) % DASHES.length],
      band: s.low && s.high ? s.points.map(([x], j) => ({ x: xNumber(x), low: s.low?.[j] ?? null, high: s.high?.[j] ?? null })) : undefined,
    }));
    const rules = first.rules.filter((r) => r.y !== undefined && show(r.state)).map((r) => ({ y: r.y ?? 0, label: r.label ?? "", color: r.role ? roleColor(r.role) : undefined }));
    const scatterShown = show(dots?.name);
    return (
      <div className="space-y-5" data-testid={`chart-${spec.id}`}>
        {scatterShown || rest.length === 0 ? (
          <div>
            {rest.length ? <p className="text-sm font-semibold text-ink mb-1">{first.title}</p> : null}
            <Scatter
              points={named}
              lines={fits}
              xFmt={spec.x_format}
              yFmt={first.y_format ?? spec.y_format}
              xLabel={spec.x_label}
              yLabel={first.y_label ?? spec.y_label}
              pointColor={roleColor(dots?.role ?? "control")}
              pointName={dots?.label ?? dots?.name ?? "metro"}
              hRules={rules}
              highlight={highlight.map((h) => first.series.find((s) => s.name === h)?.label ?? h)}
              height={height ?? 300}
            />
          </div>
        ) : null}
        {rest.map((panel, i) => {
          if (!panel.series.some((s) => show(s.name))) return null;
          const { v, h } = rulesOf(panel.rules, show);
          const shades: Shade[] = panel.bands.map((b) => ({ from: xNumber(b.from), to: xNumber(b.to), label: b.label }));
          return (
            <div key={`${panel.title}-${i}`}>
              <p className="text-sm font-semibold text-ink mb-1">{panel.title}</p>
              <LineChart
                series={lineSeries(panel, highlight)}
                xFmt={"quarter"}
                yFmt={panel.y_format ?? spec.y_format}
                xLabel={"quarter"}
                yLabel={panel.y_label ?? spec.y_label}
                vRules={v}
                hRules={h}
                shades={shades}
                zero={false}
                height={height ?? 260}
              />
            </div>
          );
        })}
      </div>
    );
  }
  // Lines: one panel or several stacked, each on its own axis.
  return (
    <div className="space-y-5" data-testid={`chart-${spec.id}`}>
      {spec.panels.map((panel, i) => {
        const { v, h } = rulesOf(panel.rules, show);
        const shades: Shade[] = panel.bands.map((b) => ({ from: xNumber(b.from), to: xNumber(b.to), label: b.label }));
        const marks: PointMark[] = [];
        for (const a of panel.annotations) {
          if (!show(a.state)) continue;
          const x = xNumber(a.x);
          if (!Number.isFinite(x)) continue;
          if (a.y !== null && a.y !== undefined) marks.push({ x, y: a.y, label: a.text, color: "var(--ink)" });
          else v.push({ x, label: a.text, color: "var(--ink2)", dash: "3 3" });
        }
        return (
          <div key={`${panel.title}-${i}`}>
            {spec.panels.length > 1 ? <p className="text-sm font-semibold text-ink mb-1">{panel.title}</p> : null}
            <LineChart
              series={lineSeries(panel, highlight)}
              xFmt={spec.x_format}
              yFmt={panel.y_format ?? spec.y_format}
              xLabel={spec.x_label}
              yLabel={panel.y_label ?? spec.y_label}
              vRules={v}
              hRules={h}
              shades={shades}
              marks={marks}
              zero={spec.kind === "curves"}
              height={height ?? (spec.panels.length > 1 ? 220 : 300)}
              compact={spec.panels.length > 2}
            />
            {marks.length ? (
              <ul className="mt-1 text-xs text-ink2 flex flex-wrap gap-x-4">
                {marks.map((m) => (
                  <li key={m.label}>{m.label}</li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/** A spec's table toggle data. */
export function specTable(spec: ChartSpec): { columns: string[]; formats: string[]; rows: ChartSpec["table_rows"] } {
  const formats = spec.table_columns.map((_, i) => {
    const sample = spec.table_rows.find((r) => r[i] !== null && r[i] !== undefined)?.[i];
    if (typeof sample === "number") return Number.isInteger(sample) && Math.abs(sample) >= 1000 ? "int" : "float3";
    return "text";
  });
  return { columns: spec.table_columns, formats, rows: spec.table_rows };
}

export function describe(spec: ChartSpec): string {
  return `${spec.message}. ${spec.subtitle}. ${formatValue(spec.panels.length, "int")} panel${spec.panels.length === 1 ? "" : "s"}.`;
}
