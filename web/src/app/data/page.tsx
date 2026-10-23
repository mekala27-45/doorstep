import type { Metadata } from "next";

import { ManifestTable } from "@/components/ManifestTable";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { bundle, manifest } from "@/lib/load";
import { REPO } from "@/lib/site";

import { QuarantineByYear, RecoveryMultiples } from "./DataClient";

export const metadata: Metadata = { title: "The warehouse" };

export default function DataPage() {
  const m = manifest();
  const b = bundle();
  const recovery = m.has("recovery.by_condition") ? m.table("recovery.by_condition") : null;
  const exports: [string, string, string][] = [
    ["The workbook with live formulas", "exports/workbook.xlsx", "Pick a metro on the Model sheet and type an income, a rate and a down payment; PMT and lookup formulas produce the payment, the payment share, the affordable price and a 360 row amortisation table. LibreOffice recalculates it in the tests against the calculator for three metros."],
    ["The Tableau extracts and view specification", "exports/tableau/workbook_spec.md", "The metro by year and metro by quarter marts, the ranking, the burden bands and the supply cells as CSV, with the five views the companion workbook shows."],
    ["The Power BI model specification", "exports/powerbi/model_spec.md", "Tables, relationships and DAX measures (payment share, price to income, affordable share, cost burdened share, permits per hundred households, lock in share, turnover) as text."],
    ["The CSV bundle and its dictionary", "exports/csv/data_dictionary.csv", "Every chapter table as CSV, with every column named."],
  ];
  return (
    <>
      <PageHeader kicker="The warehouse" question="Where every number comes from, and how it was checked.">
        <p>
          Prices from {m.vOr("data.window.start_year", "2000")} to {m.vOr("data.fhfa.latest_period", "the latest quarter")}, every census one year release from{" "}
          {m.vOr("data.acs.first_year", "2005")} to {m.vOr("data.acs.last_year", "the latest")} (none in 2020), rents and income limits from HUD, weekly rates
          from Freddie Mac through {m.vOr("data.pmms.latest_week", "the latest week")}, permits and population by county from {m.vOr("data.window.start_year", "2000")},
          and {m.vOr("data.hmda.rows_in_analysis", "every")} loans from the HMDA extract, {m.vOr("data.hmda.first_year", "2018")} to {m.vOr("data.hmda.last_year", "the latest year")},
          went through named quarantine rules (flagged and counted, nothing deleted) and {m.vOr("data.omb.vintages", "")} delineation vintages into a dbt warehouse of{" "}
          {m.vOr("warehouse.models", "")} models and {m.vOr("warehouse.tests", "")} tests. The metric layer defines each of {m.vOr("metrics.count", "")} metrics once over the
          finest grain and once over the shipped mart and compares them at {m.vOr("metrics.grains", "")} grains: {m.vOr("metrics.disagreements", "")} disagreements.
        </p>
      </PageHeader>
      <Section title="The quarantine report" id="quarantine">
        <ManifestTable m={m} tableKey="data.quarantine.by_rule" testId="quarantine-table" />
        <div className="mt-5">
          <QuarantineByYear />
        </div>
      </Section>
      <Section title="The delineation crosswalk" id="geography" intro={<p>Every source is mapped to its area through the delineation vintage in force when it was published; the warehouse carries each area under its latest code with the earlier codes as aliases. {m.vOr("data.omb.vintages", "")} vintages, the latest {m.vOr("data.omb.latest_vintage", "")}; the crosswalk tests prove every county maps to one area per vintage.</p>}>
        {m.has("data.omb.crosswalk") ? <ManifestTable m={m} tableKey="data.omb.crosswalk" testId="crosswalk-table" /> : <p className="text-sm text-ink2">The crosswalk counts are in the geography document.</p>}
      </Section>
      <Section title="The metric layer, reconciled" id="metrics" intro={<p>{m.vOr("metrics.cells", "")} cells compared across {m.vOr("metrics.grains", "")} grains, {m.vOr("metrics.disagreements", "")} disagreements.</p>}>
        <ManifestTable m={m} tableKey="metrics.definitions" testId="metrics-table" />
      </Section>
      <Section title="The anchor sensitivity" id="anchor" intro={<p>Every headline of chapter one re-anchored in each neighbour of the chosen year; the word degenerate marks a neighbour where the headline turns.</p>}>
        <ManifestTable m={m} tableKey="ch1.anchor_sensitivity" testId="anchor-table" />
      </Section>
      <Section title="The recovery study" id="recovery" intro={<p>Every estimator, run on simulated metros where the truth is known, {m.vOr("recovery.conditions", "")} conditions with {m.vOr("recovery.seeds", "")} seeds each, before it touched a real metro. The condition with strong reverse causality is drawn in clay; it is where the migration chapter admits its limit.</p>}>
        <ManifestTable m={m} tableKey="recovery.by_estimator" testId="recovery-estimators" />
        <div className="mt-5">{recovery ? <RecoveryMultiples rows={recovery.rows} source={m.prov("recovery.by_condition")} /> : null}</div>
      </Section>
      <Section title="The data dictionary" id="dictionary">
        <div className="card p-4 overflow-x-auto" data-testid="dictionary">
          <table className="data-table">
            <thead>
              <tr>
                <th>Published file</th>
                <th className="num">Bytes</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(b.files).map(([file, bytes]) => (
                <tr key={file}>
                  <td className="mono">{file}</td>
                  <td className="num">{bytes.toLocaleString("en-US")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink2">
            Every column of every exported table is named in{" "}
            <a className="underline" href={`${REPO}/blob/main/exports/csv/data_dictionary.csv`}>
              the CSV bundle&apos;s dictionary
            </a>
            , and every definition is in{" "}
            <a className="underline" href={`${REPO}/blob/main/docs/definitions.md`}>
              docs/definitions.md
            </a>
            .
          </p>
        </div>
      </Section>
      <Section title="Exports and the BI companions" id="exports">
        <ul className="space-y-3" data-testid="exports">
          {exports.map(([label, path, note]) => (
            <li key={path} className="card p-4">
              <a className="font-semibold underline" href={`${REPO}/blob/main/${path}`}>
                {label}
              </a>
              <p className="text-sm text-ink2 mt-1">{note}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Pushback>
        <p>
          A warehouse can agree with itself and still be wrong about the world. The reconcile proves that two expressions over two grains give the
          same number; it cannot prove that owners reported their home values right or that a lender reported the income it used. That is why the
          quarantine rules flag a margin that exceeds its estimate, a jam value, a missing quarter and a loan with no rate rather than fixing them, and
          why every flagged row is counted here by source and year.
        </p>
      </Pushback>
    </>
  );
}
