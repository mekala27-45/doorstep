"use client";

import { useEffect, useState } from "react";

import { ChartSkeleton, DataTable, Figure } from "@/components/charts/Figure";
import { LineChart } from "@/components/charts/LineChart";
import { StackedColumns } from "@/components/charts/StackedColumns";
import { mart, martNames, query, type Row } from "@/lib/data";
import { formatValue } from "@/lib/format";
import { useMart } from "@/lib/useMart";

const SOURCE = "Source: the warehouse's marts over FHFA, the census, HUD, Freddie Mac, the permits, the population estimates and HMDA (real), queried in the browser.";
const ANY = "";

type MetroRow = {
  cbsa_code: string;
  cbsa_title: string;
  households: number | null;
};
type YearRow = {
  year: number;
  value_anchored: number | null;
  median_income: number | null;
  payment_share: number | null;
  price_to_income: number | null;
  median_rent: number | null;
  rent_share: number | null;
  renter_burdened_share: number | null;
  renter_severe_share: number | null;
  permits_rate: number | null;
  migration_per_100: number | null;
  borrower_income_ratio: number | null;
  rate: number | null;
};

function Picker({ label, value, options, onChange, testId }: { label: string; value: string; options: [string, string][]; onChange: (v: string) => void; testId: string }) {
  return (
    <label className="flex flex-col text-xs text-ink2 gap-1 min-w-[16rem]">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testId} className="text-sm">
        {options.map(([v, text]) => (
          <option key={v} value={v}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

/** The gap year: every line breaks at 2020 because the one year census release does not exist. */
function withGap(rows: YearRow[], column: keyof YearRow): { x: number; y: number | null }[] {
  const out: { x: number; y: number | null }[] = [];
  for (const r of rows) {
    const v = r[column];
    out.push({ x: r.year, y: typeof v === "number" && Number.isFinite(v) ? v : null });
  }
  return out;
}

export function ExploreClient({ line }: { line: number }) {
  const my = mart("metro_year");
  const metros = useMart<MetroRow>(`select cbsa_code, cbsa_title, max(households) as households from ${my} where kind = 'metropolitan' group by cbsa_code, cbsa_title order by households desc nulls last, cbsa_title`);
  const [code, setCode] = useState<string>(ANY);
  useEffect(() => {
    if (code === ANY && metros.rows?.[0]) setCode(metros.rows[0].cbsa_code);
  }, [metros.rows, code]);
  const title = metros.rows?.find((r) => r.cbsa_code === code)?.cbsa_title ?? "";
  const sql = code
    ? `select year, value_anchored, median_income, payment_share, price_to_income, median_rent,\n       rent_share_of_median_income as rent_share, renter_burdened_share, renter_severe_share,\n       100.0 * permits / households as permits_rate, domestic_migration_per_100 as migration_per_100,\n       borrower_income_ratio, rate\nfrom ${my}\nwhere cbsa_code = '${code}'\norder by year`
    : null;
  const years = useMart<YearRow>(sql);
  const rows = years.rows ?? [];
  const latest = [...rows].reverse().find((r) => r.payment_share !== null);
  const first = rows.find((r) => r.payment_share !== null);
  const above = rows.filter((r) => r.payment_share !== null && (r.payment_share ?? 0) > line).length;
  const sqlBurden = sql;
  const bandYears = rows.filter((r) => r.renter_burdened_share !== null).map((r) => String(r.year));
  const latestBurden = [...rows].reverse().find((r) => r.renter_severe_share !== null);
  const latestPermits = [...rows].reverse().find((r) => r.permits_rate !== null);
  const latestMig = [...rows].reverse().find((r) => r.migration_per_100 !== null);
  const latestRatio = [...rows].reverse().find((r) => r.borrower_income_ratio !== null);
  const table = (cols: (keyof YearRow)[], formats: string[]) => ({
    columns: ["Year", ...cols.map((c) => c.replace(/_/g, " "))],
    formats: ["year", ...formats],
    rows: rows.map((r) => [r.year, ...cols.map((c) => r[c])]),
  });
  return (
    <div className="space-y-6">
      <div className="card p-4 flex flex-wrap gap-4 items-end" data-testid="pickers">
        <Picker label="Metro" value={code} onChange={setCode} options={(metros.rows ?? []).map((r) => [r.cbsa_code, r.cbsa_title])} testId="pick-metro" />
        {metros.rows ? <p className="text-xs text-ink2">{formatValue(metros.rows.length, "int")} metropolitan areas; the largest first.</p> : <p className="text-xs text-ink2">Loading the metros</p>}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Figure
          testId="explore-price"
          message={latest && first ? `The median home in ${title} went from ${formatValue(first.value_anchored, "usd0")} to ${formatValue(latest.value_anchored, "usd0")} while the median income went from ${formatValue(first.median_income, "usd0")} to ${formatValue(latest.median_income, "usd0")}` : "The price and the income"}
          subtitle="The anchored median home and the census median household income, by year"
          source={SOURCE}
          sql={sql}
          table={table(["value_anchored", "median_income", "price_to_income"], ["usd0", "usd0", "ratio2"])}
        >
          {years.rows ? (
            <LineChart
              series={[
                { key: "home", name: "Median home", color: "var(--cat-1)", points: withGap(rows, "value_anchored") },
                { key: "income", name: "Median income", color: "var(--ink)", points: withGap(rows, "median_income") },
              ]}
              xFmt="year"
              yFmt="usdk"
              xLabel="Year"
              yLabel="Dollars"
            />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-payment"
          message={latest ? `The payment on the median home takes ${formatValue(latest.payment_share, "pct1")} of the median income in ${latest.year}; ${formatValue(above, "int")} of ${formatValue(rows.filter((r) => r.payment_share !== null).length, "int")} years sat above the ${formatValue(line, "pct0")} line` : "The payment share"}
          subtitle="Twelve payments on ninety percent of the median home at the year's rate, over the median household income"
          source={SOURCE}
          sql={sql}
          table={table(["payment_share", "rate"], ["pct1", "rate2"])}
        >
          {years.rows ? (
            <LineChart
              series={[{ key: "share", name: "Payment share", color: "var(--cat-1)", points: withGap(rows, "payment_share") }]}
              xFmt="year"
              yFmt="pct0"
              xLabel="Year"
              yLabel="Share of median income"
              hRules={[{ y: line, label: `${formatValue(line, "pct0")} line`, color: "var(--cat-2)" }]}
            />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-rent"
          message={latestBurden ? `${formatValue(latestBurden.renter_severe_share, "pct0")} of renters in ${title} paid half or more of their income in rent in ${latestBurden.year}` : "The rent and the burden"}
          subtitle="Renters by the share of income the rent takes: under 30 percent, 30 to 50, 50 and over"
          source={SOURCE}
          sql={sqlBurden}
          table={table(["median_rent", "rent_share", "renter_burdened_share", "renter_severe_share"], ["usd0", "pct1", "pct1", "pct1"])}
        >
          {years.rows ? (
            <StackedColumns
              categories={bandYears}
              series={[
                { key: "under", name: "Under 30 percent", color: "var(--control)", hatched: true, values: Object.fromEntries(rows.map((r) => [String(r.year), r.renter_burdened_share === null ? null : 1 - (r.renter_burdened_share ?? 0)])) },
                { key: "mid", name: "30 to 50 percent", color: "var(--cat-2)", values: Object.fromEntries(rows.map((r) => [String(r.year), r.renter_burdened_share === null ? null : (r.renter_burdened_share ?? 0) - (r.renter_severe_share ?? 0)])) },
                { key: "severe", name: "50 percent and over", color: "var(--cat-4)", values: Object.fromEntries(rows.map((r) => [String(r.year), r.renter_severe_share])) },
              ]}
              yFmt="pct0"
              xLabel="Year"
              yLabel="Share of renters"
            />
          ) : (
            <ChartSkeleton shape="bars" />
          )}
        </Figure>
        <Figure
          testId="explore-supply"
          message={latestPermits ? `${title} permitted ${formatValue(latestPermits.permits_rate, "float2")} homes per hundred households in ${latestPermits.year}` : "Permits per hundred households"}
          subtitle="Building permits per hundred households, by year"
          source={SOURCE}
          sql={sql}
          table={table(["permits_rate"], ["float2"])}
        >
          {years.rows ? (
            <LineChart series={[{ key: "permits", name: "Permits per 100 households", color: "var(--cat-6)", points: withGap(rows, "permits_rate") }]} xFmt="year" yFmt="float1" xLabel="Year" yLabel="Permits per 100 households" />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-people"
          message={latestMig ? `Domestic migration in ${title} was ${formatValue(latestMig.migration_per_100, "sfloat2")} per hundred residents in ${latestMig.year}` : "Domestic migration"}
          subtitle="Net domestic migration per hundred residents, by population estimate year (July to June)"
          source={SOURCE}
          sql={sql}
          table={table(["migration_per_100"], ["sfloat2"])}
        >
          {years.rows ? (
            <LineChart series={[{ key: "mig", name: "Migration per 100 residents", color: "var(--cat-7)", points: withGap(rows, "migration_per_100") }]} xFmt="year" yFmt="sfloat1" xLabel="Year" yLabel="Per 100 residents" zero />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-borrowers"
          message={latestRatio ? `The median purchase borrower in ${title} earned ${formatValue(latestRatio.borrower_income_ratio, "ratio2")} the median household income in ${latestRatio.year}` : "The borrower income ratio"}
          subtitle="Median purchase borrower income over the metro median household income, HMDA years"
          source={SOURCE}
          sql={sql}
          table={table(["borrower_income_ratio"], ["ratio2"])}
        >
          {years.rows ? (
            <LineChart series={[{ key: "ratio", name: "Borrower income ratio", color: "var(--cat-8)", points: withGap(rows, "borrower_income_ratio") }]} xFmt="year" yFmt="ratio1" xLabel="Year" yLabel="Ratio" zero={false} />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
      </div>
      <SqlBox />
    </div>
  );
}

function SqlBox() {
  const names = martNames();
  const [sql, setSql] = useState(`select cbsa_title, payment_share, price_to_income\nfrom mart_metro_year\nwhere year = (select max(year) from mart_metro_year where payment_share is not null) and kind = 'metropolitan'\norder by payment_share desc\nlimit 20`);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  useEffect(() => setRows(null), [sql]);
  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await query(sql);
      setRows(result.slice(0, 500));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  };
  const columns = rows && rows[0] ? Object.keys(rows[0]) : [];
  return (
    <section className="card p-4 sm:p-5" aria-labelledby="sqlbox" data-testid="sql-box">
      <h2 id="sqlbox" className="text-xl mb-1">
        Ask your own question
      </h2>
      <p className="text-sm text-ink2 mb-3">Read only SQL over the published marts: {names.map((n) => `mart_${n}`).join(", ")}.</p>
      <textarea value={sql} onChange={(e) => setSql(e.target.value)} className="sql w-full min-h-[140px]" aria-label="SQL" spellCheck={false} data-testid="sql-input" />
      <div className="flex items-center gap-3 mt-2">
        <button type="button" onClick={run} disabled={running} className="text-sm px-3 py-1.5 rounded bg-ink text-surface disabled:opacity-60" data-testid="sql-run">
          {running ? "Running" : "Run the query"}
        </button>
        {error ? (
          <p className="text-sm text-ink" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      {rows ? (
        <div className="mt-3" data-testid="sql-result">
          <DataTable
            table={{
              columns,
              formats: columns.map((c) => (typeof rows[0]?.[c] === "number" ? "float3" : "text")),
              rows: rows.map((r) => columns.map((c) => (r[c] as string | number | null) ?? null)),
            }}
          />
        </div>
      ) : null}
    </section>
  );
}
