// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { TransitionList } from "@/components/projects/project-tables";
import {
  ContributorList,
  SubprojectList,
  WorkBreakdownList,
} from "@/components/projects/settings-lists";
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
const navigation = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001/settings",
  useSearchParams: () => new URLSearchParams(navigation.search),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const BANNER = '<section aria-label="Reading context"';

type StateTransition = components["schemas"]["StateTransition"];
type WorkBreakdown = components["schemas"]["WorkBreakdown"];

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

/** The calls the pages made to an operation, each by its query. */
function queriesOf(route: string): Record<string, string>[] {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => Object.fromEntries(call.query));
}

/** The table a page names, its inner markup. */
function table(markup: string, name: string): string {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === name,
  );
  expect(found).toBeDefined();
  return found?.[2] ?? "";
}

/** The texts of the rows of a table of a page, by its name. */
function rows(markup: string, name: string): string[] {
  return [...table(markup, name).matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((row) =>
    text(row[1] ?? ""),
  );
}

/** The headings of the columns a grid sorts — those whose header holds a button —, of all its grids. */
function sortable(markup: string, name?: string): string[] {
  const head = /<thead[^>]*>(.*?)<\/thead>/.exec(name === undefined ? markup : table(markup, name));
  return [...(head?.[1] ?? "").matchAll(/<th[^>]*>(.*?)<\/th>/g)]
    .filter((header) => (header[1] ?? "").includes("<button"))
    .map((header) => text(header[1] ?? ""));
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
    "GET /projects/{project_id}/contributors/suggestions": "contributor_suggestions",
    "GET /projects/{project_id}/work-breakdown": "work_breakdown",
    "GET /projects/{project_id}/state-transitions": "state_transitions",
    "GET /projects/{project_id}/next-state": "next_state",
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
    expect(text(page)).toContain(
      "Label Modernisation du poste de commande Code PRJ-001 Order received on 15 Jan 2026 " +
        "Description Not set Annual inflation rate 3% Probability of winning 100%",
    );
  });

  it("shows the work breakdown of the project, read by the server, in a region of its own: a tree of each order item, its work packages under it and their deliverables under them, which sorts nothing and folds", async () => {
    const page = html(await SettingsPage(at()));
    expect(paths()["GET /projects/{project_id}/work-breakdown"]).toBe(
      `/projects/${PROJECT}/work-breakdown`,
    );
    const region = /<section aria-label="Work breakdown"[^>]*>(.*?)<\/section>/.exec(page)?.[1];
    expect(region).toMatch(
      /<h2[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Work breakdown<\/h2>/,
    );
    expect(rows(region ?? "", "Work breakdown")).toEqual([
      "Label Kind",
      "Fourniture et montage des armoires Order item",
      "Armoires Work package",
      "Procès-verbal de réception usine des armoires Deliverable",
      "1 order item",
    ]);
    expect(region).toMatch(/<table[^>]*role="treegrid"[^>]*aria-label="Work breakdown"/);
    expect(region).toContain('aria-level="3"');
    expect(sortable(region ?? "")).toEqual([]);
    // Searched by the server on its labels, filtered on its kinds; read whole, nothing says it
    // partial.
    expect(region).toContain('type="search"');
    expect(text(region ?? "")).toContain("Every kind Order item Work package Deliverable");
    expect(text(region ?? "")).not.toContain("show only what the search and the filter retain");
  });

  it("asks the server for the search and the kinds of the work breakdown the address names, under the names of the contract, and says the order items and work packages kept partial", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/work-breakdown": "work_breakdown_work_packages",
    };
    const page = html(
      await SettingsPage(
        at({
          breakdown_search: "Armoires",
          breakdown_kinds: "deliverable,unknown,work_package",
          // The names of the contract alone belong to no grid of this screen.
          kinds: "order_item",
        }),
      ),
    );
    expect(queriesOf("GET /projects/{project_id}/work-breakdown")).toEqual([
      { search: "Armoires", kinds: "work_package,deliverable" },
    ]);
    // The order item kept for its work package holds it alone: the list says so.
    expect(rows(page, "Work breakdown").slice(1)).toEqual([
      "Fourniture et montage des armoires Order item",
      "Armoires Work package",
      "1 order item",
    ]);
    expect(text(page)).toContain(
      "The order items and work packages show only what the search and the filter retain.",
    );
  });

  it("names in the note of a work breakdown read partial only what narrows it: the search, or the filter by kind", () => {
    const searched = example("work_breakdown_search") as WorkBreakdown;
    expect(
      text(
        html(
          <WorkBreakdownList
            breakdown={searched}
            project={PROJECT}
            shown={{ query: { sort: undefined, search: "Montage" }, preferences: undefined }}
          />,
        ),
      ),
    ).toContain("The order items and work packages show only what the search retains.");
    const packages = example("work_breakdown_work_packages") as WorkBreakdown;
    expect(
      text(
        html(<WorkBreakdownList breakdown={packages} project={PROJECT} kinds={["work_package"]} />),
      ),
    ).toContain("The order items and work packages show only what the filter by kind retains.");
  });

  it("keeps the grid of a work breakdown a search narrows to nothing, never saying the project has no order item", () => {
    // Read filtered, the server gives the reading no counter: it is partial.
    const filtered = example("work_breakdown_search") as WorkBreakdown;
    const none = html(
      <WorkBreakdownList
        breakdown={{ ...filtered, order_items: [] }}
        project={PROJECT}
        shown={{ query: { sort: undefined, search: "zzz" }, preferences: undefined }}
      />,
    );
    expect(rows(none, "Work breakdown")).toContain("No row matches the request.");
    expect(text(none)).not.toContain("This project has no order item.");
  });

  it("shows the work breakdown by default of a project whose order was not entered: one order item, one work package, no deliverable", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/work-breakdown": "work_breakdown_default",
    };
    const page = html(await SettingsPage(at()));
    expect(rows(page, "Work breakdown").slice(1)).toEqual([
      "Commande Order item",
      "Lot unique Work package",
      "1 order item",
    ]);
  });

  it("shows an order item without a work package alone, and says a work breakdown without an order item empty", () => {
    const fallback = example("work_breakdown_default") as WorkBreakdown;
    const [item] = fallback.order_items;
    const bare = { ...fallback, order_items: item ? [{ ...item, work_packages: [] }] : [] };
    expect(
      rows(html(<WorkBreakdownList breakdown={bare} project={PROJECT} />), "Work breakdown"),
    ).toEqual(["Label Kind", "Commande Order item", "1 order item"]);
    expect(
      text(
        html(<WorkBreakdownList breakdown={{ ...fallback, order_items: [] }} project={PROJECT} />),
      ),
    ).toBe("Work breakdown This project has no order item.");
  });

  it("lists the sub-projects of the project on a grid, each by its ERP code, and whether actual costs are charged to it, searched, sorted and filtered by the server on each column", async () => {
    // Each sub-project of the witness is cited by the reference revision and charged (EP-14/L42l).
    const undeletable =
      "Unmet conditions: subproject cited by no marked revision and no actual cost booked against " +
      "the subproject.";
    const page = html(await SettingsPage(at()));
    expect(paths()["GET /projects/{project_id}/subprojects"]).toBe(
      `/projects/${PROJECT}/subprojects`,
    );
    expect(page).toMatch(/<h2[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Subprojects<\/h2>/);
    expect(rows(page, "Subprojects")).toEqual([
      "ERP code Label Actual costs Modify Delete",
      `SP-CMD Poste de commande Charged Modify Delete ${undeletable}`,
      `SP-ESS Essais et mise en service Charged Modify Delete ${undeletable}`,
      "2 subprojects",
    ]);
    expect(sortable(page, "Subprojects")).toEqual(["ERP code", "Label", "Actual costs"]);
    expect(page).toContain('aria-label="Search in “Subprojects”"');
    expect(text(page)).toContain(
      "Actual costs Every subproject With actual costs charged Without actual costs charged",
    );
  });

  it("lists the contributors of the project on a grid, the project manager told from a contributor in words and by an icon, an account deactivated since said so, searched, sorted and filtered by the server on each column", async () => {
    const page = html(await SettingsPage(at()));
    expect(paths()["GET /projects/{project_id}/contributors"]).toBe(
      `/projects/${PROJECT}/contributors`,
    );
    expect(rows(page, "Contributors")).toEqual([
      "Name Capacity Account",
      "Camille Martin Project manager Active",
      "Alix Moreau Contributor Deactivated",
      "Lucas Petit Contributor Active",
      "Inès Roux Contributor Active",
      "4 contributors",
    ]);
    expect(sortable(page, "Contributors")).toEqual(["Name", "Capacity", "Account"]);
    expect(page).toContain('aria-label="Search in “Contributors”"');
    // The project manager alone bears the icon, beside the words that say it.
    const capacities = [
      ...table(page, "Contributors").matchAll(/<td[^>]*data-column="kind"[^>]*>(.*?)<\/td>/g),
    ].map((match) => match[1] ?? "");
    expect(capacities).toHaveLength(4);
    expect(capacities[0]).toMatch(/<svg[^>]*aria-hidden="true"[^>]*>.*<\/svg>Project manager/);
    expect(capacities.slice(1).every((cell) => !cell.includes("<svg"))).toBe(true);
    expect(text(page)).toContain(
      "Every capacity Project manager Contributor Account state Every account Active accounts Deactivated accounts",
    );
  });

  it("asks the server for the search, the sort and the filters of each list the address names, under the names of the contract", async () => {
    await SettingsPage(
      at({
        subproject_search: "SP-C",
        subproject_sort_by: "has_actual_costs",
        subproject_sort_order: "desc",
        subproject_has_actual_costs: "false",
        contributor_search: "Mar",
        contributor_sort_by: "kind",
        contributor_kinds: "contributor,unknown,project_manager",
        contributor_is_active: "true",
        // The names of the contract alone belong to no grid of this screen.
        search: "ignored",
        kinds: "contributor",
        is_active: "false",
      }),
    );
    expect(queriesOf("GET /projects/{project_id}/subprojects")).toEqual([
      {
        search: "SP-C",
        sort_by: "has_actual_costs",
        sort_order: "desc",
        has_actual_costs: "false",
      },
    ]);
    expect(queriesOf("GET /projects/{project_id}/contributors")).toEqual([
      {
        search: "Mar",
        sort_by: "kind",
        sort_order: "asc",
        kinds: "project_manager,contributor",
        is_active: "true",
      },
    ]);
  });

  it("asks nothing the contract would refuse: a column it does not sort by, a filter that is no boolean", async () => {
    await SettingsPage(
      at({
        subproject_sort_by: "actual_costs",
        subproject_has_actual_costs: "yes",
        contributor_sort_by: "name",
        contributor_is_active: "1",
      }),
    );
    expect(queriesOf("GET /projects/{project_id}/subprojects")).toEqual([{}]);
    expect(queriesOf("GET /projects/{project_id}/contributors")).toEqual([{}]);
  });

  it("keeps the grid of a list a search or a filter narrows to nothing", () => {
    const searched = html(
      <SubprojectList
        subprojects={[]}
        shown={{ query: { sort: undefined, search: "XX" }, preferences: undefined }}
      />,
    );
    expect(rows(searched, "Subprojects")).toContain("No row matches the request.");
    const charged = html(<SubprojectList subprojects={[]} actualCosts={false} />);
    expect(rows(charged, "Subprojects")).toContain("No row matches the request.");
    const filtered = html(<ContributorList contributors={[]} kinds={["project_manager"]} />);
    expect(rows(filtered, "Contributors")).toContain("No row matches the request.");
    const inactive = html(<ContributorList contributors={[]} active={false} />);
    expect(rows(inactive, "Contributors")).toContain("No row matches the request.");
    const named = html(
      <ContributorList
        contributors={[]}
        shown={{ query: { sort: undefined, search: "Zoé" }, preferences: undefined }}
      />,
    );
    expect(rows(named, "Contributors")).toContain("No row matches the request.");
    // Nothing narrows it: the list says it is empty.
    expect(text(html(<ContributorList contributors={[]} />))).toBe(
      "Contributors This project has no contributor.",
    );
  });

  it("offers the commands of the sub-projects and the contributors as the project lists them, and says the fake back keeps nothing [WF-PRJ-0050-A]", async () => {
    const page = html(await SettingsPage(at()));
    expect(text(page)).toContain("Mock-up:");
    expect(buttons(page)).toEqual(
      expect.arrayContaining([
        "Edit the project",
        "New subproject",
        "Modify",
        "Delete",
        "Modify the contributors",
      ]),
    );
    // A sub-project charged with actual costs no longer deletes: its deletion says why. Both are,
    // the tests and commissioning by the invoices of the drawn tasks of its lots (EP-14/L45a).
    expect(page).toMatch(/aria-label="Delete “SP-CMD”" aria-disabled="true"/);
    expect(page).toMatch(/aria-label="Delete “SP-ESS”" aria-disabled="true"/);
    expect(text(page)).toContain(
      "Proposed from the roles of the estimate, to be confirmed: Sacha Lefèvre.",
    );
    // The list shown is whole, with its counter: it is not read twice.
    expect(queriesOf("GET /projects/{project_id}/contributors")).toEqual([{}]);
  });

  it("reads the contributors whole besides a reading filtered, which has no counter to write from", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/contributors": ["contributors_search", "contributors"],
    };
    const page = html(await SettingsPage(at({ contributor_search: "Petit" })));
    expect(queriesOf("GET /projects/{project_id}/contributors")).toEqual([{ search: "Petit" }, {}]);
    expect(rows(page, "Contributors")).toHaveLength(3);
    expect(buttons(page)).toContain("Modify the contributors");
  });

  it("says nothing of the fake back on a terminal project, whose commands it presents unavailable, those of its sub-projects' rows too", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_completed",
      "GET /projects/{project_id}/subprojects": "subprojects_completed",
    };
    const page = html(await SettingsPage(at()));
    expect(text(page)).not.toContain("Mock-up:");
    const every = [...page.matchAll(/<button([^>]*)>(.*?)<\/button>/g)];
    const named = (unavailable: boolean) =>
      every
        .filter(
          ([, attributes = ""]) => attributes.includes('aria-disabled="true"') === unavailable,
        )
        .map(([, , content = ""]) => text(content));
    expect(named(true)).toEqual(
      expect.arrayContaining(["Edit the project", "New subproject", "Modify the contributors"]),
    );
    // Nothing is offered that writes, the commands of the sub-projects' rows neither.
    expect(named(false).filter((name) => /Edit|New|Modify|Delete/.test(name))).toEqual([]);
    for (const code of ["SP-CMD", "SP-ESS"]) {
      for (const command of ["Modify", "Delete"]) {
        expect(page).toContain(`aria-label="${command} “${code}”" aria-disabled="true"`);
      }
    }
    expect(paths()["GET /projects/{project_id}/contributors/suggestions"]).toBeUndefined();
  });

  it("offers no command to a session the project lists none to, and reads nothing it would propose", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_reader" };
    const read = html(await SettingsPage(at()));
    expect(buttons(read).filter((name) => /New|Modify|Delete|Edit/.test(name))).toEqual([]);
    expect(text(read)).not.toContain("Mock-up:");
    expect(paths()["GET /projects/{project_id}/contributors/suggestions"]).toBeUndefined();
  });

  it("offers to modify the project as it lists the command, besides the commands of its lists, saying once that the fake back keeps nothing (EP-02/L44a)", async () => {
    const page = html(await SettingsPage(at()));
    expect(buttons(page)).toContain("Edit the project");
    expect(page.match(/<p role="note"/g)).toHaveLength(1);
    expect(page).toMatch(/<p role="note"[^>]*>.*Mock-up: the simulated service/);
    // The forms are the searches of the work breakdown, the sub-projects and the contributors: the
    // commands open theirs in a dialog.
    expect([...page.matchAll(/<form[^>]*>/g)].map((form) => form[0])).toEqual([
      expect.stringContaining('role="search"'),
      expect.stringContaining('role="search"'),
      expect.stringContaining('role="search"'),
    ]);
  });

  it("offers no modification to a session the project lists none for, nor says the fake back keeps nothing", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_reader" };
    const page = html(await SettingsPage(at()));
    expect(buttons(page).filter((name) => name.includes("Edit"))).toEqual([]);
    expect(page).not.toContain('role="note"');
  });

  it("presents the modification of a terminal project unavailable, naming the condition it lacks [WF-CYC-0100-A]", async () => {
    // Toute modification d'un projet terminal est refusée : la commande le dit d'avance.
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_completed" };
    const page = html(await SettingsPage(at()));
    expect(page).toMatch(
      /<button[^>]*aria-disabled="true"[^>]*>(?:(?!<\/button>).)*Edit the project/,
    );
    expect(text(page)).toContain("Edit the project Unmet condition: project not closed.");
    // Nothing can be written: the screen says nothing of what the fake back keeps.
    expect(page).not.toContain('role="note"');
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

  it("says the next state of a project before it is in progress, its trigger and the conditions it lacks, one by one, without trying anything [WF-CYC-0050-A]", async () => {
    // Pour un projet dans chacun des états Créé et Chiffrage, l'utilisateur consulte le prochain
    // état, son déclencheur et les conditions restantes, sans avoir tenté d'action.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/next-state": "next_state_pricing",
    };
    const pricing = html(await LifecyclePage(at()));
    expect(paths()["GET /projects/{project_id}/next-state"]).toBe(
      `/projects/${PROJECT}/next-state`,
    );
    expect(text(pricing)).toContain(
      "Next state State ahead In progress Trigger Reference revision designated and project code " +
        "filled in Remaining conditions reference revision designated History of states",
    );
    expect(pricing).toMatch(/<ul[^>]*><li>reference revision designated<\/li><\/ul>/);
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_created",
      "GET /projects/{project_id}/next-state": "next_state_created",
    };
    const created = html(await LifecyclePage(at()));
    expect(text(created)).toContain(
      "Next state State ahead Pricing Trigger First revision created Remaining conditions None",
    );
  });

  it("offers no command that leads to pricing or in progress, whichever state the project is in [WF-CYC-0020-A]", async () => {
    // Aucun écran ne propose de commande menant à Chiffrage ou En cours.
    for (const [project, next] of [
      ["project_created", "next_state_created"],
      ["project_pricing", "next_state_pricing"],
      ["project", "next_state"],
    ] as const) {
      server.answers = {
        ...server.answers,
        "GET /projects/{project_id}": project,
        "GET /projects/{project_id}/next-state": next,
      };
      const page = html(await LifecyclePage(at()));
      expect(buttons(page)).toEqual([
        "Complete the project",
        "Declare the project lost",
        "Abandon the project",
      ]);
    }
  });

  it("says a terminal project closed, no state following it, and refuses every exit [WF-CYC-0080-A]", async () => {
    // Aucune transition ne part d'un état terminal : toute tentative de transition depuis Terminé
    // est refusée, chacune des trois sorties présentée indisponible.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_completed",
      "GET /projects/{project_id}/next-state": "next_state_completed",
    };
    const page = html(await LifecyclePage(at()));
    expect(text(page)).toContain("Next state The project is closed: no state follows it.");
    for (const exit of [
      "Complete the project",
      "Declare the project lost",
      "Abandon the project",
    ]) {
      const button = new RegExp(
        `<button[^>]*aria-disabled="true"[^>]*>(?:(?!</button>).)*${exit}</button>`,
      ).exec(page);
      expect(button, exit).not.toBeNull();
    }
  });

  it("says a project in progress awaits no next state: only the exits of its lifecycle remain", async () => {
    const page = html(await LifecyclePage(at()));
    expect(text(page)).toContain(
      "Next state No fact leads the project to another state any more: only the exits of the " +
        "lifecycle remain.",
    );
    expect(text(page)).not.toContain("Trigger");
  });

  it.each([
    ["the history of its states", "GET /projects/{project_id}/state-transitions"],
    ["its next state", "GET /projects/{project_id}/next-state"],
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
