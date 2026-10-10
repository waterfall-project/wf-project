// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StartableTasks } from "@/components/remaining/kanban";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import KanbanPage, { generateMetadata } from "./page";

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
const STARTABLE = "GET /projects/{project_id}/remaining-indicators/startable-tasks";
const REVISION_READ = "GET /projects/{project_id}/revisions/{revision_id}";

const TASKS = example("startable_tasks") as StartableTasks;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** The markup of the column of the Kanban a page names so. */
function column(markup: string, name: string): string {
  return (
    new RegExp(`<section aria-label="${name}"[^>]*>(.*?)</section>`, "s").exec(markup)?.[1] ?? ""
  );
}

/** Render in English, as the shell hands its texts to a screen. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

/** The Kanban at the query given. */
async function kanbanAt(search: Record<string, string> = {}) {
  return html(
    await KanbanPage({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
      searchParams: Promise.resolve(search),
    }),
  );
}

/** The calls of a route, all clients together. */
function callsTo(route: string) {
  return server.clients.flatMap((client) => client.calls).filter((call) => call.route === route);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    [REVISION_READ]: "revision",
    [STARTABLE]: "startable_tasks",
  };
});

describe("the Kanban of the start of the tasks", () => {
  it("names its leaf in the tab, with the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe(
      "Kanban — task start · Modernisation du poste de commande — Waterfall",
    );
  });

  it("presents every task not started, those started and those completed, each a card of its number, its label and its finish, the overdue marked, and no milestone signalled whose predecessors are not all completed [WF-RAE-0030-A]", async () => {
    // Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non démarré tant
    // que personne ne le termine. Here the tasks of every state, none such a milestone: the
    // factory acceptance waits for the wiring, and is not signalled.
    const page = await kanbanAt();
    expect(callsTo(STARTABLE).map((call) => call.path)).toEqual([
      `/projects/${PROJECT}/remaining-indicators/startable-tasks`,
    ]);
    // Every task of the structure that is not a summary, each column in the order of the plan:
    // the tasks of the core first, then those drawn around it (EP-14/L45b) — the first of them
    // read here, the others counted: one card per task the API gives, none left out by the front.
    // The tasks not started whose predecessors are not completed too (#425): the assembly on site
    // and the commissioning wait for the wiring, and are presented all the same.
    const columns = [
      [
        "Not started",
        TASKS.not_started,
        "Not started 18 Milestone Réception usine Finish on 30/06/2026 20 Montage des armoires sur site Finish on 18/12/2026 23 Mise en service Finish on 01/01/2027 " +
          "27 Préparation 1.1.1 Finish on 14/07/2026 ",
      ],
      [
        "Started",
        TASKS.started,
        "Started 4 Pupitres opérateurs Finish on 24/04/2026 Finish overdue 9 Câblage des armoires Finish on 30/06/2026 " +
          "311 Revue 1.2.11 Finish on 10/06/2026 ",
      ],
      [
        "Completed",
        TASKS.completed,
        "Completed 2 Études de détail Completed on 10/04/2026 5 Revue de conception Completed on 24/04/2026 " +
          "6 Milestone Réception des études Completed on 24/04/2026 7 Dossier de conception Completed on 15/04/2026 " +
          "14 Relance du fournisseur Completed on 08/05/2026 16 Transport exceptionnel Completed on 15/05/2026 " +
          "247 Préparation 1.2.1 Completed on 01/05/2026 ",
      ],
    ] as const;
    for (const [name, tasks, head] of columns) {
      const markup = column(page, name);
      expect(text(markup).slice(0, head.length)).toBe(head);
      expect(markup.match(/<li\b/g)).toHaveLength(tasks.length);
    }
    // No milestone is signalled whose predecessors are not all completed: the factory acceptance
    // waits for the wiring.
    expect(text(page)).not.toContain("milestone to complete");
    expect(page.match(/aria-label="Finish overdue"/g)).toHaveLength(1);
  });

  it("invites one to complete a milestone whose predecessors are completed, which stays not started until someone does [WF-RAE-0030-A]", async () => {
    // Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non démarré tant
    // que personne ne le termine.
    server.answers = { ...server.answers, [STARTABLE]: "startable_tasks_milestone" };
    const page = await kanbanAt();
    expect(text(page)).toContain(
      "Not started 18 Milestone Réception usine Finish on 30/06/2026 Its predecessors are completed: milestone to complete. 20 Montage des armoires sur site",
    );
    // The milestone alone is signalled, not the tasks whose predecessors are not completed.
    expect(text(page).match(/milestone to complete/g)).toHaveLength(1);
    expect(page).toContain('aria-label="Milestone"');
  });

  it("offers no percentage to enter, nor any command: nothing takes a task started back to not started [WF-RAE-0030-A]", async () => {
    // Aucune commande ne fait passer une tâche démarrée à l'état non démarré — nor does the
    // mock-up offer one to start or complete a task (US-0230): no field, no button, no figure.
    const page = await kanbanAt();
    const main = page.slice(page.indexOf("<main"));
    expect(main).not.toMatch(/<(input|button|select|textarea)\b/);
    expect(main).not.toMatch(/role="(slider|spinbutton|progressbar)"/);
    expect(text(main)).not.toContain("%");
  });

  it("shows no filter of the address in its banner, the Kanban reading none (#302)", async () => {
    const page = await kanbanAt({ as_of: "2026-05-31" });
    expect(text(page)).not.toContain("Calculation date");
  });

  it("asks nothing in a marked revision, and says the Kanban reads the revision in progress", async () => {
    server.answers = { ...server.answers, [REVISION_READ]: "revision_marked" };
    const page = await kanbanAt();
    expect(callsTo(STARTABLE)).toEqual([]);
    expect(text(page)).toContain(
      "The Kanban presents the tasks of the revision in progress: a marked revision has none to start.",
    );
  });

  it("is not found when the API does not find the revision", async () => {
    server.answers = {
      ...server.answers,
      [REVISION_READ]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(kanbanAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});
