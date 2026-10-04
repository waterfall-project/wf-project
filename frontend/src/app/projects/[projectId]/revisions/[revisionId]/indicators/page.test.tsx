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
    ]);
  });

  it("gives each indicator the date it is computed at [WF-IHM-0020-A]", async () => {
    const page = text(html(await IndicatorsPage(at())));
    // One date under the title of each of the five cards, which holds the date of the values in
    // it, and one under the caption of each evolution of an index.
    expect(page.match(/Computed on/g)).toHaveLength(5 + 2);
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
    // Nor is the evolution of the indices asked: there is none before the state In progress.
    expect(queryOf("GET /projects/{project_id}/indicators/index-history")).toBeUndefined();
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
