"use client";

import { useEffect, useState } from "react";

import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { LineChart } from "@/components/charts/LineChart";
import { Status } from "@/components/Status";
import {
  type Answer,
  apiSource,
  type CheckOut,
  type CurveResponse,
  getCurve,
  type HealthResponse,
  type Inputs,
  type MetroEntry,
  type MetrosResponse,
  read,
  recordedSession,
  saveCheck,
  type Source,
} from "@/lib/api";
import { formatValue } from "@/lib/format";
import { markReady } from "@/lib/ready";

const DOWN_SHARES = [0.03, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3];
const HORIZONS = [5, 7, 10, 15, 20, 30];

function sameInputs(a: Inputs, b: Inputs): boolean {
  return a.cbsa_code === b.cbsa_code && a.income === b.income && a.down_share === b.down_share && a.rate === b.rate && a.horizon_years === b.horizon_years;
}

export function PlannerClient({ line }: { line: number }) {
  const [source, setSource] = useState<Source | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metros, setMetros] = useState<MetroEntry[]>([]);
  const [presets, setPresets] = useState<Inputs[]>([]);
  const [inputs, setInputs] = useState<Inputs | null>(null);
  const [draft, setDraft] = useState<{ income: string; rate: string }>({ income: "", rate: "" });
  const [curve, setCurve] = useState<Answer<CurveResponse> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState<Answer<CheckOut> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let live = true;
    (async () => {
      const s = await apiSource();
      const session = await recordedSession().catch(() => null);
      if (!live) return;
      setSource(s);
      setPresets(session?.inputs ?? []);
      try {
        const h = await read<HealthResponse>("/v1/health", "health");
        const list = await read<MetrosResponse>("/v1/metros", "metros");
        if (!live) return;
        setHealth(h.body);
        setMetros(list.body.metros);
        const first = session?.inputs?.[0] ?? (list.body.metros[0] ? { cbsa_code: list.body.metros[0].cbsa_code, income: Math.round(list.body.metros[0].median_income / 1000) * 1000, down_share: 0.1, rate: null, horizon_years: 30 } : null);
        if (first) {
          setInputs(first);
          setDraft({ income: String(first.income), rate: first.rate === null ? "" : String(first.rate) });
        }
      } catch (err) {
        if (live) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!inputs) return;
    let live = true;
    setCurve(null);
    setError(null);
    getCurve(inputs).then(
      (answer) => {
        if (live) {
          setCurve(answer);
          markReady();
        }
      },
      (err: unknown) => {
        if (live) setError(err instanceof Error ? err.message : String(err));
      },
    );
    return () => {
      live = false;
    };
  }, [inputs]);

  const recordedOnly = source === "recorded";
  const metro = metros.find((x) => x.cbsa_code === inputs?.cbsa_code);
  const update = (patch: Partial<Inputs>) => setInputs((i) => (i ? { ...i, ...patch } : i));
  const commitDraft = () => {
    const income = Number(draft.income.replace(/[^0-9.]/g, ""));
    const rate = draft.rate.trim() === "" ? null : Number(draft.rate);
    if (!Number.isFinite(income) || income <= 0) return;
    update({ income: Math.round(income), rate: rate !== null && Number.isFinite(rate) ? rate : null });
  };
  const save = async () => {
    if (!inputs) return;
    setSaving(true);
    try {
      setSaved(await saveCheck(inputs, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };
  const answer = curve?.body;
  const points = answer?.points ?? [];
  const breakeven = answer?.breakeven_years ?? null;

  return (
    <div className="space-y-5" data-testid="planner">
      <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="api-status">
        {source === null ? <span className="text-ink2">Asking the API whether it is awake</span> : null}
        {source === "live" ? <span className="font-semibold">Live API{health ? `, marts ${health.model_version}, prices through ${health.latest_period}` : ""}</span> : null}
        {source === "recorded" ? (
          <Status kind="warning" testId="recorded-label">
            Recorded session: the API is asleep, so these answers were recorded against the live API earlier
          </Status>
        ) : null}
      </div>
      <div className="card p-4 grid grid-cols-2 md:grid-cols-5 gap-3 items-end" data-testid="planner-form">
        {recordedOnly ? (
          <label className="flex flex-col text-xs text-ink2 gap-1 col-span-2 md:col-span-5">
            Recorded inputs
            <select
              className="text-sm"
              data-testid="pick-preset"
              value={inputs ? presets.findIndex((p) => sameInputs(p, inputs)) : -1}
              onChange={(e) => {
                const p = presets[Number(e.target.value)];
                if (p) {
                  setInputs(p);
                  setDraft({ income: String(p.income), rate: p.rate === null ? "" : String(p.rate) });
                }
              }}
            >
              {presets.map((p, i) => (
                <option key={`${p.cbsa_code}-${i}`} value={i}>
                  {`${metros.find((x) => x.cbsa_code === p.cbsa_code)?.cbsa_title ?? p.cbsa_code}, income ${formatValue(p.income, "usd0")}, ${formatValue(p.down_share, "pct0")} down, ${p.rate === null ? "default rate" : `${p.rate} percent`}, ${p.horizon_years} years`}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <label className="flex flex-col text-xs text-ink2 gap-1 col-span-2">
              Metro
              <select className="text-sm" data-testid="pick-metro" value={inputs?.cbsa_code ?? ""} onChange={(e) => update({ cbsa_code: e.target.value })}>
                {metros.map((x) => (
                  <option key={x.cbsa_code} value={x.cbsa_code}>
                    {x.cbsa_title}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Household income, per year
              <input
                type="text"
                inputMode="numeric"
                className="text-sm bg-raised border border-hairline rounded px-1 py-0.5"
                data-testid="pick-income"
                value={draft.income}
                onChange={(e) => setDraft((d) => ({ ...d, income: e.target.value }))}
                onBlur={commitDraft}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitDraft();
                }}
              />
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Rate, percent (blank for the latest week)
              <input
                type="text"
                inputMode="decimal"
                className="text-sm bg-raised border border-hairline rounded px-1 py-0.5"
                data-testid="pick-rate"
                value={draft.rate}
                placeholder={health?.rate_default ? String(health.rate_default) : ""}
                onChange={(e) => setDraft((d) => ({ ...d, rate: e.target.value }))}
                onBlur={commitDraft}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitDraft();
                }}
              />
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Down payment
              <select className="text-sm" data-testid="pick-down" value={inputs?.down_share ?? 0.1} onChange={(e) => update({ down_share: Number(e.target.value) })}>
                {DOWN_SHARES.map((d) => (
                  <option key={d} value={d}>
                    {formatValue(d, "pct0")}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Horizon
              <select className="text-sm" data-testid="pick-horizon" value={inputs?.horizon_years ?? 30} onChange={(e) => update({ horizon_years: Number(e.target.value) })}>
                {HORIZONS.map((h) => (
                  <option key={h} value={h}>
                    {h} years
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
      {error ? (
        <p className="text-sm" role="alert" data-testid="planner-error">
          {error}
        </p>
      ) : null}
      {answer ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="planner-answer">
          <div className="card p-4">
            <p className="text-xs text-ink2">Payment share of income</p>
            <p className="text-2xl font-bold num" data-testid="answer-share">
              {formatValue(answer.payment_share, "pct1")}
            </p>
            <p className="text-xs text-ink2">
              {formatValue(answer.payment, "usd0")} a month on the median home, {formatValue(answer.median_home, "usd0")} in {answer.quarter}; the line is {formatValue(line, "pct0")}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-ink2">Affordable price at the line</p>
            <p className="text-2xl font-bold num" data-testid="answer-price">
              {formatValue(answer.affordable_price, "usd0")}
            </p>
            <p className="text-xs text-ink2">{answer.affordable_price >= answer.median_home ? "at or above the median home" : "below the median home"}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-ink2">Households that can afford the median home</p>
            <p className="text-2xl font-bold num" data-testid="answer-afford">
              {answer.affordable_share === null ? "not computed" : formatValue(answer.affordable_share, "pct0")}
            </p>
            <p className="text-xs text-ink2">of households in the metro, from the census income brackets</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-ink2">Buying beats renting after</p>
            <p className="text-2xl font-bold num" data-testid="answer-breakeven">
              {breakeven === null ? "no history" : breakeven > answer.horizon_years ? `more than ${answer.horizon_years} years` : formatValue(breakeven, "years1")}
            </p>
            <p className="text-xs text-ink2">
              {answer.breakeven_low !== null && answer.breakeven_high !== null ? `interval ${formatValue(answer.breakeven_low, "years0")} to ${answer.breakeven_high > answer.horizon_years ? "beyond the horizon" : formatValue(answer.breakeven_high, "years0")}` : ""}
            </p>
          </div>
        </div>
      ) : null}
      <Figure
        testId="planner-curve"
        message={
          answer
            ? breakeven !== null && breakeven <= answer.horizon_years
              ? `In ${metro?.cbsa_title ?? answer.cbsa_code}, owning catches up with renting after ${formatValue(breakeven, "years1")} at ${formatValue(answer.rate, "rate2")}`
              : `In ${metro?.cbsa_title ?? answer.cbsa_code}, owning does not catch up with renting inside ${answer.horizon_years} years at ${formatValue(answer.rate, "rate2")}`
            : "Rent or buy"
        }
        subtitle="Renter wealth less owner equity by year under the metro's median appreciation and rent growth; the interval comes from its own history"
        source={`Source: ${curve?.source === "recorded" ? "the recorded session" : "the live API"} over the committed calculator marts.`}
        sql={null}
        table={answer ? { columns: ["Year", "Renter wealth less owner equity", "Owner equity", "Renter wealth", "Home value"], formats: ["int", "susd0", "usd0", "usd0", "usd0"], rows: points.map((p) => [p.year, p.difference, p.owner_equity, p.renter_wealth, p.home_value]) } : null}
      >
        {answer ? (
          <LineChart
            series={[{ key: "diff", name: "Renter wealth less owner equity", color: "var(--cat-2)", points: points.map((p) => ({ x: p.year, y: p.difference })) }]}
            xFmt="int"
            yFmt="susd0"
            xLabel="Years of ownership"
            yLabel="Dollars, positive means renting is ahead"
            hRules={[{ y: 0, label: "owning catches up", color: "var(--cat-1)" }]}
            vRules={breakeven !== null && breakeven <= answer.horizon_years ? [{ x: breakeven, label: `breakeven ${formatValue(breakeven, "years1")}`, color: "var(--ink)" }] : []}
          />
        ) : (
          <ChartSkeleton shape="lines" />
        )}
      </Figure>
      <div className="card p-4 space-y-3" data-testid="save-check">
        <p className="text-sm">
          Save this check through the API. The log stores the metro code, the income rounded to the nearest thousand, the down payment share, the rate
          and the horizon, nothing else, and scores the check when the next quarter of prices and rates publishes.
        </p>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="password"
            className="text-sm bg-raised border border-hairline rounded px-2 py-1"
            placeholder="write token"
            aria-label="write token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            data-testid="token"
          />
          <button type="button" onClick={save} disabled={saving || !inputs} className="text-sm px-3 py-1.5 rounded bg-ink text-surface disabled:opacity-60" data-testid="save">
            {saving ? "Saving" : "Save this check"}
          </button>
        </div>
        {saved ? (
          <p className="text-sm" data-testid="saved">
            {saved.source === "live" ? "Saved" : "Recorded"} check <code className="mono">{saved.body.check_id}</code>: payment share {formatValue(saved.body.payment_share, "pct1")}, affordable price{" "}
            {formatValue(saved.body.affordable_price, "usd0")}, breakeven {saved.body.breakeven_years === null ? "none" : formatValue(saved.body.breakeven_years, "years1")}, resting on{" "}
            {saved.body.quarter}.{saved.reason ? ` (${saved.reason})` : ""}
          </p>
        ) : null}
      </div>
    </div>
  );
}
