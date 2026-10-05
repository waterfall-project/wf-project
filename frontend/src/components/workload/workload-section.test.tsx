// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import type { WorkloadPlan } from "./workload-chart";
import { type WorkloadRead, WorkloadSection, type WorkloadSectionProps } from "./workload-section";

type Revision = components["schemas"]["Revision"];
type OrgNode = components["schemas"]["OrgNode"];

const WORKLOAD = example("workload_marked_remaining") as WorkloadPlan;
const MARKED = (example("revisions_marked") as { items: Revision[] }).items;
const ORG_NODES = example("org_nodes") as OrgNode[];
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";

/** The workload of the witness project, its roles left out: an answer without a role to show. */
const EMPTY: WorkloadRead = { kind: "read", data: { ...WORKLOAD, roles: [] } };
/** The workload of the witness project, each role kept without a month: no load either. */
const MONTHLESS: WorkloadRead = {
  kind: "read",
  data: { ...WORKLOAD, roles: WORKLOAD.roles.map((role) => ({ ...role, months: [] })) },
};

/** What a section says, its tags left out, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render a section in English, the props of the witness project unless given. */
function section(props: Partial<WorkloadSectionProps>): string {
  const node: ReactNode = (
    <WorkloadSection
      workload={{ kind: "read", data: WORKLOAD }}
      asked={{ basis: "marked_remaining", revision: undefined, orgNode: undefined }}
      bases={["reference_budget", "marked_remaining", "current_remaining"]}
      marked={MARKED}
      orgNodes={ORG_NODES}
      address={{ pathname: "/workload", parameters: [] }}
      project={{ label: "Modernisation du poste de commande", code: "PRJ-001" }}
      shown={undefined}
      {...props}
    />
  );
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {node}
    </NextIntlClientProvider>,
  );
}

describe("the workload section", () => {
  it("is a region named by its label, not by an identifier of useId", () => {
    expect(section({})).toMatch(/^<section aria-label="Project workload"/);
  });

  it("says a marked revision without a version name so, never the revision under way", () => {
    const [reference, ...others] = MARKED;
    if (reference === undefined) {
      throw new Error("the example lists no marked revision");
    }
    const unnamed = { ...reference, version_name: null };
    const page = section({ marked: [unnamed, ...others] });
    expect(page).toMatch(/<option value="[^"]*101"[^>]*>Unnamed marked revision<\/option>/);
    expect(text(page)).toContain(
      "Basis: Remaining of a marked revision — revision “Unnamed marked revision”",
    );
  });

  it("names unnamed a revision of the calculation the screen did not read, under way said so", () => {
    expect(text(section({ marked: [] }))).toContain("— revision “unnamed”");
    const current = example("workload") as WorkloadPlan;
    expect(text(section({ workload: { kind: "read", data: current }, marked: [] }))).toContain(
      "— revision “Current revision”",
    );
  });

  it("says that no role has a load on the basis, or of the node filtered, rather than an empty chart", () => {
    expect(text(section({ workload: EMPTY }))).toContain("No role has a load on this basis.");
    const filtered = text(
      section({
        workload: EMPTY,
        asked: { basis: "marked_remaining", revision: undefined, orgNode: ORG_NODE },
      }),
    );
    expect(filtered).toContain(
      "No role of the node “Bureau d&#x27;études électricité” has a load on this basis.",
    );
    expect(filtered).not.toContain("Load by role and by month");
  });

  it("says no load when its roles have no month, rather than an empty chart", () => {
    expect(WORKLOAD.roles.length).toBeGreaterThan(0);
    const said = text(section({ workload: MONTHLESS }));
    expect(said).toContain("No role has a load on this basis.");
    expect(said).not.toContain("Load by role and by month");
  });

  it("says a node it does not know unknown rather than its identifier", () => {
    const page = text(
      section({
        workload: EMPTY,
        asked: { basis: "marked_remaining", revision: undefined, orgNode: "elsewhere" },
      }),
    );
    expect(page).toContain("No role of the node “unknown node” has a load on this basis.");
  });

  it("lists the nodes in the order of the tree the API gives, each set in by its depth, the root not at all", () => {
    const page = section({});
    const labels = [...page.matchAll(/<option value="01926f3a[^"]*47\d"[^>]*>(.*?)<\/option>/g)];
    expect(labels.map((match) => match[1])).toEqual([
      "Direction technique",
      "\u2003Bureau d&#x27;études électricité",
      "\u2003\u2003Atelier de câblage",
      "\u2003Service des achats",
    ]);
    expect(page).toContain("Organisation node and its descendants");
  });
});
