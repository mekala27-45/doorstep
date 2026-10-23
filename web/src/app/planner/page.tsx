import type { Metadata } from "next";

import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

import { PlannerClient } from "./PlannerClient";

export const metadata: Metadata = { title: "The affordability calculator" };

export default function PlannerPage() {
  const m = manifest();
  return (
    <>
      <PageHeader kicker="The affordability calculator" question="What can a household afford here, and when does buying beat renting?">
        <p>
          Pick a metro, type an income, choose a down payment, a rate and a horizon. The calculator answers with the payment on the median home as a
          share of that income, the price the income can carry at the {m.vOr("policy.affordable_line", "thirty percent")} line, the share of households
          in the metro that can afford the median home, and the rent or buy breakeven with the interval the metro&apos;s own history gives it. The
          rate defaults to the latest Freddie Mac week ({m.vOr("calculator.rate_default", "")}, {m.vOr("calculator.rate_default_source", "")}); prices rest
          on {m.vOr("calculator.latest_period", "the latest quarter")} and incomes on the {m.vOr("calculator.income_year", "latest")} census release.
        </p>
        <p className="text-sm text-ink2">
          The answers come from the live API. Its instance stops when idle and starts again on the first request; the page asks twice, and if it
          is still starting it answers from a session recorded against the live API and says so.
        </p>
      </PageHeader>
      <PlannerClient line={m.has("policy.affordable_line") ? m.num("policy.affordable_line") : 0.3} />
      <Section title="The rent or buy decision across metros" id="decision">
        <SpecFigure spec={chart("decision")} callout={m.figure("chart.decision").callout} testId="decision-chart" />
      </Section>
      <Pushback>
        <p>{m.vOr("ch8.pushback", "")}</p>
      </Pushback>
    </>
  );
}
