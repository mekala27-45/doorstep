"use client";

import { Bars } from "@/components/charts/Bars";
import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { mart } from "@/lib/data";
import { formatValue, type Scalar } from "@/lib/format";
import { useMart } from "@/lib/useMart";

type QuarantineRow = { source: string; rule: string; year: number | null; flagged: number; rows: number };

export function QuarantineByYear() {
  const sql = `select source, rule, year, sum(flagged) as flagged, sum(rows) as rows\nfrom ${mart("quarantine")}\ngroup by source, rule, year\norder by source, rule, year`;
  const q = useMart<QuarantineRow>(sql);
  const rows = q.rows ?? [];
  const total = rows.reduce((a, r) => a + r.rows, 0);
  const flagged = rows.reduce((a, r) => a + r.flagged, 0);
  return (
    <Figure
      testId="quarantine-by-year"
      message={total ? `${formatValue(flagged / total, "pct2")} of rows tripped a quarantine rule; nothing was deleted` : "The quarantine report by source and year"}
      subtitle="Rows flagged by each rule, by source and year; a row can trip more than one rule"
      source="Source: every source through its contract (real), the warehouse's mart_quarantine."
      sql={sql}
      table={{ columns: ["Source", "Rule", "Year", "Flagged", "Rows"], formats: ["text", "text", "int", "int", "int"], rows: rows.map((r) => [r.source, r.rule, r.year, r.flagged, r.rows]) }}
    >
      {q.rows ? (
        <p className="text-sm text-ink2">
          {formatValue(rows.length, "int")} source, rule and year cells over {formatValue(total, "int")} rows. Show the table for every cell.
        </p>
      ) : (
        <ChartSkeleton shape="table" height={60} />
      )}
    </Figure>
  );
}

/** Small multiples: one panel per estimator, one bar per condition, the bias in absolute value. */
export function RecoveryMultiples({ rows, source }: { rows: Scalar[][]; source: string }) {
  // rows: estimator, condition, seeds, bias, rmse, coverage, flag_rate
  const estimators = [...new Set(rows.map((r) => String(r[0])))];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5" data-testid="recovery-multiples">
      {estimators.map((name) => {
        const mine = rows.filter((r) => String(r[0]) === name);
        const biases = mine.map((r) => Math.abs(Number(r[3] ?? 0)));
        const worst = mine[biases.indexOf(Math.max(...biases))];
        const coverage = mine.map((r) => (r[5] === null || r[5] === undefined ? null : Number(r[5])));
        const meanCoverage = coverage.filter((c): c is number => c !== null);
        return (
          <Figure
            key={name}
            message={`${name.replace(/_/g, " ")}: largest bias under ${String(worst?.[1] ?? "")}`}
            subtitle={meanCoverage.length ? `Absolute bias by condition; interval coverage averages ${formatValue(meanCoverage.reduce((a, b) => a + b, 0) / meanCoverage.length, "pct0")}` : "Absolute bias by condition"}
            source={source}
            sql={null}
            table={{ columns: ["Condition", "Seeds", "Bias", "RMSE", "Coverage", "Flag rate"], formats: ["text", "int", "sfloat4", "float4", "pct0", "pct0"], rows: mine.map((r) => [r[1] ?? null, r[2] ?? null, r[3] ?? null, r[4] ?? null, r[5] ?? null, r[6] ?? null]) }}
          >
            <Bars
              bars={mine.map((r, j) => ({
                key: String(r[1]),
                label: String(r[1]).replace(/_demand\//, " demand, ").replace(/_supply\//, " supply, ").replace(/_reverse\//, " reverse, ").replace(/_noise$/, " noise"),
                value: biases[j] ?? 0,
                color: String(r[1]).includes("strong_reverse") ? "var(--cat-2)" : "var(--control)",
              }))}
              fmt="float4"
              axisLabel="absolute bias"
            />
          </Figure>
        );
      })}
    </div>
  );
}
