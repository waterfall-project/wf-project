// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import IndicatorsPage, { generateMetadata } from "./page";

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
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
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

/** What Next hands the screen of the indicators, at the query given. */
function at(search: Record<string, string> = {}) {
  return {
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(search),
  };
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
    // The contract cites no example of the tracking of the milestones yet.
    "GET /projects/{project_id}/indicators/milestone-tracking": NOT_FOUND,
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
    ]);
  });

  it("gives each indicator the date it is computed at [WF-IHM-0020-A]", async () => {
    const page = text(html(await IndicatorsPage(at())));
    // One date in the header of each of the five cards, and one under each of the six values
    // under `Computable`: three progresses, a projection, two indices.
    expect(page.match(/Computed on/g)).toHaveLength(5 + 6);
    expect(page).toContain(
      "Financial progress Computed on Financial progress 0% Computed on Budget consumption 0% Computed on",
    );
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
    expect(text(schedule)).toContain("Schedule index 0 Computed on");
    expect(schedule).toMatch(
      /class="[^"]*text-signal-alert[^"]*"><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg><span>Alert<\/span>/,
    );
    expect(cost.slice(0, cost.indexOf("Evolution"))).not.toContain("text-signal-");
  });

  it("asks the indicators for the sub-project and the date the address filters", async () => {
    await IndicatorsPage(at({ subproject_id: SUBPROJECT, as_of: "2026-02-01" }));
    expect(queryOf("GET /projects/{project_id}/indicators")).toEqual({
      scope: SUBPROJECT,
      as_of: "2026-02-01",
    });
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
    expect(page).toContain("Milestone tracking");
  });

  it("says the tracking of the milestones unavailable when the API does not find it", async () => {
    const page = text(html(await IndicatorsPage(at())));
    expect(page).toContain("Milestone tracking The milestone tracking is unavailable.");
  });

  it("is not found when the API does not find the indicators of the project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}/indicators": NOT_FOUND };
    await expect(IndicatorsPage(at())).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });

  it("is not found when the API does not find the project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": NOT_FOUND };
    await expect(IndicatorsPage(at())).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });

  it("leads to the sign-in when the session is lost while the indicators are read", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/indicators/milestone-tracking": {
        problem: { code: "SESSION_REQUIRED", status: 401 },
      },
    };
    await expect(IndicatorsPage(at())).rejects.toThrow();
  });
});
