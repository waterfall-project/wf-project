// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SignedOut, UnexpectedAnswer } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import type { components } from "@/api/generated/schema";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import IndicatorsPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

// One client for the whole of a page, made at its first call: a sequence of answers to a route
// answers the calls of the page in turn, whichever read makes them.
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
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const REVISION_ROUTE = "GET /projects/{project_id}/revisions/{revision_id}";
const MARKED = "01926f3a-7c00-7000-8000-000000000101";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
type Indicators = components["schemas"]["ProjectIndicators"];
type History = components["schemas"]["IndexHistory"];
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

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

/** What Next hands the screen of the indicators, at the query given, in the revision given. */
function at(search: Record<string, string> = {}, revisionId = REVISION) {
  return {
    params: Promise.resolve({ projectId: PROJECT, revisionId }),
    searchParams: Promise.resolve(search),
  };
}

/** The paths of the calls of a route, in their order. */
function pathsOf(route: string): string[] {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => call.path);
}

/** The query of the call of a route, as the client serialized it. */
function queryOf(route: string): Record<string, string> | undefined {
  const call = server.clients.flatMap((client) => client.calls).find((c) => c.route === route);
  return call === undefined ? undefined : Object.fromEntries(call.query);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/indicators": "project_indicators",
    "GET /projects/{project_id}/indicators/index-history": "index_history",
    "GET /projects/{project_id}/indicators/milestone-tracking": "milestone_tracking",
    "GET /projects/{project_id}/indicators/cost-curve": "cost_curve",
    "GET /projects/{project_id}/indicators/earned-value-curves": "earned_value_curves",
    "GET /projects/{project_id}/workload": "workload",
    "GET /reference/org-nodes": "org_nodes",
    "GET /projects/{project_id}/revisions": "revisions_marked",
  };
});

