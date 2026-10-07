// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import {
  ContributorList,
  SubprojectList,
  TransitionList,
} from "@/components/projects/project-tables";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import LifecyclePage, { generateMetadata as lifecycleMetadata } from "./lifecycle/page";
import ProjectPage from "./page";
import SettingsPage, { generateMetadata as settingsMetadata } from "./settings/page";

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
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const BANNER = '<section aria-label="Reading context"';

type StateTransition = components["schemas"]["StateTransition"];

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
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** What Next hands a page of the project, at the query given. */
function at(search: Record<string, string> = {}) {
  return {
    params: Promise.resolve({ projectId: PROJECT }),
    searchParams: Promise.resolve(search),
  };
}

/** The paths the pages asked the API for, by route. */
function paths(): Record<string, string> {
  return Object.fromEntries(
    server.clients.flatMap((client) => client.calls).map((call) => [call.route, call.path]),
  );
}

/** The names of the buttons of a page. */
function buttons(markup: string): string[] {
  return [...markup.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((match) => text(match[1] ?? ""));
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/contributors": "contributors",
    "GET /projects/{project_id}/state-transitions": "state_transitions",
  };
});

describe("the screen of a project", () => {
  it("shows what the project is as the API reads it, a value it lacks said missing, never invented", async () => {
    const page = html(await ProjectPage(at()));
    expect(text(page)).toContain(
      "Code PRJ-001 State In progress Order received on 15 Jan 2026 Description Not set",
    );
    expect(page).toContain('<dl aria-label="The project"');
  });

  it("names each revision by its version name, and the draft without one the current revision, from its status", async () => {
    const page = html(await ProjectPage(at()));
    expect(text(page)).toContain("Revisions Référence Current revision");
  });

  it("opens each revision with the filters of its address, the revision it was read in left to the link", async () => {
    const subproject = "01926f3a-7c00-7000-8000-000000000801";
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_offer",
    };
    const page = html(
      await ProjectPage(
        at({
          revision_id: "01926f3a-7c00-7000-8000-000000000100",
          subproject_id: subproject,
          as_of: "2026-05-31",
        }),
      ),
    );
    const revision = `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102`;
    expect(page).toContain(`href="${revision}?subproject_id=${subproject}&amp;as_of=2026-05-31"`);
    expect(html(await ProjectPage(at()))).toContain(`href="${revision}"`);
  });

  it("offers nothing to create or modify: those forms belong to the epic of their domain", async () => {
    const page = html(await ProjectPage(at()));
    expect(buttons(page)).toEqual([]);
    expect(page).not.toContain("<form");
  });
});

