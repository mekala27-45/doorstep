import type { Metadata } from "next";

import { ManifestTable } from "@/components/ManifestTable";
import { MarkReady } from "@/components/MarkReady";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

export const metadata: Metadata = { title: "Who still buys" };

export default function BuyersPage() {
  const m = manifest();
  const spec = chart("buyers");
  return (
    <>
      <MarkReady />
      <PageHeader kicker="Who still buys" question="Who gets a mortgage now, compared with 2019?">
        <p>
          From the purchase subset of the HMDA extract: the median purchase borrower&apos;s income as a ratio of the metro median household income by
          year, the share of purchase loans to borrowers under 35, the share with income above twice the metro median, the median property value to
          borrower income, and the rate spread distribution. Intervals are by bootstrap over lenders. The denial question is not asked; fair lending is
          another build, and the statement says so.
        </p>
      </PageHeader>
      <SpecFigure spec={spec} callout={m.figure("chart.buyers").callout} testId="buyers-chart" />
      <Section title="By year" id="buyers-year">
        <ManifestTable m={m} tableKey="ch6.by_year" testId="buyers-table" />
      </Section>
      <Section title="The largest metros" id="buyers-metros" intro={<p>The borrower income ratio in {m.vOr("ch6.base_year", "")} and {m.vOr("ch6.latest_year", "")} with the lender bootstrap interval, and the share of buyers under 35.</p>}>
        <ManifestTable m={m} tableKey="ch6.largest_metros" testId="buyers-metros" />
      </Section>
      <Section title="The extract and the rounding rules, in plain words" id="buyers-rules">
        <div className="prose space-y-3">
          <p>
            The extract holds originated loans (action taken 1) for home purchase, refinance and cash out refinance (loan purposes 1, 31 and 32) from the
            public snapshot files, {m.vOr("data.hmda.first_year", "2018")} to {m.vOr("data.hmda.last_year", "the latest year")}; at ingest the rows are
            narrowed to principal residences, and reverse mortgages, open end lines and business purpose loans are flagged. This page reads the purchase
            subset only. The lenders report income in thousands of dollars, the loan amount and the property value at the midpoint of their reporting
            bins, and the applicant age in bands; the chapter reads histograms per lender in five thousand dollar bins, so no loan row is ever held
            by the site and the median is exact to the bin.
          </p>
          <p>
            Spread: p10 {m.vOr("ch6.latest.spread.p10", "")}, p50 {m.vOr("ch6.latest.spread.p50", "")}, p90 {m.vOr("ch6.latest.spread.p90", "")} in{" "}
            {m.vOr("ch6.latest_year", "")}. Plan <code className="mono">{m.vOr("ch6.plan_hash", "")}</code>. {m.vOr("ch6.method.interval", "")}.
          </p>
        </div>
      </Section>
      <Pushback>
        <p>{m.vOr("ch6.pushback", "")}</p>
      </Pushback>
    </>
  );
}