describe("the screen of the indicators of a project", () => {
  it("names its function in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toMatch(/^Project indicators/);
  });

  it("shows its reading context above one card for each indicator FBS-4.8.1 to FBS-4.8.5", async () => {
    const page = html(await IndicatorsPage(at()));
    expect(page).toContain('<section aria-label="Reading context"');
    expect(page).toMatch(
      /<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Project indicators<\/h1>/,
    );
    const headings = [...page.matchAll(/<h2[^>]*>(.*?)<\/h2>/g)].map((m) => m[1]);
    expect(headings).toEqual([
      "Financial progress",
      "Projection at completion",
      "Physical progress",
      "Cost performance index (CPI)",
      "Schedule performance index (SPI)",
      "Milestone tracking",
      "Cumulative costs",
      "Earned value curves",
      "Project workload",
    ]);
  });

  it("gives each indicator the date it is computed at [WF-IHM-0020-A]", async () => {
    const page = text(html(await IndicatorsPage(at())));
    // One date under the title of each of the five cards, which holds the date of the values in
    // it, one under the caption of each evolution of an index, and one under the caption of each
    // chart below: the milestones, the cumulative costs, the earned value, the workload.
    expect(page.match(/Computed on/g)).toHaveLength(5 + 2 + 4);
    expect(page).toContain(
      "Financial progress Computed on Financial progress 0% Budget consumption 0% Actual cost",
    );
    expect(page).toContain("Evolution of the cost index Computed on");
    expect(page).toContain("Evolution of the schedule index Computed on");
  });

  it("shows the amounts as the API gives them, nothing summed nor divided", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain(
      "Actual cost 0.00 Remaining to commit 100,000.00 Reference budget 100,000.00",
    );
    expect(page).toContain("At budget 100,000.00 0.00 Project manager’s 100,000.00 0.00");
    expect(page).toContain(
      "Schedule variance -33,333.33 Earned value 0.00 Planned value 33,333.33",
    );
  });

  it("says an index the API cannot compute not computable, with its reason, never zero", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Cost index Not computable No actual cost at the calculation date.");
    expect(page).toContain(
      "Projection at the observed rate Not computable No actual cost at the calculation date.",
    );
  });

  it("shows the zone of an index by the one signal, and none where the API gives none [WF-IHM-0070-A]", async () => {
    const page = html(await IndicatorsPage(at()));
    const cost = page.slice(
      page.indexOf("Cost performance index"),
      page.indexOf("Schedule performance index"),
    );
    const schedule = page.slice(
      page.indexOf("Schedule performance index"),
      page.indexOf("Evolution of the schedule index"),
    );
    expect(text(schedule)).toContain("Schedule index 0 Alert Schedule variance");
    expect(schedule).toMatch(
      /class="[^"]*text-signal-alert[^"]*"><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg><span>Alert<\/span>/,
    );
    expect(cost.slice(0, cost.indexOf("Evolution"))).not.toContain("text-signal-");
  });

  it("asks the indicators for the sub-project and the date the address filters, the evolution of the indices dated by its own calculation [WF-IHM-0020-A]", async () => {
    const page = html(await IndicatorsPage(at({ subproject_id: SUBPROJECT, as_of: "2026-02-01" })));
    expect(queryOf("GET /projects/{project_id}/indicators")).toEqual({
      scope: SUBPROJECT,
      as_of: "2026-02-01",
    });
    // The evolution runs to the current day whatever the address asks: it takes no date, and
    // says its own date of calculation beside that of the indicators.
    expect(queryOf("GET /projects/{project_id}/indicators/index-history")).toEqual({});
    const dated = (heading: string) => {
      const from = page.indexOf(heading);
      return /Computed on <time dateTime="([^"]+)">/.exec(page.slice(from))?.[1];
    };
    expect(dated("Cost performance index")).toBe(
      (example("project_indicators") as Indicators).context.computed_at,
    );
    expect(dated("Evolution of the cost index")).toBe(
      (example("index_history") as History).context.computed_at,
    );
    server.clients = [];
    await IndicatorsPage(at());
    expect(queryOf("GET /projects/{project_id}/indicators")).toEqual({});
  });

  it("draws the evolution of each index with the values of each point", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Evolution of the cost index");
    expect(page).toContain("Evolution of the schedule index");
    expect(page).toContain("Whole project Current revision");
  });

  it("says at its head that its figures are computed on another revision than the one its banner names, and which [WF-IHM-0020-A]", async () => {
    // The reference, marked, is read; the API computes on the revision under way (#247), which
    // the screen reads then by its identifier — once, though the indicators and the evolution
    // of the indices both name it.
    server.answers = {
      ...server.answers,
      [REVISION_ROUTE]: ["revision_marked", "revision"],
    };
    const page = text(html(await IndicatorsPage(at({}, MARKED))));
    expect(page).toContain(
      "Project indicators Indicators of another revision These indicators are computed on the revision “Current revision”, not on the one the banner names. Financial progress",
    );
    expect(page).toMatch(/Revision Référence/);
    expect(pathsOf(REVISION_ROUTE)).toEqual([
      `/projects/${PROJECT}/revisions/${MARKED}`,
      `/projects/${PROJECT}/revisions/${REVISION}`,
    ]);
  });

  it("says unnamed a revision of the calculation the API does not find, and stays [WF-IHM-0020-A]", async () => {
    server.answers = {
      ...server.answers,
      [REVISION_ROUTE]: ["revision_marked", NOT_FOUND],
    };
    const page = text(html(await IndicatorsPage(at({}, MARKED))));
    expect(page).toContain(
      "These indicators are computed on the revision “unnamed”, not on the one the banner names. Financial progress",
    );
  });

  it("says nothing of another revision when its figures are computed on its own, nor reads the revisions", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).not.toContain("Indicators of another revision");
    expect(pathsOf(REVISION_ROUTE)).toEqual([`/projects/${PROJECT}/revisions/${REVISION}`]);
  });

  it("says the indicators unavailable before the state In progress, the rest of the screen shown [WF-IND-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators": {
        problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
      },
    };
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain(
      "Indicators unavailable The indicators of a project are computed from the In progress state",
    );
    expect(page).not.toContain("Financial progress");
    // Nor is the evolution of the indices asked, nor the cumulative curves: there are none before
    // the state In progress. The milestones and the workload are.
    expect(queryOf("GET /projects/{project_id}/indicators/index-history")).toBeUndefined();
    expect(queryOf("GET /projects/{project_id}/indicators/cost-curve")).toBeUndefined();
    expect(queryOf("GET /projects/{project_id}/indicators/earned-value-curves")).toBeUndefined();
    expect(page).not.toContain("Cumulative costs");
    expect(page).toContain("Milestone tracking Time/time diagram");
    expect(page).toContain("Project workload");
  });

  it("does not take a refusal of the same status for another reason as the state of the project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators": {
        problem: { code: "ALREADY_EXISTS", status: 409 },
      },
    };
    await expect(IndicatorsPage(at())).rejects.toBeInstanceOf(UnexpectedAnswer);
  });

  it("is not found when the API does not find the indicators of the project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}/indicators": NOT_FOUND };
    await expect(IndicatorsPage(at())).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });

  it("is not found when the API does not find the project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": NOT_FOUND };
    await expect(IndicatorsPage(at())).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });

  it("leads to the sign-in when the session is lost while the evolution of the indices is read", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators/index-history": {
        problem: { code: "SESSION_REQUIRED", status: 401 },
      },
    };
    await expect(IndicatorsPage(at())).rejects.toBeInstanceOf(SignedOut);
  });
});

