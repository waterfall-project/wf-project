// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import PlanningPage from "./page";

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
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const BREAKDOWN = "GET /projects/{project_id}/work-breakdown";
// The lot of the witness and its post, as its work breakdown names them.
const LOT = "01926f3a-7c00-7000-8000-000000000711";
const ITEM = "01926f3a-7c00-7000-8000-000000000712";
// The button of the skeleton, from its tag to its name.
const SKELETON = /<button(?:(?!<button).)*?Generate the schedule skeleton<\/button>/;

/** Render in English, as the shell hands its texts to a screen. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

/** The planning of the revision of the address, as the fake back answers it. */
async function planning(search: Record<string, string> = {}) {
  return html(
    await PlanningPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

/** The calls of a route the page made. */
function callsOf(route: string) {
  return server.clients.flatMap((client) => client.calls).filter((call) => call.route === route);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_planning",
    [BREAKDOWN]: "work_breakdown",
  };
});

describe("the screen of the planning", () => {
  it("offers the skeleton in the empty grid of a revision that lists it available, and says the fake back keeps nothing", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_without_tasks",
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures_without_tasks",
      [NODES]: "nodes_empty",
      [BREAKDOWN]: "work_breakdown_default",
    };
    const page = await planning();
    const command = SKELETON.exec(page)?.[0] ?? "";
    expect(command).not.toBe("");
    expect(command).not.toContain(" aria-disabled=");
    expect(page).toContain("Mock-up: the simulated service answers each write");
  });

  it("enters the attachment from the work breakdown read whole, and offers no skeleton beside the tasks", async () => {
    const page = await planning();
    expect(page).toMatch(/<th(?:(?!<\/th>).)*>Attached to</);
    expect(page).not.toMatch(SKELETON);
    const [read] = callsOf(BREAKDOWN);
    expect(read?.path).toBe(`/projects/${PROJECT}/work-breakdown`);
    expect(read?.query.toString()).toBe("");
  });

  it("reads the work breakdown whole for its filter alone on a revision that may not be planned, and says nothing of the fake back", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures_amendments",
    };
    const page = await planning();
    const [read] = callsOf(BREAKDOWN);
    expect(read?.query.toString()).toBe("");
    expect(page).toContain(`<option value="${ITEM}">Order item: Poste 1.1</option>`);
    expect(page).not.toContain("Mock-up:");
  });
});

describe("the filter of the planning by a lot or a post", () => {
  it("offers the lots and the posts of the work breakdown read whole, named by their kind, and filters nothing by default", async () => {
    const page = await planning();
    expect(page).toMatch(/<label[^>]*>Work package or order item<\/label>/);
    // The lot, then its post, in the order of the work breakdown, after the choice that lifts it.
    expect(page).toContain(
      `<option value="" selected="">All work packages and order items</option>` +
        `<option value="${LOT}">Work package: Lot 1</option>` +
        `<option value="${ITEM}">Order item: Poste 1.1</option>`,
    );
    const [read] = callsOf(NODES);
    expect(read?.query.get("work_package_id")).toBeNull();
    expect(read?.query.get("order_item_id")).toBeNull();
    expect(page).not.toContain("Active filters");
  });

  it("asks the server for the subtree of the post the address names, shows it chosen and active in the banner, lifted with the rest of the address kept", async () => {
    const page = await planning({ order_item_id: ITEM, search: "Revue" });
    const [read] = callsOf(NODES);
    expect(read?.query.get("order_item_id")).toBe(ITEM);
    expect(read?.query.get("work_package_id")).toBeNull();
    expect(read?.query.get("search")).toBe("Revue");
    expect(page).toContain(`<option value="${ITEM}" selected="">Order item: Poste 1.1</option>`);
    const chips = /<ul aria-label="Active filters"(?:(?!<\/ul>).)*<\/ul>/.exec(page)?.[0] ?? "";
    expect(chips).toContain("Order item: Poste 1.1");
    expect(chips).toContain(
      `href="/projects/${PROJECT}/revisions/${REVISION}/planning?search=Revue"`,
    );
    expect(chips).toContain(`aria-label="Remove the filter “Order item: Poste 1.1”"`);
  });

  it("asks the subtree of the lot the address names, the post it would name besides not read", async () => {
    const page = await planning({ work_package_id: LOT, order_item_id: ITEM });
    const [read] = callsOf(NODES);
    expect(read?.query.get("work_package_id")).toBe(LOT);
    expect(read?.query.get("order_item_id")).toBeNull();
    expect(page).toContain(`<option value="${LOT}" selected="">Work package: Lot 1</option>`);
    // The chip lifts both: the post left in the address would take the place of the lot.
    expect(page).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/planning"`);
  });
});

describe("the planning whose work breakdown the API refuses", () => {
  it.each([
    { code: "NOT_FOUND", status: 404 },
    { code: "VALIDATION_FAILED", status: 422 },
    { code: "COMPONENT_UNAVAILABLE", status: 503 },
  ] as const)(
    "opens without the filter on a revision that may not be planned ($status), the post of the address read and shown active",
    async (problem) => {
      server.answers = {
        ...server.answers,
        "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
        [BREAKDOWN]: { problem },
      };
      const page = await planning({ order_item_id: ITEM });
      expect(page).not.toContain("Work package or order item");
      const [read] = callsOf(NODES);
      expect(read?.query.get("order_item_id")).toBe(ITEM);
      const chips = /<ul aria-label="Active filters"(?:(?!<\/ul>).)*<\/ul>/.exec(page)?.[0] ?? "";
      expect(chips).toContain(ITEM);
      expect(chips).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/planning"`);
    },
  );

  it("is not found where the attachment is entered, which cannot do without the work breakdown", async () => {
    server.answers = {
      ...server.answers,
      [BREAKDOWN]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(planning()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("fails where the attachment is entered on a work breakdown the API cannot answer", async () => {
    server.answers = {
      ...server.answers,
      [BREAKDOWN]: { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } },
    };
    await expect(planning()).rejects.toMatchObject({ name: "UnexpectedAnswer" });
  });
});

describe("a lot or a post of the address that is no identifier", () => {
  it("is neither sent to the server nor shown active, the post the address names read in its place", async () => {
    const page = await planning({ work_package_id: "pas-un-uuid", order_item_id: ITEM });
    const [read] = callsOf(NODES);
    expect(read?.query.get("work_package_id")).toBeNull();
    expect(read?.query.get("order_item_id")).toBe(ITEM);
    expect(page).not.toContain("pas-un-uuid");
  });

  it("leaves the grid unfiltered when it is the one the address names", async () => {
    const page = await planning({ order_item_id: "../x" });
    const [read] = callsOf(NODES);
    expect(read?.query.get("order_item_id")).toBeNull();
    expect(page).not.toContain("Active filters");
  });
});
