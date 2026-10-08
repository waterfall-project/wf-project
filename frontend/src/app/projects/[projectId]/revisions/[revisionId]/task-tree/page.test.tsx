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
    [NODES]: "nodes_summaries",
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

  it("asks the server for the summaries down to the depth of the address, their parents, for the sub-project its banner shows [WF-PLA-0110-A]", async () => {
    // Sur un planning de quatre niveaux, l'affichage demandé au niveau 2 ne représente que les
    // récapitulatives des deux premiers niveaux : the server selects them, the screen asks it.
    await treeAt({ subproject_id: SUBPROJECT });
    const { fields, ...query } = queryOf(NODES) ?? {};
    expect(query).toEqual({
      kinds: "task",
      subproject_id: SUBPROJECT,
      summaries_only: "true",
      max_level: "2",
    });
    expect(fields?.split(",")).toContain("parent_id");
    server.clients = [];
    await treeAt({ depth: "1" });
    expect(queryOf(NODES)).toMatchObject({ summaries_only: "true", max_level: "1" });
  });

  it("draws the summaries the server renders under the project, and the levels to choose, the one shown current [WF-PLA-0110-A]", async () => {
    const page = await treeAt({ subproject_id: SUBPROJECT });
    expect(page).toMatch(/role="tree" aria-label="Tree of the summary tasks"/);
    expect(text(page)).toContain(
      "Modernisation du poste de commande 1 Études 8 Installation sur site 9 Poste de commande",
    );
    expect(page).toContain(`href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;depth=1"`);
    expect(page).toMatch(/aria-current="true"[^>]*>Level 2</);
    // A summary at the second level may have summaries under it: the third is offered.
    expect(page).toContain(`href="${SCREEN}?subproject_id=${SUBPROJECT}&amp;depth=3"`);
    const first = await treeAt({ depth: "1" });
    expect(first).toMatch(/aria-current="true"[^>]*>Level 1</);
  });

  it("is the project alone, with no level to choose, for a plan of leaves alone [WF-PLA-0110-A]", async () => {
    // Un planning composé uniquement de tâches feuilles produit une arborescence réduite au nœud
    // du projet.
    server.answers = { ...server.answers, [NODES]: "nodes_summaries_leaves" };
    const page = await treeAt();
    expect(page).toMatch(/role="tree" aria-label="Tree of the summary tasks"/);
    expect(page.match(/role="treeitem"/g)).toHaveLength(1);
    expect(page).not.toContain('aria-label="Level shown"');
    expect(text(page)).toContain(
      "This plan has no summary task: the tree comes down to the project.",
    );
  });

  it("keeps the summaries down to the depth asked of an answer that holds more, as the fake back renders it [WF-PLA-0110-A]", async () => {
    // Aucun jalon ni aucune tâche feuille n'apparaît, quel que soit le niveau demandé.
    server.answers = { ...server.answers, [NODES]: "nodes_core" };
    const page = await treeAt();
    expect(text(page)).toContain(
      "Modernisation du poste de commande 1 Études 8 Poste de commande 13 Risque survenu",
    );
    for (const absent of ["Réception des études", "Câblage des armoires", "Réception usine"]) {
      expect(text(page)).not.toContain(absent);
    }
  });
});
