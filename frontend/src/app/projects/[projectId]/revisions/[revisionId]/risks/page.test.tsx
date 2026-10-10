// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type Risk, RiskDetail } from "@/components/risks/risk-detail";
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
  grids.risks = [];
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    [LIST]: "risks",
    [MATRIX]: "risk_matrix",
    [COVERAGE]: "risk_coverage",
    [RISK]: "risk",
    [REVIEWS]: "risk_reviews",
  };
});

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
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION });
    expect(queryOf(MATRIX)).toEqual({ revision_id: REVISION });
    // No risk named, no detail read.
    expect(callsTo(RISK)).toEqual([]);
    expect(callsTo(REVIEWS)).toEqual([]);
    expect(text(page)).toContain("Risk management 3 risks retained");
    expect(text(page)).toContain(
      "Choose a risk in the register to read its description, its mitigation actions and the history of its reviews.",
    );
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
      states: "occurred,dismissed",
      search: "armoires",
      sort_by: "provision_amount",
      sort_order: "desc",
    });
    expect(grids.risks[0]?.query).toEqual({
      sort: { column: "provision_amount", order: "desc" },
      search: "armoires",
    });
  });

  it("asks no sort by a column the server does not sort the risks by", async () => {
    await risksAt({ sort_by: "zone" });
    expect(queryOf(LIST)).toEqual({ revision_id: REVISION });
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
    expect(page).toContain('<section aria-label="Provisions of the risks retained"><dl');
  });

  it("shows the risk reserve of the reference revision in the coverage alone, never among the totals of the provisions", async () => {
    // Decision of the author of 2026-10-07 (#409): the reserve has its sense beside the provisions
    // remaining, the cost of the risks occurred and the variance.
    const page = await risksAt();
    const start = page.indexOf('<section aria-label="Provisions of the risks retained">');
    const totals = page.slice(start, page.indexOf("</section>", start));
    expect(text(totals)).toBe(
      "Identified risks 500,000.00 Occurred risks 60.00 Dismissed risks 600,000.00 General total 1,100,060.00",
    );
    expect(text(page).match(/Risk reserve/g)).toHaveLength(1);
  });

  it("reads the coverage of the risks in the revision of its route, and shows its four amounts as the server computes them, the variance signed [WF-RIS-0050-A]", async () => {
    const page = await risksAt();
    expect(queryOf(COVERAGE)).toEqual({ revision_id: REVISION });
    expect(page).toContain('<section aria-label="Risk coverage"><dl');
    expect(text(page)).toContain(
      "Risk reserve 850,060.00 Remaining provisions 500,000.00 Cost of the occurred risks 200.00 Coverage variance 349,860.00",
    );
  });

  it("names the axes of the matrix by their bounds, and each cell by its signal and its count [WF-IHM-0070-A]", async () => {
    const page = await risksAt();
    // The table of the matrix, named by its caption.
    const start = page.lastIndexOf("<table", page.indexOf("Risk matrix</h2></caption>"));
    const matrix = page.slice(start, page.indexOf("</table>", start));
    expect(text(matrix)).toContain(
      "Probability Severity, as a share of the reference budget " +
        "0% to under 1% 1% to under 5% 5% to under 10% 10% and over",
    );
    // The highest probability at the top, its cells as the server classes them.
    const rows = [...matrix.matchAll(/<tr>(.*?)<\/tr>/g)].slice(2).map((row) => row[1] ?? "");
    expect(rows.map((row) => text(row))).toEqual([
      "60% and over 0 0 0 0",
      "30% to under 60% 1 1 0 0",
      "10% to under 30% 0 0 0 0",
      "0% to under 10% 0 0 0 1",
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
      "Risque de reprise du câblage State Identified Probability 40% Severity 1,250,000.00 Provision 500,000.00 Last review 2 Mar 2026",
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

  it("says deactivated the category of a provision that is no longer active, as the server says", () => {
    // A counterfactual variant of `risk`: its category deactivated since its designation, the rest
    // of the example kept.
    const risk: Risk = { ...(example("risk") as Risk), provision_cost_category_is_active: false };
    const detail = renderToStaticMarkup(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
        <RiskDetail risk={risk} reviews={[]} />
      </NextIntlClientProvider>,
    );
    expect(text(detail)).toContain("Category Provisions pour risques (deactivated)");
  });

  it("says the provision line of a risk occurred withdrawn at its occurrence [WF-RIS-0060-A]", async () => {
    server.answers = {
      ...server.answers,
      [RISK]: { example: "risk_occurred_detail", status: 200 },
    };
    const page = await risksAt({ risk: DELIVERY });
    expect(text(page)).toContain(
      "Provision line Withdrawn from the main structure at the occurrence: the lines merged from its own estimate bear the provision.",
    );
  });

  it("says a risk retained by none of its filters, its totals those of the server", async () => {
    server.answers = { ...server.answers, [LIST]: { example: "risks_empty", status: 200 } };
    const page = await risksAt({ states: "occurred" });
    expect(text(page)).toContain("Risk management no risk retained");
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
