import type { Metadata } from "next";

import { ManifestTable } from "@/components/ManifestTable";
import { MarkReady } from "@/components/MarkReady";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

export const metadata: Metadata = { title: "The two shocks" };

export default function ShocksPage() {
  const m = manifest();
  return (
    <>
      <MarkReady />
      <PageHeader kicker="The two shocks" question="What the rate shock did to the payment and to turnover, and what the migration shock did to prices.">
        <p>
          Two event studies. The payment on the same home, quarter by quarter from 2019, split exactly into the part the price moved and the part the
          rate moved; the rate part overtook the price part in {m.vOr("ch2.overtaking_quarter", "")}. Then the lock in: originations of 2019 to 2021 under
          four percent per hundred owner households, and what turnover did where owners had the most to lose, with the pre period placebo beside it.
          And the migration shock: price growth over {m.vOr("ch7.window", "")} against the pandemic migration shock per hundred residents, with the
          placebo on {m.vOr("ch7.placebo_window", "")} and three synthetic controls.
        </p>
      </PageHeader>
      <Section title="The rate shock" id="rate-shock">
        <SpecFigure spec={chart("rate_shock")} callout={m.figure("chart.rate_shock").callout} testId="shock-decomposition" />
      </Section>
      <Section
        title="The lock in"
        id="lock-in"
        intro={
          <p>
            Each point of lock in: {m.vOr("ch2.lock_in.coef", "")} purchases per hundred owners ({m.vOr("ch2.lock_in.low", "")} to {m.vOr("ch2.lock_in.high", "")});
            placebo {m.vOr("ch2.placebo.coef", "")} ({m.vOr("ch2.placebo.low", "")} to {m.vOr("ch2.placebo.high", "")}); {m.vOr("ch2.metros", "")} metros,{" "}
            {m.vOr("ch2.clusters", "")} state clusters. Plan <code className="mono">{m.vOr("ch2.plan_hash", "")}</code>.
          </p>
        }
      >
        <SpecFigure spec={chart("lock_in")} callout={m.figure("chart.rate_shock.lock_in").callout} testId="shock-lock-in" />
        <div className="mt-5">
          <ManifestTable m={m} tableKey="ch2.threshold_interior" testId="lock-in-interior" />
        </div>
      </Section>
      <Section
        title="The migration shock"
        id="migration"
        intro={
          <p>
            {m.vOr("ch7.coef", "")} price growth over the window per person gained per hundred residents beyond the pre pandemic pace ({m.vOr("ch7.low", "")} to{" "}
            {m.vOr("ch7.high", "")}); placebo {m.vOr("ch7.placebo.coef", "")} ({m.vOr("ch7.placebo.low", "")} to {m.vOr("ch7.placebo.high", "")}); {m.vOr("ch7.metros", "")}{" "}
            metros, {m.vOr("ch7.clusters", "")} state clusters. Plan <code className="mono">{m.vOr("ch7.plan_hash", "")}</code>.
          </p>
        }
      >
        <SpecFigure spec={chart("migration")} callout={m.figure("chart.migration").callout} testId="shock-migration" />
        <div className="mt-5 space-y-5">
          <ManifestTable m={m} tableKey="ch7.regression" testId="migration-regression" />
          <ManifestTable m={m} tableKey="ch7.synthetic_controls" testId="migration-synthetic" />
        </div>
      </Section>
      <Section title="Proven on the simulator first" id="shocks-recovery">
        <div className="prose space-y-3">
          <p>
            The lock in difference in differences recovered the planted response with a mean bias of {m.vOr("recovery.lock_in_did.mean_bias", "")} and
            interval coverage of {m.vOr("recovery.lock_in_did.mean_coverage", "")} across conditions. The migration estimator&apos;s bias was{" "}
            {m.vOr("recovery.migration.none.bias", "")} with no reverse causality, {m.vOr("recovery.migration.mild.bias", "")} with mild and{" "}
            {m.vOr("recovery.migration.strong.bias", "")} with strong, where the placebo flagged the condition {m.vOr("recovery.migration.strong.flag_rate", "")} of
            the time: that is the limit this chapter admits in print.
          </p>
        </div>
      </Section>
      <Pushback>
        <p>{m.vOr("ch2.pushback", "")}</p>
        <p>{m.vOr("ch7.pushback", "")}</p>
      </Pushback>
    </>
  );
}
