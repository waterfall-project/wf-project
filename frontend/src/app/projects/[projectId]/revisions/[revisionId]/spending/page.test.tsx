// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UnexpectedAnswer } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import SpendingPage, { generateMetadata } from "./page";

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
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));
// The grid of the projection, rendered on the server as the page sends it.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => `/projects/${PROJECT}/revisions/${REVISION}/spending`,
  useSearchParams: () => new URLSearchParams(),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const MARKED = "01926f3a-7c00-7000-8000-000000000101";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const SPENDING_ROUTE = "GET /projects/{project_id}/spending";

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

/** What Next hands the screen of the projection, at the query given. */
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

/** The options of a list of the page, by the name of its parameter. */
function options(page: string, name: string): (string | undefined)[] {
  const select = new RegExp(`<select[^>]*name="${name}"[^>]*>(.*?)</select>`).exec(page);
  return [...(select?.[1] ?? "").matchAll(/<option[^>]*>(.*?)<\/option>/g)].map((m) => m[1]);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    [SPENDING_ROUTE]: "spending",
    "GET /projects/{project_id}/revisions": "revisions_marked",
  };
});

describe("the screen of the spending projection of a project", () => {
  it("names its function in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toMatch(/^Spending projection/);
  });

  it("asks the projection on the remaining of the revision under way unless the address names another basis, at the date of consumption, and shows its chart [WF-DEV-0100-A]", async () => {
    const page = text(html(await SpendingPage(at())));
    expect(queryOf(SPENDING_ROUTE)).toEqual({ basis: "current_remaining" });
    expect(page).toMatch(/Modernisation du poste de commande.*Spending projection/);
    expect(page).toContain(
      "Basis: Remaining of the current revision — revision “Current revision” — Date of consumption",
    );
    // Its chart under its caption, with the command of its export and its date of calculation.
    expect(page).toContain("Spending by cost type and by month Export as PNG Computed on");
  });

  it("asks the projection on the marked revision, at the date of payment, for the subproject chosen, the server filtering [WF-DEV-0100-A]", async () => {
    server.answers = { ...server.answers, [SPENDING_ROUTE]: "spending_marked_remaining" };
    const page = text(
      html(
        await SpendingPage(
          at({
            basis: "marked_remaining",
            spending_revision: MARKED,
            payment_delays: "true",
            subproject_id: SUBPROJECT,
          }),
        ),
      ),
    );
    expect(queryOf(SPENDING_ROUTE)).toEqual({
      basis: "marked_remaining",
      revision_id: MARKED,
      payment_delays: "true",
      subproject_id: SUBPROJECT,
    });
    expect(page).toContain(
      "Basis: Remaining of a marked revision — revision “Référence” — Date of payment",
    );
  });

  it("sends neither the marked revision with another basis nor the date of payment unasked, and offers the bases, the marked revisions, the dates and the subprojects [WF-DEV-0100-A]", async () => {
    server.answers = { ...server.answers, [SPENDING_ROUTE]: "spending_reference_budget" };
    const page = html(
      await SpendingPage(
        at({ basis: "reference_budget", spending_revision: MARKED, as_of: "2026-03-16" }),
      ),
    );
    expect(queryOf(SPENDING_ROUTE)).toEqual({ basis: "reference_budget" });
    expect(options(page, "basis")).toEqual([
      "Budget of the reference revision",
      "Remaining of a marked revision",
      "Remaining of the current revision",
    ]);
    expect(options(page, "spending_revision")).toEqual(["Référence", "Offre v1.0"]);
    expect(options(page, "payment_delays")).toEqual(["Date of consumption", "Date of payment"]);
    expect(options(page, "subproject_id").slice(0, 2)).toEqual([
      "Whole project",
      "Outside any subproject",
    ]);
    expect(options(page, "subproject_id")).toHaveLength(4);
    expect(page).toContain('type="hidden" name="as_of" value="2026-03-16"');
    expect(page).toMatch(/for="spending-basis"[^>]*>Basis<\/label>/);
  });

  it("offers the revision under way alone on a project with neither a reference nor a marked revision [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = html(await SpendingPage(at()));
    expect(options(page, "basis")).toEqual(["Remaining of the current revision"]);
  });

  it("presents the values of the chart in a table and the grid under it, the totals the API's, nothing summed [WF-DEV-0100-A] [WF-IHM-0130-A]", async () => {
    const plan = example("spending") as {
      total: string;
      cost_types: { label: string; total: string; categories: { label: string }[] }[];
    };
    const page = html(await SpendingPage(at()));
    const chart = page.indexOf("Spending by cost type and by month");
    const grid = page.indexOf('aria-label="Spending by cost type and by category"');
    expect(chart).toBeGreaterThan(0);
    expect(grid).toBeGreaterThan(chart);
    // One reading of the projection serves the chart and the grid.
    const calls = server.clients.flatMap((client) => client.calls);
    expect(calls.filter((call) => call.route === SPENDING_ROUTE)).toHaveLength(1);
    expect(page).toContain('aria-label="Spending projection by cost type and by category"');
    // The table of the values of the chart.
    for (const type of plan.cost_types) {
      expect(page).toContain(type.label.replaceAll("'", "&#x27;"));
    }
    expect(text(page)).toContain("Total of the projection");
    expect(page).toContain("66,997,090.97");
    expect(page.slice(grid)).not.toContain("<select");
  });

  it("says the projection unavailable on a project without a reference revision, and why, the choice left [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: { problem: example("spending_no_reference") as Problem & { status: 409 } },
    };
    const page = text(html(await SpendingPage(at({ basis: "reference_budget" }))));
    expect(page).toContain(
      "The projection is not available on the basis of the budget of the reference revision: the project has no reference revision.",
    );
    expect(page).toContain("Modernisation du poste de commande");
    expect(page).not.toContain("Spending by cost type and by month");
    expect(page).not.toContain("Total of the projection");
  });

  it("says the current revision is what the project lacks when the basis asked is its remaining [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: { problem: example("spending_no_reference") as Problem & { status: 409 } },
    };
    const page = text(html(await SpendingPage(at({ basis: "current_remaining" }))));
    expect(page).toContain(
      "The projection is not available on the basis of the remaining of the current revision: the project has no current revision.",
    );
    expect(page).not.toContain("no reference revision");
  });

  it("says no reason it cannot know when a marked revision basis is refused with a 409 [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: { problem: example("spending_no_reference") as Problem & { status: 409 } },
    };
    const page = text(
      html(await SpendingPage(at({ basis: "marked_remaining", spending_revision: REVISION }))),
    );
    expect(page).toContain("The projection is not available: the API refuses what is asked.");
  });

  it("says the projection unavailable on a marked revision the API refuses [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: {
        problem: example("spending_revision_refused") as Problem & { status: 422 },
      },
    };
    const page = text(
      html(await SpendingPage(at({ basis: "marked_remaining", spending_revision: REVISION }))),
    );
    expect(page).toContain(
      "The projection is not available on this basis: the marked revision asked for is missing, or is not marked.",
    );
  });

  it("says the projection unavailable on a subproject the project does not have [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: {
        problem: example("spending_subproject_unknown") as Problem & { status: 422 },
      },
    };
    const page = text(html(await SpendingPage(at({ subproject_id: SUBPROJECT }))));
    expect(page).toContain(
      "The projection is not available: the subproject asked for does not exist.",
    );
  });

  it("names the labour category without an hourly rate when the API refuses the projection for it [WF-DEV-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: { problem: example("spending_rate_missing") as Problem & { status: 422 } },
    };
    const page = text(html(await SpendingPage(at())));
    expect(page).toContain("Ingénierie électrique");
    expect(page).not.toContain("Spending by cost type and by month");
  });

  it.each([
    [[], "The projection is not available: the API refuses what is asked."],
    [
      [
        { pointer: "/query/revision_id", code: "VALIDATION_FAILED" },
        { pointer: "/query/subproject_id", code: "VALIDATION_FAILED" },
      ],
      "The projection is not available: the API refuses what is asked.",
    ],
  ] as const)("does not guess a reason from the fields %j", async (fields, sentence) => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: {
        problem: { code: "VALIDATION_FAILED", status: 422, fields: [...fields] },
      },
    };
    expect(text(html(await SpendingPage(at())))).toContain(sentence);
  });

  it("does not take a refusal of the same status for another reason as one of the basis", async () => {
    server.answers = {
      ...server.answers,
      [SPENDING_ROUTE]: { problem: { code: "ALREADY_EXISTS", status: 409 } },
    };
    await expect(SpendingPage(at())).rejects.toBeInstanceOf(UnexpectedAnswer);
  });

  it("is not found when the API does not find the project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(SpendingPage(at())).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});
