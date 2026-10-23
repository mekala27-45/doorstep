import type { Metadata } from "next";

import { ManifestTable } from "@/components/ManifestTable";
import { MarkReady } from "@/components/MarkReady";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

export const metadata: Metadata = { title: "The fair ranking" };

export default function RankPage() {
  const m = manifest();
  const spec = chart("ranking");
  return (
    <>
      <MarkReady />
      <PageHeader kicker="The fair ranking" question="Which metros are the least affordable, once you hold constant what people earn there?">
        <p>
          The raw ranking sorts metros by the price of the median home. The adjusted ranking sorts them by the payment on that home as a share of
          the local median household income, so a metro where homes are expensive because incomes are high is compared on what its own households
          face. Every rank carries an interval from {m.vOr("ch5.draws", "ten thousand")} Monte Carlo draws over the census margins of error, with
          the index held fixed; {m.vOr("ch5.metros_ranked", "")} metropolitan areas are ranked in {m.vOr("ch5.year", "")} and{" "}
          {m.vOr("ch5.micropolitan_excluded", "")} micropolitan areas are excluded, because the one year release reaches only the largest of them.
        </p>
      </PageHeader>
      <SpecFigure spec={spec} callout={m.figure("chart.ranking").callout} testId="rank-slope" />
      <Section title="The largest metros, raw beside adjusted" id="rank-table">
        <ManifestTable m={m} tableKey="ch5.largest" testId="rank-table" />
      </Section>
      <Section title="The specification" id="rank-model">
        <div className="prose space-y-3">
          <p>{m.vOr("ch5.method.estimator", "")} {m.vOr("ch5.method.interval", "")}.</p>
          <p>
            Plan <code className="mono">{m.vOr("ch5.plan_hash", "")}</code>, registered before the estimate ran on the real metros. The rank correlation
            between the raw and adjusted rankings is {m.vOr("ch5.spearman", "")}; the mean absolute rank change is {m.vOr("ch5.mean_abs_rank_change", "")}{" "}
            places and the largest is {m.vOr("ch5.max_rank_change", "")}, for {m.vOr("ch5.biggest_mover", "")} (from {m.vOr("ch5.biggest_mover.raw_rank", "")} to{" "}
            {m.vOr("ch5.biggest_mover.adjusted_rank", "")}). The affordable share, the share of local households whose income clears the payment on the
            median home at the {m.vOr("policy.affordable_line", "thirty percent")} line, runs from {m.vOr("ch5.affordable_share.min", "")} to{" "}
            {m.vOr("ch5.affordable_share.max", "")} across the {m.vOr("ch5.affordable_share.metros", "")} metros with income brackets, median{" "}
            {m.vOr("ch5.affordable_share.median", "")}.
          </p>
        </div>
      </Section>
      <Section title="Proven on the simulator first" id="rank-recovery">
        <div className="prose space-y-3">
          <p>
            On simulated metros where the true payment share ranking is known and the expensive metros are given the high incomes on purpose, the
            adjusted ranking&apos;s rank correlation with the truth averaged {m.vOr("recovery.ranking.adjusted", "")} against{" "}
            {m.vOr("recovery.ranking.raw", "")} for the raw ranking, over {m.vOr("recovery.conditions", "")} conditions and {m.vOr("recovery.seeds", "")} seeds
            each. The bracket interpolation behind the affordable share missed the exact share by {m.vOr("recovery.bracket_interpolation.mean_bias", "")} on
            average.
          </p>
        </div>
      </Section>
      <Pushback>
        <p>{m.vOr("ch5.pushback", "")}</p>
      </Pushback>
    </>
  );
}