const WORKLOAD_ROUTE = "GET /projects/{project_id}/workload";
const ORG_NODE = "01926f3a-7c00-7000-8000-000000000471";

describe("the curves, the milestones and the workload of the screen", () => {
  it("draws the tracking of the milestones the API gives [WF-IND-0090-A]", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Milestone tracking Time/time diagram Computed on");
    expect(page).toContain("Réception usine");
  });

  it("says that no milestone is tracked when the API gives none, its date of calculation left with the chart", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators/milestone-tracking": "milestone_tracking_none",
    };
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Milestone tracking No milestone is tracked. Cumulative costs");
  });

  it("asks the cumulative costs at the date the address filters and the earned value for its sub-project too [WF-IND-0100-A] [WF-IND-0110-A]", async () => {
    await IndicatorsPage(at({ subproject_id: SUBPROJECT, as_of: "2026-02-01" }));
    expect(queryOf("GET /projects/{project_id}/indicators/cost-curve")).toEqual({
      as_of: "2026-02-01",
    });
    expect(queryOf("GET /projects/{project_id}/indicators/earned-value-curves")).toEqual({
      scope: SUBPROJECT,
      as_of: "2026-02-01",
    });
  });

  it("shifts the cumulative costs by the payment delays when the address asks it, and names them as the API says [WF-IND-0100-A]", async () => {
    let page = html(await IndicatorsPage(at({ subproject_id: SUBPROJECT })));
    expect(queryOf("GET /projects/{project_id}/indicators/cost-curve")).toEqual({});
    // The command keeps the other parameters of the address.
    expect(page).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/indicators?subproject_id=${SUBPROJECT}&amp;payment_delays=true"`,
    );
    expect(text(page)).toContain("Shift by the payment delays S-curve");

    server.clients = [];
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators/cost-curve": "cost_curve_payment_delays",
    };
    page = html(await IndicatorsPage(at({ payment_delays: "true" })));
    expect(queryOf("GET /projects/{project_id}/indicators/cost-curve")).toEqual({
      payment_delays: "true",
    });
    expect(page).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/indicators"`);
    expect(text(page)).toContain("Remove the shift by the payment delays Cash out Computed on");
    expect(text(page)).toContain("Cash out by month");
  });

  it("asks the workload on the remaining of the revision under way unless the address names another basis [WF-DEV-0070-A]", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({ basis: "current_remaining" });
    expect(page).toContain(
      "Basis: Remaining of the current revision — revision “Current revision”",
    );
    expect(page).toContain("Load by role and by month");
  });

  it("asks the workload on the marked revision and the node of organisation chosen, the server filtering [WF-DEV-0070-A]", async () => {
    server.answers = {
      ...server.answers,
      [WORKLOAD_ROUTE]: "workload_marked_remaining",
      [REVISION_ROUTE]: ["revision", "revision_marked"],
    };
    const page = text(
      html(
        await IndicatorsPage(
          at({ basis: "marked_remaining", workload_revision: MARKED, org_node_id: ORG_NODE }),
        ),
      ),
    );
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({
      basis: "marked_remaining",
      revision_id: MARKED,
      org_node_id: ORG_NODE,
    });
    expect(queryOf("GET /projects/{project_id}/revisions")).toEqual({ status: "marked" });
    // The revision the API says it read, by its identifier: the reference.
    expect(pathsOf(REVISION_ROUTE)).toEqual([
      `/projects/${PROJECT}/revisions/${REVISION}`,
      `/projects/${PROJECT}/revisions/${MARKED}`,
    ]);
    expect(page).toContain("Basis: Remaining of a marked revision — revision “Référence”");
  });

  it("sends no marked revision with another basis, and offers the three bases, the marked revisions and the nodes [WF-DEV-0070-A]", async () => {
    server.answers = { ...server.answers, [WORKLOAD_ROUTE]: "workload_reference_budget" };
    const page = html(
      await IndicatorsPage(at({ basis: "reference_budget", workload_revision: MARKED })),
    );
    expect(queryOf(WORKLOAD_ROUTE)).toEqual({ basis: "reference_budget" });
    const options = (name: string) => {
      const select = new RegExp(`<select[^>]*name="${name}"[^>]*>(.*?)</select>`).exec(page);
      return [...(select?.[1] ?? "").matchAll(/<option[^>]*>(.*?)<\/option>/g)].map((m) => m[1]);
    };
    expect(options("basis")).toEqual([
      "Budget of the reference revision",
      "Remaining of a marked revision",
      "Remaining of the current revision",
    ]);
    expect(options("workload_revision")).toEqual(["Référence", "Offre v1.0"]);
    expect(options("org_node_id")).toEqual([
      "All nodes",
      "Direction technique",
      "Bureau d&#x27;études électriques",
      "Service des essais",
    ]);
    // The choice keeps the other parameters of the address, the workload's own left to it.
    expect(page).not.toContain('type="hidden" name="basis"');
  });

  it("offers only the revision under way on a project without a reference revision [WF-DEV-0070-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/indicators": {
        problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
      },
    };
    const page = html(await IndicatorsPage(at()));
    expect(page).toMatch(
      /<select[^>]*name="basis"[^>]*><option value="current_remaining"[^>]*>[^<]*<\/option><\/select>/,
    );
    expect(page).not.toContain('name="workload_revision"');
  });

  it("does not offer the marked revisions as a basis when the project has none", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = html(await IndicatorsPage(at()));
    expect(page).not.toContain('value="marked_remaining"');
  });

  it("says the workload unavailable on a basis the API refuses, the rest of the screen shown [WF-DEV-0070-A]", async () => {
    server.answers = {
      ...server.answers,
      [WORKLOAD_ROUTE]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } },
    };
    const page = text(html(await IndicatorsPage(at({ basis: "reference_budget" }))));
    expect(page).toContain("The workload is not available on this basis.");
    expect(page).toContain("Financial progress");
  });

  it("offers its workload for export, a command named under the caption of its chart", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Load by role and by month Export as PNG Computed on");
  });
});
