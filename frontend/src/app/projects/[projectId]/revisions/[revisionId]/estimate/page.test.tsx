// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EstimateGridProps } from "@/components/grid/estimate-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import EstimatePage from "./page";

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
// The grid is not rendered: the page is read for what it asks and what it hands its grid.
const grids = vi.hoisted((): { estimate: EstimateGridProps[] } => ({ estimate: [] }));
vi.mock("@/components/grid/estimate-grid", () => ({
  EstimateGrid: (props: EstimateGridProps) => {
    grids.estimate.push(props);
    return null;
  },
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The query the page asked a list of the reference with, by the end of its route. */
function queryOf(end: string): URLSearchParams | undefined {
  return server.clients.flatMap((client) => client.calls).find((call) => call.route.endsWith(end))
    ?.query;
}

/** The markup of the estimate of the witness revision for the session given. */
async function estimatePage(session: "me" | "me_estimator" | "me_manager"): Promise<string> {
  server.answers = { ...server.answers, "GET /me": session };
  const page = await EstimatePage({
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve({}),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** Read the estimate of the witness revision for the session given; its grid as handed. */
async function estimateFor(session: "me" | "me_estimator") {
  await estimatePage(session);
  return grids.estimate.at(-1);
}

beforeEach(() => {
  grids.estimate = [];
  server.clients = [];
  server.answers = {
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": "nodes",
    "GET /projects/{project_id}/estimate-indicators": "estimate_indicators",
    "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates_none",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
    "GET /projects/{project_id}/subprojects": "subprojects",
  };
});

describe("the reference data the estimate is entered from", () => {
  it("asks the deactivated categories and roles with the permissions of the reference that keep them", async () => {
    const grid = await estimateFor("me");
    expect(queryOf("/cost-categories")?.get("include_inactive")).toBe("true");
    expect(queryOf("/resource-roles")?.get("include_inactive")).toBe("true");
    expect(grid?.reference.roles?.some(({ active }) => !active)).toBe(true);
  });

  it("asks only the active ones of a part of the reference the session may not read, and still enters the estimate on them (#351)", async () => {
    // The estimator reads the cost settings, not the resource settings: the contract would refuse
    // him the deactivated roles (403), and he enters on the active ones.
    const grid = await estimateFor("me_estimator");
    expect(queryOf("/cost-categories")?.get("include_inactive")).toBe("true");
    expect(queryOf("/resource-roles")?.has("include_inactive")).toBe(false);
    expect(grid?.reference.roles).toBeDefined();
    expect(grid?.editable).toBe(true);
  });
});

describe("the way from the estimate to the imports and exports (#521)", () => {
  it("leads a costing engineer who does not read the planning to the screen of the imports, the import of an estimate listed", async () => {
    const page = await estimatePage("me_estimator");
    expect(page).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/exchanges"`);
    expect(page).toContain("Imports and exports");
  });

  it("leads there too when the import is listed unavailable, which that screen presents with what it lacks (WF-IHM-0090)", async () => {
    // The import of an estimate listed unavailable, lacking `may_create_revision`.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    expect(await estimatePage("me_estimator")).toContain("/exchanges");
  });

  it("offers no way there when the project lists no import of an estimate", async () => {
    // A manager reads the estimate, and may import nothing: the project lists him no command.
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_reader" };
    expect(await estimatePage("me_manager")).not.toContain("/exchanges");
  });
});