describe("the settings of a project", () => {
  it("shows the inflation rate and the probability of winning as the API gives them", async () => {
    const page = html(await SettingsPage(at()));
    expect(page.startsWith(BANNER)).toBe(true);
    expect(page).toMatch(
      /<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Project settings<\/h1>/,
    );
    expect(text(page)).toContain("Annual inflation rate 3% Probability of winning 100%");
  });

  it("lists the sub-projects of the project, each by its ERP code, and whether actual costs are charged to it", async () => {
    const page = html(await SettingsPage(at()));
    expect(paths()["GET /projects/{project_id}/subprojects"]).toBe(
      `/projects/${PROJECT}/subprojects`,
    );
    expect(page).toMatch(/<h2[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Subprojects<\/h2>/);
    expect(text(page)).toContain(
      "Subprojects ERP code Label Actual costs SP-CMD Poste de commande Charged SP-ESS Essais et mise en service None",
    );
  });

  it("lists the contributors of the project, the project manager told from a contributor in words and by an icon, an account deactivated since said so", async () => {
    const page = html(await SettingsPage(at()));
    expect(paths()["GET /projects/{project_id}/contributors"]).toBe(
      `/projects/${PROJECT}/contributors`,
    );
    expect(text(page)).toContain(
      "Contributors Name Capacity Account " +
        "Camille Martin Project manager Active Alix Moreau Contributor Deactivated " +
        "Lucas Petit Contributor Active Inès Roux Contributor Active",
    );
    // The project manager alone bears the icon, beside the words that say it.
    const capacities = [...page.matchAll(/<td[^>]*>(.*?)<\/td>/g)]
      .map((match) => match[1] ?? "")
      .filter((cell) => /Project manager|^Contributor$/.test(text(cell)));
    expect(capacities).toHaveLength(4);
    expect(capacities[0]).toMatch(/<svg[^>]*aria-hidden="true"[^>]*>.*<\/svg>Project manager/);
    expect(capacities.slice(1)).toEqual(["Contributor", "Contributor", "Contributor"]);
  });

  it("offers nothing to create or modify: those forms belong to the epic of their domain", async () => {
    const page = html(await SettingsPage(at()));
    expect(buttons(page)).toEqual([]);
    expect(page).not.toContain("<form");
  });

  it("is not found for a project the API does not find, as the other screens of a project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}/contributors": NOT_FOUND };
    await expect(SettingsPage(at())).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    server.answers = { ...server.answers, "GET /projects/{project_id}": NOT_FOUND };
    await expect(SettingsPage(at())).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("is not found at an address that names no project, before the API is asked", async () => {
    const page = SettingsPage({
      params: Promise.resolve({ projectId: "a.b" }),
      searchParams: Promise.resolve({}),
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("titles the tab with the settings and the project", async () => {
    const params = Promise.resolve({ projectId: PROJECT });
    expect((await settingsMetadata({ params })).title).toBe(
      "Project settings · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the lifecycle of a project", () => {
  it("on a project in pricing, presents completion unavailable, naming the condition it lacks [WF-IHM-0090-A]", async () => {
    // Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en
    // nommant la condition manquante.
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_pricing" };
    const page = html(await LifecyclePage(at()));
    const complete =
      /<button[^>]*aria-disabled="true"[^>]*aria-describedby="([^"]+)"[^>]*>(?:(?!<\/button>).)*Complete the project<\/button>/.exec(
        page,
      );
    expect(complete).not.toBeNull();
    expect(page).toContain(`id="${complete?.[1] ?? ""}"`);
    expect(text(page)).toContain("Complete the project Unmet condition: project in progress.");
  });

  it("offers the exits of the lifecycle alone, in the order of the server: nothing to create or modify", async () => {
    const page = html(await LifecyclePage(at()));
    expect(page.startsWith(BANNER)).toBe(true);
    expect(buttons(page)).toEqual([
      "Complete the project",
      "Declare the project lost",
      "Abandon the project",
    ]);
  });

  it("shows the current state of the project, and the history of its states, each transition dated as the API gives it and by whom [WF-ARC-0020-A]", async () => {
    // Les montants, dates et indices affichés sont ceux que l'API renvoie, sans recalcul.
    const page = html(await LifecyclePage(at()));
    expect(paths()["GET /projects/{project_id}/state-transitions"]).toBe(
      `/projects/${PROJECT}/state-transitions`,
    );
    expect(text(page)).toMatch(/^.*Project lifecycle State In progress/);
    expect(text(page)).toContain(
      "History of states Date Transition By Reason " +
        "Creation Created Camille Martin Created Pricing Camille Martin Pricing In progress Camille Martin",
    );
    // Each instant, in the local time of the workstation, which the browser writes.
    expect([...page.matchAll(/<time dateTime="([^"]+)"/g)].map((match) => match[1])).toEqual([
      "2025-10-06T09:00:00Z",
      "2025-11-03T08:30:00Z",
      "2026-01-15T11:00:00Z",
    ]);
  });

  it.each([
    ["the history of its states", "GET /projects/{project_id}/state-transitions"],
    ["the project", "GET /projects/{project_id}"],
  ] as const)(
    "is not found when the API does not find %s, as the other screens of a project",
    async (_, route) => {
      server.answers = { ...server.answers, [route]: NOT_FOUND };
      await expect(LifecyclePage(at())).rejects.toMatchObject({
        digest: "NEXT_HTTP_ERROR_FALLBACK;404",
      });
    },
  );

  it("is not found at an address that names no project, before the API is asked", async () => {
    const page = LifecyclePage({
      params: Promise.resolve({ projectId: "a.b" }),
      searchParams: Promise.resolve({}),
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("titles the tab with the lifecycle and the project", async () => {
    const params = Promise.resolve({ projectId: PROJECT });
    expect((await lifecycleMetadata({ params })).title).toBe(
      "Project lifecycle · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the lists of a project", () => {
  it("say a list is empty, rather than showing an empty table", () => {
    const page = html(
      <>
        <SubprojectList subprojects={[]} />
        <ContributorList contributors={[]} />
        <TransitionList transitions={[]} />
      </>,
    );
    expect(text(page)).toBe(
      "Subprojects This project has no subproject. Contributors This project has no contributor. " +
        "History of states No transition is recorded.",
    );
    expect(page).not.toContain("<table");
  });

  it("name an automatic process of the platform for a transition no user made", () => {
    const [created] = example("state_transitions") as StateTransition[];
    const page = html(
      <TransitionList
        transitions={created === undefined ? [] : [{ ...created, actor: { kind: "platform" } }]}
      />,
    );
    expect(text(page)).toContain("Creation Created Automatic process");
  });

  it("show the motive of an exit to Lost as the user gave it, and none for a transition without one [WF-CYC-0130-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/state-transitions": "state_transitions_exited",
    };
    const page = html(await LifecyclePage(at()));
    const rows = [...page.matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((match) => match[1] ?? "");
    const reasons = rows
      .filter((row) => row.includes("<td"))
      .map((row) => [...row.matchAll(/<td[^>]*>(.*?)<\/td>/g)].at(-1)?.[1]);
    expect(reasons).toEqual([
      "",
      "",
      "Offre non retenue : le client a préféré une solution sur étagère.",
    ]);
    expect(text(page)).toContain(
      "Pricing Lost Camille Martin Offre non retenue : le client a préféré une solution sur étagère.",
    );

    // An automatic transition bears none.
    const [created] = example("state_transitions_exited") as StateTransition[];
    const automatic = html(
      <TransitionList
        transitions={created === undefined ? [] : [{ ...created, actor: { kind: "platform" } }]}
      />,
    );
    expect(automatic).toMatch(/Automatic process<\/span><\/td><td[^>]*><\/td><\/tr>/);
  });

  it("say actual costs charged to a sub-project", () => {
    const [subproject] = example("subprojects") as components["schemas"]["Subproject"][];
    const page = html(
      <SubprojectList
        subprojects={subproject === undefined ? [] : [{ ...subproject, has_actual_costs: true }]}
      />,
    );
    expect(text(page)).toContain("SP-CMD Poste de commande Charged");
  });
});
