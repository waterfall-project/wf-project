// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { nodeFieldNames } from "@/components/grid/nodes";
import { REMAINING_FIELDS } from "@/components/grid/remaining";
import type { RemainingGridProps } from "@/components/grid/remaining-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import { filtersOf, menuText } from "@/test/filter-menu";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import RemainingPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

// One client for the whole of a page, made at its first call.
vi.mock("@/api/server", () => ({
  serverClient: () => {
    const made = server.clients.at(-1);
    if (made !== undefined) {
      return made;
    }
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => SCREEN,
  useSearchParams: () => new URLSearchParams(),
}));
// The grid is rendered as it is, and what the page hands it is kept: the static markup of a closed menu
// does not say whether the sub-projects were given.
vi.mock("@/components/grid/remaining-grid", async (original) => {
  const actual = await original<typeof import("@/components/grid/remaining-grid")>();
  return {
    ...actual,
    RemainingGrid: (props: RemainingGridProps) => {
      handed.push(props);
      return actual.RemainingGrid(props);
    },
  };
});
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const handed = vi.hoisted((): RemainingGridProps[] => []);

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const INDICATORS = "GET /projects/{project_id}/remaining-indicators";
const REVISION_READ = "GET /projects/{project_id}/revisions/{revision_id}";
const STRUCTURES = "GET /projects/{project_id}/revisions/{revision_id}/structures";
// The lot of the witness and its post, as its work breakdown names them.
const LOT = "01926f3a-7c00-7000-8000-000000000711";
const ITEM = "01926f3a-7c00-7000-8000-000000000712";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render in English, as the shell hands its texts to a screen. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

/** The screen of the remaining to commit at the query given. */
async function remainingAt(search: Record<string, string> = {}) {
  return html(
    await RemainingPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

/** The query of the call of a route, as the client serialized it. */
function queryOf(route: string): Record<string, string> | undefined {
  const call = server.clients.flatMap((client) => client.calls).find((c) => c.route === route);
  return call === undefined ? undefined : Object.fromEntries(call.query);
}

/** The opening tag of the cell of a row, by its index among the rows, and of a column. */
function cellTag(page: string, row: number, column: string): string {
  const tags = page.match(/<td\b[^>]*>/g) ?? [];
  const found = tags.find(
    (tag) =>
      tag.includes(`data-row="${row.toString()}"`) && tag.includes(`data-column="${column}"`),
  );
  if (found === undefined) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The section a page names, from its opening tag to its end. */
function section(page: string, name: string): string {
  // The cards of figures, from the first one, which carries the name, to the grid that follows.
  const named = page.indexOf(`role="region" aria-label="${name}"`);
  const start = page.lastIndexOf("<div", named);
  return named < 0
    ? ""
    : page.slice(start, page.indexOf('aria-label="Remaining to commit grid"', start));
}

beforeEach(() => {
  handed.length = 0;
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /reference/settings": "reference_settings",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    [REVISION_READ]: "revision",
    [STRUCTURES]: "structures",
    [NODES]: "nodes_estimate",
    [INDICATORS]: "remaining_indicators",
    "GET /projects/{project_id}/work-breakdown": "work_breakdown",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
  };
});

describe("the screen of the remaining to commit", () => {
  it("names its function in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe(
      "Remaining to commit · Modernisation du poste de commande — Waterfall",
    );
  });

  it("reads the lines of the tasks started alone, the fields its grid shows, for the sub-project its banner shows alone, said to restrict the grid alone [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres — the sub-project, by
    // which the nodes are read and not the indicators, the chip saying so (#459); the date, which
    // no read of the screen takes, is not shown (#302).
    const page = await remainingAt({ subproject_id: SUBPROJECT, as_of: "2026-05-31" });
    const { fields, ...query } = queryOf(NODES) ?? {};
    expect(query).toEqual({ progress: "started", subproject_id: SUBPROJECT });
    expect(fields?.split(",").sort()).toEqual(nodeFieldNames(REMAINING_FIELDS).sort());
    const banner = page.slice(0, page.indexOf("</section>"));
    expect(text(banner)).toContain("Subproject: SP-CMD — Poste de commande, on the grid only");
    expect(text(banner)).not.toContain("Calculation date");
    expect(queryOf(INDICATORS)).toEqual({ revision_id: REVISION });
  });

  it("asks the tasks not started too when the address asks them, their lines then entered, and offers to show the started alone again [WF-RAE-0040-A]", async () => {
    // Les tâches non démarrées n'apparaissent qu'à la demande, et sont alors modifiables : a link
    // of the head asks them, and the lines of the mounting on site, not started, take a
    // re-estimation of their figures.
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;progress=not_started%2Cstarted"`,
    );
    expect(text(page)).toContain("Show the tasks not started too");

    server.clients = [];
    server.answers = { ...server.answers, [NODES]: "nodes_installation" };
    const shown = await remainingAt({ progress: "not_started,started", sort_by: "label" });
    expect(queryOf(NODES)?.progress).toBe("not_started,started");
    // The wiring on site, the first line of the mounting: its effort and its quantity entered.
    expect(cellTag(shown, 2, "hours")).not.toContain("aria-readonly");
    expect(cellTag(shown, 2, "quantity")).not.toContain("aria-readonly");
    expect(cellTag(shown, 2, "reestimated_amount")).toContain('aria-readonly="true"');
    expect(text(shown)).toContain("Show the started tasks only");
    expect(shown).toContain(`href="${SCREEN}?sort_by=label"`);

    // A state the contract does not know is not asked: the tasks started.
    server.clients = [];
    await remainingAt({ progress: "half_done" });
    expect(queryOf(NODES)?.progress).toBe("started");
  });

  it("asks no sort by the progress nor the finish of a task, which the server leaves in the order of the tree, and no header shows one (#526)", async () => {
    for (const sort_by of ["progress", "finish"]) {
      server.clients = [];
      const page = await remainingAt({ sort_by, sort_order: "desc" });
      expect(queryOf(NODES)?.sort_by).toBeUndefined();
      expect(queryOf(NODES)?.sort_order).toBeUndefined();
      expect(page).not.toContain("aria-sort");
    }
  });

  it("shows the indicators of the remaining to commit as the server gives them, dated, its deviations signed [WF-RAE-0020-A]", async () => {
    // Les écarts sont présents et signés. La couverture des risques présente la réserve de
    // référence, les provisions restantes, le coût des risques survenus et l'écart de couverture.
    const summary = section(await remainingAt(), "Remaining to commit indicators");
    expect(summary).toMatch(/Computed on <time dateTime="2026-06-03T14:05:00Z"/);
    expect(text(summary)).toContain(
      "Remaining to commit 67,497,090.97 Margin on the reference budget 1,406,335.39 " +
        "Deviation from the previous review -1,803,418.08 By cost type",
    );
    // Each amount bears the one mark of a computed value.
    expect(summary.match(/aria-label="Computed"/g)).toHaveLength(8);
    expect(text(summary)).toContain("Débours: €57,658,305.66 (85.42%)");
    expect(text(summary)).toContain(
      "Risk reserve 850,060.00 Remaining provisions 500,000.00 Cost of the occurred risks 200.00 reestimated Reestimated cost of the occurred risks (information) 200.00 Coverage variance 349,860.00",
    );
  });

  it("signals the scope outside the sub-projects over its budget in the zone the server classes it in, the others not, the deviations signed [WF-RAE-0020-A]", async () => {
    // Les écarts sont présents et signés. Un sous-projet dont le coût réel augmenté du reste à
    // engager dépasse son budget est signalé par la couleur, les autres non.
    // The remaining to commit had the risk of rework of the wiring been re-examined today at 60 %
    // instead of 40 %: its provision, which no sub-project bears, overruns the margin of the whole
    // outside the sub-projects alone; the two sub-projects keep theirs.
    server.answers = { ...server.answers, [INDICATORS]: "remaining_indicators_over_budget" };
    const markup = section(await remainingAt(), "Remaining to commit indicators");
    const summary = text(markup);
    expect(summary).toContain("Poste de commande: €23,322,741.24, margin €632,968.59");
    expect(summary).toContain("Essais et mise en service: €20,825,768.55, margin €612,061.48");
    expect(summary).toContain("No subproject: €23,598,581.18, margin -€88,694.68");
    // Each by the zone the server gives it, named: the whole outside the sub-projects alone is
    // over its budget, signalled; the two sub-projects within theirs are not.
    expect(
      [...markup.matchAll(/role="img" aria-label="(Alert|Nominal|Watch)"/g)].map((m) => m[1]),
    ).toEqual(["Nominal", "Nominal", "Alert"]);
    // The margin on the reference budget, in the sense of the balances: 250,000 less of it, the
    // provision the review adds.
    expect(summary).toContain("Margin on the reference budget 1,156,335.39");
    expect(summary).toContain("Deviation from the previous review -1,553,418.08");
  });

  it("says the indicators unavailable when the API does not find them, the grid shown", async () => {
    server.answers = {
      ...server.answers,
      [INDICATORS]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = await remainingAt();
    expect(text(page)).toContain("The remaining to commit indicators are unavailable.");
    expect(page).toContain('aria-label="Remaining to commit grid"');
  });

  it("leads to the imports and exports, in the same context, when the project lists the import of a remaining to commit (#521)", async () => {
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/exchanges?subproject_id=${SUBPROJECT}"`,
    );
    server.clients = [];
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    expect(await remainingAt()).not.toContain("/exchanges");
  });

  it("leads to the Kanban of the start of the tasks, in the same context", async () => {
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/kanban?subproject_id=${SUBPROJECT}"`,
    );
    expect(text(page)).toContain("Kanban — task start");
  });

  it("leads to the workload of the project on the remaining of the revision under way, in the same context [WF-DEV-0070-A]", async () => {
    const page = await remainingAt({ subproject_id: SUBPROJECT });
    expect(page).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/workload?subproject_id=${SUBPROJECT}&amp;basis=current_remaining"`,
    );
    expect(page).toContain('aria-label="Workload"');
  });

  it("places undo and redo in the remaining to commit of a revision in progress, and none in that of a marked one, whose marking nothing undoes [WF-IHM-0110-A]", async () => {
    // Aucune commande n'annule un marquage : the grid of a marked revision enters nothing.
    const open = await remainingAt();
    expect(open).toContain('aria-label="Undo"');
    expect(open).toContain('aria-label="Redo"');

    server.clients = [];
    server.answers = {
      ...server.answers,
      [REVISION_READ]: "revision_marked",
      [STRUCTURES]: "structures_amendments",
    };
    const marked = await remainingAt();
    expect(marked).not.toContain('aria-label="Undo"');
    expect(marked).not.toMatch(/<td(?![^>]*aria-readonly)[^>]*data-column=/);
  });

  it("is read only on a project that is not in progress, the structure listing the remaining to commit unavailable, and reads no category to create a line from [WF-RAE-0040-A]", async () => {
    // Sur un projet qui n'est pas En cours, la grille ne propose ni création ni suppression de
    // tâche ou de ligne : the structure says it (`project_in_progress` lacks), the front deduces
    // nothing from the state of the project.
    server.answers = { ...server.answers, [STRUCTURES]: "structures_without_tasks" };
    const page = await remainingAt();
    expect(page).not.toContain('aria-label="Undo"');
    expect(page).not.toMatch(/<td(?![^>]*aria-readonly)[^>]*data-column=/);
    const calls = server.clients.flatMap((client) => client.calls.map((call) => call.route));
    expect(calls).not.toContain("GET /reference/cost-categories");
    expect(calls).not.toContain("GET /reference/resource-roles");
  });

  it("opens the grid to entry on a project in progress, where tasks and lines are created and deleted, and reads the categories a line is created from", async () => {
    // The gestures themselves, in the menu of a cell, are proven on the grid
    // (`structure-gestures.dom.test.tsx`).
    const page = await remainingAt();
    expect(page).toContain('aria-label="Undo"');
    expect(page).toMatch(/<td(?![^>]*aria-readonly)[^>]*data-column=/);
    const calls = server.clients.flatMap((client) => client.calls.map((call) => call.route));
    expect(calls).toContain("GET /reference/cost-categories");
  });

  it("still hands the grid the lines of the answer, asking no kind, whatever the tasks beside them [WF-PLA-0080-A]", async () => {
    await remainingAt();
    expect(queryOf(NODES)).not.toHaveProperty("kinds");
    const items = handed[0]?.nodes.items ?? [];
    expect(items.some((row) => row.kind === "estimate_line")).toBe(true);
  });

  it("hands the grid the sub-projects of the project, with their codes, when the structure lists the remaining to commit available", async () => {
    await remainingAt();
    expect(handed).toHaveLength(1);
    expect(handed[0]?.subprojects).toEqual([
      { id: SUBPROJECT, label: "Poste de commande", code: "SP-CMD" },
      {
        id: "01926f3a-7c00-7000-8000-000000000802",
        label: "Essais et mise en service",
        code: "SP-ESS",
      },
    ]);
  });

  it("hands the grid no sub-project when the structure lists the remaining to commit unavailable, the grid read only", async () => {
    server.answers = { ...server.answers, [STRUCTURES]: "structures_without_tasks" };
    await remainingAt();
    expect(handed).toHaveLength(1);
    expect(handed[0]?.subprojects).toBeUndefined();
    expect(handed[0]?.editable).toBe(false);
  });

  it("hands the grid the type of the cost of the categories and the roles a line is created from [WF-DEV-0020-A]", async () => {
    await remainingAt();
    expect(handed[0]?.categories?.some(({ kind }) => kind === "non_labor")).toBe(true);
    expect(handed[0]?.categories?.some(({ kind }) => kind === "labor")).toBe(true);
    expect(handed[0]?.categories?.every(({ kind }) => kind !== undefined)).toBe(true);
    expect(handed[0]?.roles?.map(({ label }) => label)).toContain("Ingénieur électricien");
    const calls = server.clients.flatMap((client) => client.calls.map((call) => call.route));
    expect(calls).toContain("GET /reference/resource-roles");
  });

  it("hands the grid no role when the API refuses the list, the grid still entered [WF-DEV-0020-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/resource-roles": { problem: { code: "PERMISSION_MISSING", status: 403 } },
    };
    await remainingAt();
    expect(handed).toHaveLength(1);
    expect(handed[0]?.roles).toBeUndefined();
    expect(handed[0]?.categories).toBeDefined();
    expect(handed[0]?.editable).toBe(true);
  });

  it("hands the grid no sub-project when the API refuses the list, the grid still entered", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/subprojects": {
        problem: { code: "NOT_FOUND", status: 404 },
      },
    };
    await remainingAt();
    expect(handed).toHaveLength(1);
    expect(handed[0]?.subprojects).toBeUndefined();
    expect(handed[0]?.editable).toBe(true);
  });

  it("offers the filter by a lot or a post, read from the work breakdown whole, as the planning and the estimate do", async () => {
    // Le lot ou le poste porté par une tâche rattachée : the server retains its subtree and its
    // ancestors, the banner says the filter restricts the grid alone.
    const page = await remainingAt({ order_item_id: ITEM });
    expect(menuText(page, "Work package or order item")).toBe("Order item: Poste 1.1");
    expect(filtersOf(handed[0]).breakdown?.items.map((item) => item.id)).toEqual([LOT, ITEM]);
    expect(queryOf(NODES)).toMatchObject({ progress: "started", order_item_id: ITEM });
    expect(text(page.slice(0, page.indexOf("</section>")))).toContain(
      "Order item: Poste 1.1, on the grid only",
    );
    expect(queryOf(INDICATORS)).toEqual({ revision_id: REVISION });
  });

  it("opens without the filter when the API refuses the work breakdown, the grid read whole", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/work-breakdown": {
        problem: { code: "VALIDATION_FAILED", status: 422 },
      },
    };
    const page = await remainingAt();
    expect(page).not.toContain("Work package or order item");
    expect(queryOf(NODES)?.order_item_id).toBeUndefined();
  });

  it("reads the main structure alone, whatever structure the address names, and offers no other", async () => {
    // The remaining to commit is the main structure of the current revision, read by its
    // re-estimated amounts: a differential or the own estimate of a risk has none (WF-RAE-0040).
    const page = await remainingAt({ structure: "01926f3a-7c00-7000-8000-000000000203" });
    const nodes = server.clients
      .flatMap((client) => client.calls)
      .find((call) => call.route === NODES);
    expect(nodes?.path).toContain("/structures/01926f3a-7c00-7000-8000-000000000201/nodes");
    expect(page).not.toContain("Change the structure");
    expect(page).not.toContain("Avenant 2");
  });
});

describe("the note of the fake back on the remaining to commit", () => {
  it("shows none: the service serves the screen, its grid and its indicators", async () => {
    const page = await remainingAt();
    expect(page).not.toContain('role="note"');
    expect(page).not.toContain("Filters, search, sort and pages are ignored");
  });
});
