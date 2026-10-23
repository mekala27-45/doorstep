import type { Metadata } from "next";

import { PageHeader, Pushback } from "@/components/Section";
import { manifest } from "@/lib/load";

import { ExploreClient } from "./ExploreClient";

export const metadata: Metadata = { title: "Explore" };

export default function ExplorePage() {
  const m = manifest();
  return (
    <>
      <PageHeader kicker="The explorer" question="Pick a metro and see what its prices, incomes, rents, permits, people and buyers did.">
        <p>
          Every chart on this page is a query over the marts the warehouse published, run in your browser with DuckDB. Change the metro and every
          chart reruns; the SQL behind each one is under its button, and the box at the bottom takes your own.
        </p>
        <p className="text-ink2 text-sm">
          Prices run from {m.vOr("data.window.start_year", "2000")} to {m.vOr("data.fhfa.latest_period", "the latest quarter")}; the census measures from{" "}
          {m.vOr("data.acs.first_year", "2005")} to {m.vOr("data.acs.last_year", "the latest release")} with no 2020 release, so every line breaks there; loans from{" "}
          {m.vOr("data.hmda.first_year", "2018")}. Micropolitan areas are in the marts and in the SQL box; the picker lists the metropolitan areas.
        </p>
      </PageHeader>
      <ExploreClient line={m.has("policy.affordable_line") ? m.num("policy.affordable_line") : 0.3} />
      <Pushback>
        <p>
          A metro chart is only as good as the survey behind it, and a small metro in the one year release carries a wide margin; the table toggle
          under every chart gives the numbers behind each point, and the manifest carries the margins the chapters propagate. The anchored price is
          the regulator&apos;s index moved from the census median value of {m.vOr("chapters.anchor_year", "the anchor year")}, so a metro whose owners
          report their homes high in that year sits high in every year, which is why the anchor sensitivity table is on the data page.
        </p>
      </Pushback>
    </>
  );
}
