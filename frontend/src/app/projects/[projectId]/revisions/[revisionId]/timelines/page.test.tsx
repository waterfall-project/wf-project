// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import TimelinesPage, { generateMetadata } from "./page";

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
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const SCREEN =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/timelines";
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";

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

/** The query of the call of a route, as the client serialized it. */
function queryOf(route: string): Record<string, string> | undefined {
  const call = server.clients.flatMap((client) => client.calls).find((c) => c.route === route);
  return call === undefined ? undefined : Object.fromEntries(call.query);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_timeline",
    "GET /projects/{project_id}/timelines": "timelines",
  };
});

const STEERING = "01926f3a-7c00-7000-8000-000000001000";
const CUSTOMER = "01926f3a-7c00-7000-8000-000000001001";

/** The timelines at the query given. */
async function timelinesAt(search: Record<string, string> = {}) {
  return html(
    await TimelinesPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

describe("the screen of the timelines", () => {
  it("names its leaf in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe("Timelines · Modernisation du poste de commande — Waterfall");
  });

  it("offers the timelines of the project, the first shown, and the tasks the server renders for it on their axis", async () => {
    const page = await timelinesAt({ subproject_id: SUBPROJECT });
    expect(page).toMatch(/aria-current="true"[^>]*>Comité de pilotage</);
    expect(page).toContain(`href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;timeline=${CUSTOMER}"`);
    const table = page.slice(page.indexOf('aria-label="Comité de pilotage"'));
    expect(text(table)).toContain(
      "1 Études 02/03/2026 24/04/2026 6 Réception des études 24/04/2026 24/04/2026 " +
        "18 Réception usine 30/06/2026 30/06/2026 23 Mise en service",
    );
    expect(table).toContain('aria-label="Milestone on 24/04/2026 — critical"');
    // The server selects the tasks of the timeline shown, for the sub-project the banner shows.
    const { fields, ...query } = queryOf(NODES) ?? {};
    expect(query).toEqual({ kinds: "task", subproject_id: SUBPROJECT, timeline_id: STEERING });
    expect(fields?.split(",")).toContain("task.tracking");
  });

  it("asks the server for the tasks of the timeline the address names, and draws them [WF-PLA-0140-A]", async () => {
    // Deux chronologies d'un même projet portent des sélections distinctes : each is asked of the
    // server by its own identifier, and the screen draws what it renders, selecting nothing.
    const page = await timelinesAt({ timeline: CUSTOMER });
    expect(page).toMatch(/aria-current="true"[^>]*>Revue client</);
    expect(queryOf(NODES)).toMatchObject({ timeline_id: CUSTOMER });
    expect(text(page.slice(page.indexOf('aria-label="Revue client"')))).toContain(
      "6 Réception des études",
    );
  });

  it("keeps the tasks inscribed to the timeline of an answer that holds more, as the fake back renders it [WF-PLA-0140-A]", async () => {
    // Deux chronologies d'un même projet portent des sélections distinctes: the customer's, the
    // two receptions alone, the core read whole.
    server.answers = { ...server.answers, [NODES]: "nodes_core" };
    const table = text(
      (await timelinesAt({ timeline: CUSTOMER })).split('aria-label="Revue client"')[1] ?? "",
    );
    expect(table).toContain("6 Réception des études");
    expect(table).toContain("18 Réception usine");
    expect(table).not.toContain("Études 02/03/2026");
    expect(table).not.toContain("Mise en service");
  });

  it("says a timeline holds no task of the revision read", async () => {
    server.answers = { ...server.answers, [NODES]: "nodes_risk_occurred" };
    const empty = await timelinesAt({ timeline: CUSTOMER });
    expect(text(empty)).toContain("No task of this revision is inscribed to this timeline.");
  });

  it("reads no task of a project without a timeline, says it has none, and shows no filter in its banner (#302)", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/timelines": "timelines_empty",
    };
    const page = await timelinesAt({ subproject_id: SUBPROJECT });
    expect(queryOf(NODES)).toBeUndefined();
    const banner = page.slice(0, page.indexOf("</section>"));
    expect(banner).toContain('aria-label="Reading context"');
    expect(text(banner)).not.toContain("Subproject");
    expect(text(page)).toContain("This project has no timeline.");
  });
});
