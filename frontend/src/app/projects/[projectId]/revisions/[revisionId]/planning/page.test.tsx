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
async function planning() {
  return html(
    await PlanningPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve({}),
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
    "GET /session": "session",
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

  it("reads no work breakdown for a revision that may not be planned, and says nothing of the fake back", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
    };
    const page = await planning();
    expect(callsOf(BREAKDOWN)).toEqual([]);
    expect(page).not.toContain("Mock-up:");
  });
});
