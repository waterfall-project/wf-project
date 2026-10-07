// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import TaskTreePage, { generateMetadata } from "./page";

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
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/task-tree";
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
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_core",
    "GET /projects/{project_id}/timelines": "timelines",
  };
});

/** The task tree at the query given. */
async function treeAt(search: Record<string, string> = {}) {
  return html(
    await TaskTreePage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

describe("the screen of the task tree", () => {
  it("names its leaf in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe("Task tree · Modernisation du poste de commande — Waterfall");
  });

  it("reads the tasks of the main structure, their parents, for the sub-project its banner shows", async () => {
    await treeAt({ subproject_id: SUBPROJECT });
    const { fields, ...query } = queryOf(NODES) ?? {};
    expect(query).toEqual({ kinds: "task", subproject_id: SUBPROJECT });
    expect(fields?.split(",")).toContain("parent_id");
    expect(fields?.split(",")).toContain("task.is_summary");
  });

  it("shows the summaries of the first two levels under the project, and the levels to choose, the one shown current", async () => {
    const page = await treeAt({ subproject_id: SUBPROJECT });
    expect(page).toMatch(/role="tree" aria-label="Tree of the summary tasks"/);
    expect(text(page)).toContain(
      "Modernisation du poste de commande 1 Études 8 Poste de commande 13 Risque survenu",
    );
    expect(page).toContain(`href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;depth=1"`);
    expect(page).toMatch(/aria-current="true"[^>]*>Level 2</);
    const first = await treeAt({ depth: "1" });
    expect(text(first)).not.toContain("Risque survenu");
    expect(first).toMatch(/aria-current="true"[^>]*>Level 1</);
  });
});
