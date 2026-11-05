// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ProjectRiskMatrixProps } from "@/components/risks/risk-bubble-chart";
import { type Risk, RiskDetail, type RiskDetailProps } from "@/components/risks/risk-detail";
import type { RisksGridProps } from "@/components/risks/risks-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import RisksPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

vi.mock("@/api/server", () => ({
  serverClient: () => {
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
// The session of the contract, some of the sizes of pages its account keeps and the permissions it
// holds set for a test.
const kept = vi.hoisted(
  (): {
    grids: Record<string, { page_size: number }>;
    permissions: readonly string[] | undefined;
  } => ({
    grids: {},
    permissions: undefined,
  }),
);
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            ...(kept.permissions === undefined ? {} : { permissions: kept.permissions }),
            display_preferences: {
              ...session.display_preferences,
              grids: { ...session.display_preferences?.grids, ...kept.grids },
            },
          };
    },
  };
});
// The grid renders as it would, and keeps what its page handed it.
const grids = vi.hoisted((): { risks: RisksGridProps[] } => ({ risks: [] }));
vi.mock("@/components/risks/risks-grid", async (original) => {
  const actual = await original<typeof import("@/components/risks/risks-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    RisksGrid: (props: RisksGridProps) => {
      grids.risks.push(props);
      return createElement(actual.RisksGrid, props);
    },
  };
});
// The detail renders as it would, and keeps what its page handed it.
const details = vi.hoisted((): { props: RiskDetailProps[] } => ({ props: [] }));
vi.mock("@/components/risks/risk-detail", async (original) => {
  const actual = await original<typeof import("@/components/risks/risk-detail")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    RiskDetail: (props: RiskDetailProps) => {
      details.props.push(props);
      return createElement(actual.RiskDetail, props);
    },
  };
});
// The matrix renders as it would, and keeps what its page handed it.
const matrices = vi.hoisted((): { props: ProjectRiskMatrixProps[] } => ({ props: [] }));
vi.mock("@/components/risks/risk-bubble-chart", async (original) => {
  const actual = await original<typeof import("@/components/risks/risk-bubble-chart")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    ProjectRiskMatrix: (props: ProjectRiskMatrixProps) => {
      matrices.props.push(props);
      return createElement(actual.ProjectRiskMatrix, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const PATHNAME = `/projects/${PROJECT}/revisions/${REVISION}/risks`;
const CABLING = "01926f3a-7c00-7000-8000-000000000751";
const DELIVERY = "01926f3a-7c00-7000-8000-000000000752";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const BANNER = '<section aria-label="Reading context"';
const LIST = "GET /projects/{project_id}/risks";
const MATRIX = "GET /projects/{project_id}/risks/matrix";
const COVERAGE = "GET /projects/{project_id}/risks/coverage";
const RISK = "GET /projects/{project_id}/risks/{risk_id}";
const REVIEWS = "GET /projects/{project_id}/risks/{risk_id}/reviews";
const CATEGORIES = "GET /reference/cost-categories";
const SUBPROJECTS = "GET /projects/{project_id}/subprojects";
const STRUCTURES = "GET /projects/{project_id}/revisions/{revision_id}/structures";
const NODES = `${STRUCTURES}/{structure_id}/nodes` as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render the screen of the risks in English, at the query given. */
async function risksAt(search: PageSearchParams = {}) {
  const page = await RisksPage({
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The calls the page made to an operation. */
function callsTo(route: string) {
  return server.clients.flatMap((client) => client.calls).filter((call) => call.route === route);
}

/** The query of the one call the page made to an operation. */
function queryOf(route: string): Record<string, string> {
  const [call, ...more] = callsTo(route);
  expect(more).toEqual([]);
  return Object.fromEntries(call?.query ?? []);
}

beforeEach(() => {
  kept.grids = {};
  kept.permissions = undefined;
  grids.risks = [];
  details.props = [];
  matrices.props = [];
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    [LIST]: "risks",
    [MATRIX]: "risk_matrix",
    [COVERAGE]: "risk_coverage",
    [RISK]: "risk",
    [REVIEWS]: "risk_reviews",
    // What the form of a risk chooses its provision among, read while the declaration is available.
    [CATEGORIES]: "volume/cost_categories",
    [SUBPROJECTS]: "subprojects",
    [STRUCTURES]: "structures",
    [NODES]: "nodes",
  };
});

/** The markup of a region of the page, from its opening to the next region. */
function regionOf(page: string, name: string): string {
  const parts = page.split('role="region"');
  return parts.find((part) => part.startsWith(` aria-label="${name}"`)) ?? "";
}

describe("the screen of the risks", () => {
  it("titles the tab with the function and the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toMatch(/^Risk management · /);
  });

  it("reads the risks and their matrix in the revision of its route, which fixes their own estimate [WF-RIS-0040-A]", async () => {
    const page = await risksAt();
    expect(page.startsWith(BANNER)).toBe(true);
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION, limit: "50" });
    expect(queryOf(MATRIX)).toEqual({ revision_id: REVISION });
    // No risk named, no detail read.
    expect(callsTo(RISK)).toEqual([]);
    expect(callsTo(REVIEWS)).toEqual([]);
    expect(text(page)).toContain("Risk management Help 3 risks retained");
    // The matrix is not in a column beside the grid: with no risk named, nothing is.
    expect(page).not.toContain("<aside");
  });

  it("draws the matrix over the whole width, between the cards and the grid, as a bubble chart [WF-RIS-0040-A]", async () => {
    const page = await risksAt();
    const figure = page.indexOf("<figure aria-labelledby");
    expect(figure).toBeGreaterThan(page.indexOf('aria-label="Risk coverage"'));
    expect(figure).toBeLessThan(page.indexOf('role="grid"'));
    expect(text(page.slice(figure, figure + 400))).toContain("Risk matrix");
    expect(page).toContain("Export as PNG");
    expect(page).not.toContain("<aside");
    // A risk named opens its detail in a column beside the grid, the matrix staying above.
    const opened = await risksAt({ risk: CABLING });
    expect(opened.indexOf("<aside")).toBeGreaterThan(opened.indexOf('role="grid"'));
    expect(opened.indexOf("<figure aria-labelledby")).toBeLessThan(opened.indexOf('role="grid"'));
  });

  it("reads the matrix without the states of the filter, and shows the three distinct totals of the list [WF-RIS-0040-A]", async () => {
    const page = await risksAt({ states: "occurred" });
    expect(matrices.props).toHaveLength(1);
    expect(Object.keys(matrices.props[0] ?? {})).not.toContain("states");
    expect(text(page)).toContain(
      "Identified risks 500,000.00 Occurred risks 60.00 Dismissed risks 600,000.00 General total 1,100,060.00",
    );
  });

  it("starts the matrix as the account kept it, folded when it kept nothing", async () => {
    await risksAt();
    expect(matrices.props.map(({ folded }) => folded)).toEqual([true]);
    matrices.props = [];
    server.answers = { ...server.answers, "GET /me": "me_grid_settings" };
    await risksAt();
    expect(matrices.props.map(({ folded }) => folded)).toEqual([false]);
  });

  it("hands the grid the risks in the order of the answer, of each the fields it reads alone", async () => {
    await risksAt();
    const [handed] = grids.risks;
    expect(handed?.risks.items.map((risk) => risk.label)).toEqual([
      "Risque de reprise du câblage",
      "Retard de livraison des armoires",
      "Indisponibilité de l'automaticien",
    ]);
    expect(Object.keys(handed?.risks.items[0] ?? {})).toEqual([
      "risk_id",
      "label",
      "probability",
      "severity",
      "provision_amount",
      "occurrence_cost",
      "occurred_reestimated_amount",
      "state",
      "computed_fields",
      "last_review_on",
      "matrix_cell",
    ]);
    expect(handed?.risks.totals.total).toBe("1100060.00");
  });

  it("asks the server for the sort, the search and the states the address names, by the names of the contract [WF-RIS-0040-A]", async () => {
    await risksAt({
      states: "occurred,unknown,dismissed",
      sort_by: "provision_amount",
      sort_order: "desc",
      search: "armoires",
    });
    expect(queryOf(LIST)).toEqual({
      revision_id: REVISION,
      limit: "50",
      states: "occurred,dismissed",
      search: "armoires",
      sort_by: "provision_amount",
      sort_order: "desc",
    });
    expect(grids.risks[0]?.query).toEqual({
      sort: { column: "provision_amount", order: "desc" },
      search: "armoires",
      size: 50,
    });
  });

  it("asks the server the zones, the bounds of each column of figures and the period of the last review the address names, under the names of the contract [WF-IHM-0130-A]", async () => {
    server.answers = { ...server.answers, [LIST]: "risks_filtered" };
    await risksAt({
      zones: "watch,unknown",
      probability_min: "0.1",
      provision_amount_min: "100000",
      occurred_reestimated_amount_max: "300.5",
      last_review_on_to: "2026-03-01",
      severity_min: "abc",
    });
    expect(queryOf(LIST)).toEqual({
      revision_id: REVISION,
      limit: "50",
      zones: "watch",
      probability_min: "0.1",
      provision_amount_min: "100000",
      occurred_reestimated_amount_max: "300.5",
      last_review_on_to: "2026-03-01",
    });
    // The totals are those of the risks retained, as the answer gives them.
    const answer = example("risks_filtered") as { totals: unknown };
    expect(grids.risks[0]?.risks.totals).toEqual(answer.totals);
  });

  it("says the filters the server refused at their field and reads no grid, the other filters kept [WF-IHM-0130-A]", async () => {
    const refusal = example("risks_period_inverted") as components["schemas"]["Problem"] & {
      status: 422;
    };
    server.answers = { ...server.answers, [LIST]: { problem: refusal } };
    const page = await risksAt({
      last_review_on_from: "2026-03-01",
      last_review_on_to: "2026-02-01",
    });
    expect(grids.risks).toEqual([]);
    expect(text(page)).toContain("The risks are not read: the server refuses the filters asked.");
    expect(text(page)).toContain("The end of the period may not precede its start, 1 Mar 2026");
    expect(page).toContain("Period of the last review");
  });

  it("offers the shortcut of the periodic review at the day of the last marking of the project, which the server lists [WF-RIS-0020-A]", async () => {
    const revisions = example("revisions") as { items: { marked_at: string | null }[] };
    const marked = revisions.items.find((each) => each.marked_at !== null)?.marked_at ?? "";
    const day = new Date(marked).toISOString().slice(0, 10);
    const page = await risksAt();
    expect(text(page)).toContain("Not reviewed since the last marking");
    expect(page).toContain(`last_review_on_to=${day}`);
  });

  it("reads the register without the shortcut when the revisions are refused, the contract giving them no other refusal [WF-RIS-0020-A]", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}/revisions": NOT_FOUND };
    const page = await risksAt();
    expect(grids.risks).not.toEqual([]);
    expect(text(page)).not.toContain("Not reviewed since the last marking");
  });

  it("asks the server the page and the size of the pages the address names [WF-IHM-0060-A]", async () => {
    await risksAt({ limit: "25", offset: "50", states: "identified" });
    expect(queryOf(LIST)).toEqual({
      revision_id: REVISION,
      limit: "25",
      offset: "50",
      states: "identified",
    });
    expect(grids.risks[0]?.query.size).toBe(25);
    // A size the contract does not take is not asked: the default stands.
    server.clients = [];
    await risksAt({ limit: "7", offset: "abc" });
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION, limit: "50" });
  });

  it("asks the size of the pages the account kept when the address names none, found again at the reopening [WF-IHM-0060-A]", async () => {
    kept.grids = { risks: { page_size: 25 } };
    await risksAt();
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION, limit: "25" });
    expect(grids.risks[0]?.query.size).toBe(25);
  });

  it("counts the risks the answer retains, not those of its page [WF-IHM-0060-A]", async () => {
    server.answers = { ...server.answers, [LIST]: { example: "risks_page", status: 200 } };
    const page = await risksAt({ limit: "2" });
    // `risks_page` holds 2 lines of the 3 risks retained (`meta.total`).
    expect(grids.risks[0]?.risks.items).toHaveLength(2);
    expect(text(page)).toContain("Risk management Help 3 risks retained");
  });

  it("hands the grid the totals of the answer, those of every risk retained, not the sum of the page [WF-IHM-0060-A]", async () => {
    server.answers = { ...server.answers, [LIST]: { example: "risks_page", status: 200 } };
    await risksAt({ limit: "2" });
    const answer = example("risks_page") as { totals: unknown };
    expect(grids.risks[0]?.risks.totals).toEqual(answer.totals);
    expect(grids.risks[0]?.risks.items).toHaveLength(2);
  });

  it("asks no sort by a column the server does not sort the risks by", async () => {
    await risksAt({ sort_by: "zone" });
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION, limit: "50" });
  });

  it("asks the server to sort the risks by the reestimated amount of the occurred risks, and leaves the place of its null values to it [WF-RIS-0050-A]", async () => {
    await risksAt({ sort_by: "occurred_reestimated_amount", sort_order: "desc" });
    expect(queryOf(LIST)).toEqual({
      revision_id: REVISION,
      limit: "50",
      sort_by: "occurred_reestimated_amount",
      sort_order: "desc",
    });
  });

  it("presses the states the address filters on", async () => {
    const page = await risksAt({ states: "identified" });
    expect(page).toMatch(/aria-pressed="true"[^>]*>.*?Identified<\/button>/);
    expect(page).toMatch(/aria-pressed="false"[^>]*>.*?Every state<\/button>/);
  });

  it("shows the three totals of the provisions, distinct, and the general total, as the server gives them [WF-RIS-0040-A]", async () => {
    const page = await risksAt();
    expect(text(page)).toContain(
      "Identified risks 500,000.00 Occurred risks 60.00 Dismissed risks 600,000.00 General total 1,100,060.00",
    );
    expect(page).toMatch(/role="region" aria-label="Provisions of the risks retained"/);
    // The card is a list of terms under its title, within its own region.
    expect(regionOf(page, "Provisions of the risks retained")).toMatch(
      /<h2[^>]*>Provisions of the risks retained<\/h2>.*?<dl/,
    );
  });

  it("shows the risk reserve of the reference revision in the coverage alone, never among the totals of the provisions", async () => {
    // Decision of the author of 2026-10-07 (#409): the reserve has its sense beside the provisions
    // remaining, the cost of the risks occurred and the variance.
    const page = await risksAt();
    const start = page.indexOf(
      "<dl",
      page.indexOf('aria-label="Provisions of the risks retained"'),
    );
    const totals = page.slice(start, page.indexOf("</dl>", start));
    expect(text(totals)).toBe(
      "Identified risks 500,000.00 Occurred risks 60.00 Dismissed risks 600,000.00 General total 1,100,060.00",
    );
    expect(text(page).match(/Risk reserve/g)).toHaveLength(1);
  });

  it("reads the coverage of the risks in the revision of its route, and shows its amounts as the server computes them, the reestimated of the occurred risks beside their cost as an information, the variance signed [WF-RIS-0050-A]", async () => {
    const page = await risksAt();
    expect(queryOf(COVERAGE)).toEqual({ revision_id: REVISION });
    expect(page).toMatch(/role="region" aria-label="Risk coverage"/);
    // Dated like every card, the region reading alone [WF-IHM-0020-A].
    expect(regionOf(page, "Risk coverage")).toMatch(/<time dateTime="2026-06-03T14:05:00Z"/);
    expect(text(page)).toContain(
      "Risk reserve 850,060.00 Remaining provisions 500,000.00 Cost of the occurred risks 200.00 reestimated Reestimated cost of the occurred risks (information) 200.00 Coverage variance 349,860.00",
    );
    // The reestimated stands in regard of the cost, in its entry, not as a term of the variance: four
    // terms, and the entry of the cost holds both amounts, the reestimated named in full to a reader.
    const region = regionOf(page, "Risk coverage");
    const coverage = region.slice(0, region.indexOf("</dl>"));
    expect(coverage.match(/<dt/g)).toHaveLength(4);
    const cost = coverage.slice(
      coverage.indexOf("<dd", coverage.indexOf("Cost of the occurred risks</dt>")),
    );
    const entry = cost.slice(0, cost.indexOf("</dd></div>"));
    expect(entry.match(/aria-label="Computed"/g)).toHaveLength(2);
    // The bullet is a hidden element of its own, drawn by the style, not a part of the translated word.
    expect(entry).toMatch(/<span[^>]*aria-hidden="true"[^>]*before:content-\[[^>]*><\/span>/);
    expect(entry).toMatch(/<span aria-hidden="true">reestimated<\/span>/);
    expect(entry).toMatch(
      /<span class="sr-only">Reestimated cost of the occurred risks \(information\)<\/span>/,
    );
  });

  it("names the axes of the matrix by their bounds, and each cell by its signal and its count [WF-IHM-0070-A]", async () => {
    const page = await risksAt();
    // The table of the counts of the matrix, under the chart, named by its caption.
    const start = page.lastIndexOf(
      "<table",
      page.indexOf("Count of the risks identified by cell of the matrix</caption>"),
    );
    const matrix = page.slice(start, page.indexOf("</table>", start));
    expect(text(matrix)).toContain(
      "Probability Severity, as a share of the base of the project " +
        "0% to under 1% 1% to under 5% 5% to under 10% 10% and over",
    );
    // The highest probability at the top, its cells as the server classes them, counting only the identified risks (#1395).
    const rows = [...matrix.matchAll(/<tr>(.*?)<\/tr>/g)].slice(2).map((row) => row[1] ?? "");
    expect(rows.map((row) => text(row))).toEqual([
      "60% and over 0 0 0 0",
      "30% to under 60% 0 1 0 0",
      "10% to under 30% 0 0 0 0",
      "0% to under 10% 0 0 0 0",
    ]);
    const zones = (row: string) =>
      [...row.matchAll(/role="img" aria-label="(\w+)"/g)].map((m) => m[1]);
    expect(zones(rows[0] ?? "")).toEqual(["Watch", "Watch", "Alert", "Alert"]);
    expect(zones(rows[3] ?? "")).toEqual(["Nominal", "Nominal", "Nominal", "Watch"]);
  });

  it("shows the detail of the risk the address names, read in the revision: its notes, its provision line, the history of its reviews [WF-RIS-0040-A]", async () => {
    const page = await risksAt({ risk: CABLING });
    expect(callsTo(RISK).map((call) => call.path)).toEqual([
      `/projects/${PROJECT}/risks/${CABLING}`,
    ]);
    expect(queryOf(RISK)).toEqual({ revision_id: REVISION });
    expect(queryOf(REVIEWS)).toEqual({ revision_id: REVISION });
    const said = text(page);
    expect(said).toContain(
      "Risque de reprise du câblage Modify Review Declare occurred Delete the risk Unmet condition: risk cited by no marked revision. State Identified Probability 40% Severity 1,250,000.00 Provision 500,000.00 Last review 2 Mar 2026",
    );
    expect(said).toContain(
      "Description Les essais de l'armoire de commande peuvent révéler des défauts de câblage à reprendre sur site.",
    );
    expect(said).toContain(
      "Mitigation actions Contrôle du câblage en atelier avant expédition ; essais de continuité systématiques.",
    );
    expect(said).toContain(
      "Provision line In the main structure: the provision weighs on the estimate.",
    );
    // The history, from the latest, shows the probability and the severity move.
    expect(said).toContain(
      "History of the reviews Date Probability Severity State By " +
        "02/03/2026 40% 1,250,000.00 Identified Camille Martin " +
        "02/02/2026 25% 1,250,000.00 Identified Camille Martin " +
        "12/01/2026 25% 1,000,000.00 Identified Camille Martin",
    );
  });

  it("presents the severity and the provision of a risk as computed in its detail [WF-IHM-0030-A]", async () => {
    const page = await risksAt({ risk: CABLING });
    const facts = page.slice(
      page.indexOf("<dl", page.indexOf("Risque de reprise du câblage</h2>")),
    );
    expect(facts).toMatch(
      /Severity<\/dt><dd[^>]*><span[^>]*><svg[^>]*role="img" aria-label="Computed"/,
    );
    expect(facts).toMatch(
      /Provision<\/dt><dd[^>]*><span[^>]*><svg[^>]*role="img" aria-label="Computed"/,
    );
    // Nothing of the detail is entered.
    expect(facts).not.toContain("<input");
  });

  it("names the category and the sub-project the risk designates for its provision, by the labels the server resolves (EP-14/L42p)", async () => {
    const page = await risksAt({ risk: CABLING });
    expect(text(page)).toContain(
      "Provision line In the main structure: the provision weighs on the estimate. " +
        "Category Provisions pour risques Subproject Out of any subproject",
    );
  });

  it("says the category of a provision that is no longer admitted, as the server says (aucune exigence : propre à l'US (US-0660, #1532))", () => {
    const risk = example("risk_dismissed_category_deactivated") as Risk;
    const detail = renderToStaticMarkup(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <RiskDetail risk={risk} reviews={[]} projectId="01926f3a-7c00-7000-8000-000000000001" />
      </NextIntlClientProvider>,
    );
    expect(text(detail)).toContain("Category Provisions pour risques (no longer admitted)");
  });

  it("says the provision line of a risk occurred withdrawn at its occurrence [WF-RIS-0060-A]", async () => {
    server.answers = {
      ...server.answers,
      [RISK]: { example: "risk_occurred_detail", status: 200 },
    };
    const page = await risksAt({ risk: DELIVERY });
    expect(text(page)).toContain(
      "Provision line Withdrawn from the main structure at the occurrence: the lines merged from its own estimate bear its cost.",
    );
  });

  it("says of a risk occurred the provision of the reference and its cost at the occurrence, each computed, in its detail", async () => {
    server.answers = {
      ...server.answers,
      [RISK]: { example: "risk_occurred_detail", status: 200 },
    };
    const page = await risksAt({ risk: DELIVERY });
    expect(text(page)).toContain(
      "State Occurred Probability 30% Severity 200.00 Reference provision 60.00 Cost at occurrence 200.00 Last review",
    );
    expect(page).toMatch(
      /Cost at occurrence<\/dt><dd[^>]*><span[^>]*><svg[^>]*role="img" aria-label="Computed"/,
    );
  });

  it("says no cost at the occurrence of a risk identified, and its provision its own", async () => {
    const said = text(await risksAt({ risk: CABLING }));
    // The detail alone: the register heads the column for every risk.
    const start = said.indexOf("Risque de reprise du câblage Modify");
    expect(start).toBeGreaterThan(-1);
    const detail = said.slice(start);
    expect(detail).toContain("Provision 500,000.00 Last review");
    expect(detail).not.toContain("Cost at occurrence");
    expect(detail).not.toContain("Reference provision");
  });

  it("says a risk retained by none of its filters, its totals those of the server", async () => {
    server.answers = { ...server.answers, [LIST]: { example: "risks_empty", status: 200 } };
    const page = await risksAt({ states: "occurred" });
    expect(text(page)).toContain("Risk management Help no risk retained");
    expect(text(page)).toContain(
      "Identified risks 0.00 Occurred risks 0.00 Dismissed risks 0.00 General total 0.00",
    );
    expect(text(page)).toContain("No row matches the request.");
  });

  it("asks nothing of a risk the address names by no identifier", async () => {
    await risksAt({ risk: "../reference" });
    expect(callsTo(RISK)).toEqual([]);
  });

  it("is not found when the API finds neither the risk named, nor the project", async () => {
    server.answers = { ...server.answers, [RISK]: NOT_FOUND };
    await expect(risksAt({ risk: CABLING })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    server.answers = { ...server.answers, "GET /projects/{project_id}": NOT_FOUND };
    await expect(risksAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});

describe("the commands of the risks", () => {
  /** The command that identifies a risk in the markup of the page, and its tag. */
  function command(page: string): string {
    return /<button[^>]*>(?:(?!<\/button>).)*Identify a risk<\/button>/s.exec(page)?.[0] ?? "";
  }

  it("offers « Identify a risk » as the revision lists `declare_risk`, and reads once each of the listings the provision is chosen among", async () => {
    const page = await risksAt();
    expect(command(page)).not.toBe("");
    expect(command(page)).not.toContain(`aria-disabled="true"`);
    // The active categories of the type provision, the sub-projects, and the tasks of the main
    // structure of the revision: read once each.
    expect(callsTo(CATEGORIES)).toHaveLength(1);
    expect(callsTo(SUBPROJECTS)).toHaveLength(1);
    expect(callsTo(NODES)).toHaveLength(1);
    expect(callsTo(NODES)[0]?.path).toContain(`/revisions/${REVISION}/structures/`);
    expect(Object.fromEntries(callsTo(NODES)[0]?.query ?? [])).toMatchObject({ kinds: "task" });
  });

  it("leads the state of a risk occurred to the estimate, and to the planning for a session that does not read it, the risk filtered on [WF-RIS-0060-A]", async () => {
    const grid = `/projects/${PROJECT}/revisions/${REVISION}`;
    const page = await risksAt();
    expect(grids.risks.at(-1)?.originGrid).toBe(`${grid}/estimate`);
    expect(page).toContain(`href="${grid}/estimate?origin_risk_ids=${DELIVERY}"`);
    grids.risks = [];
    kept.permissions = ["planning.read"];
    const planning = await risksAt();
    expect(grids.risks.at(-1)?.originGrid).toBe(`${grid}/planning`);
    expect(planning).toContain(`href="${grid}/planning?origin_risk_ids=${DELIVERY}"`);
    expect(planning).not.toContain(`${grid}/estimate?origin_risk_ids=`);
    grids.risks = [];
    kept.permissions = [];
    const none = await risksAt();
    expect(grids.risks.at(-1)?.originGrid).toBeUndefined();
    expect(none).not.toContain("origin_risk_ids=");
  });

  it.each([
    ["the sub-projects", SUBPROJECTS],
    ["the tasks of the main structure", NODES],
    ["the categories of cost", CATEGORIES],
  ] as const)(
    "renders the screen and offers the command when the session may not read %s, the server judging the declaration",
    async (_listing, route) => {
      server.answers = {
        ...server.answers,
        [route]: { problem: { code: "PERMISSION_MISSING", status: 403 } },
      };
      const page = await risksAt();
      expect(command(page)).not.toBe("");
      expect(command(page)).not.toContain(`aria-disabled="true"`);
      expect(grids.risks).not.toEqual([]);
    },
  );

  it("offers it unavailable on a revision without a task, described by the condition it lacks, and reads nothing for a form it cannot open [WF-RIS-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_without_tasks",
    };
    const page = await risksAt();
    expect(command(page)).toContain('aria-disabled="true"');
    expect(text(page)).toContain("Unmet condition: at least one task.");
    expect(callsTo(CATEGORIES)).toEqual([]);
    expect(callsTo(NODES)).toEqual([]);
  });

  it("offers nothing to a caller whose revision lists no declaration", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_reader",
    };
    expect(command(await risksAt())).toBe("");
  });

  it("offers « Modify » in the detail of a risk, and reads the choices of its provision", async () => {
    const page = await risksAt({ risk: CABLING });
    expect(page).toContain("Modify</button>");
    expect(callsTo(NODES)).toHaveLength(1);
  });

  it("reads nothing for the forms of a risk occurred, which lists no command of entry available, on a revision that offers no declaration either", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_without_tasks",
      [RISK]: "risk_occurred_detail",
    };
    const page = await risksAt({ risk: CABLING });
    expect(page).toContain("Review</button>");
    expect(callsTo(CATEGORIES)).toEqual([]);
    expect(callsTo(NODES)).toEqual([]);
  });

  it("hands the detail the choices of the provision it read: the categories of the type, the sub-projects, the tasks of the main structure", async () => {
    await risksAt({ risk: CABLING });
    const handed = details.props.at(-1)?.options;
    expect(handed?.categories.length).toBeGreaterThan(0);
    expect(handed?.subprojects.length).toBeGreaterThan(0);
    expect(handed?.tasks.map(({ label }) => label)).toContain("Études de détail");
  });
});

describe("the note of the fake back on the risks", () => {
  it("says once, under the header, that the service does not apply filters, search, sort and pages (US-0760)", async () => {
    const page = await risksAt();
    expect(page.match(/<p role="note"/g)).toHaveLength(1);
    expect(page).toContain("Filters, search, sort and pages are ignored");
  });
});
