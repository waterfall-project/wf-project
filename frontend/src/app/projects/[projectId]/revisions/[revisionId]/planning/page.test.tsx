// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanningGridProps } from "@/components/grid/planning-grid";
import type { StructureChoiceProps } from "@/components/context/structure-choice";
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
// The choice of the structure is a menu the server renders closed: what it is offered is read here.
const choices = vi.hoisted((): { offered: StructureChoiceProps[] } => ({ offered: [] }));
vi.mock("@/components/context/structure-choice", () => ({
  StructureChoice: (props: StructureChoiceProps) => {
    choices.offered.push(props);
    return null;
  },
}));
// The grid is rendered as it is; its props are read here, to see what the page gives it.
const grid = vi.hoisted((): { given: PlanningGridProps[] } => ({ given: [] }));
vi.mock("@/components/grid/planning-grid", async (original) => {
  const planned = await original<typeof import("@/components/grid/planning-grid")>();
  return {
    ...planned,
    PlanningGrid: (props: PlanningGridProps) => {
      grid.given.push(props);
      return planned.PlanningGrid(props);
    },
  };
});
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
  choices.offered = [];
  grid.given = [];
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_planning",
    [BREAKDOWN]: "work_breakdown",
    "GET /projects/{project_id}/timelines": "timelines",
    "GET /reference/duration-units": "duration_units",
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

  it("reads the timelines of the project, which name the inscriptions of the tasks in a column hidden until it is shown [WF-PLA-0060-A]", async () => {
    // Une tâche inscrite apparaît dans la chronologie : the column and the submenu of the cells are
    // proven on the grid (`choice-menu.dom.test.tsx`).
    const page = await planning();
    const [read] = callsOf("GET /projects/{project_id}/timelines");
    expect(read?.path).toBe(`/projects/${PROJECT}/timelines`);
    expect(page).toMatch(/<th(?:(?!<\/th>).)*>Attached to</);
    expect(page).not.toMatch(/<th(?:(?!<\/th>).)*>Timelines</);
  });

  // aucune exigence : propre à l'US (US-0530, le niveau des heures travaillées et l'export du Gantt).
  it("gives the Gantt the hours of a day of the installation, and the project, the revision and the date of calculation its image names", async () => {
    await planning();
    expect(callsOf("GET /reference/duration-units")).toHaveLength(1);
    expect(grid.given.at(-1)?.gantt).toEqual({
      hoursPerDay: 8,
      exported: {
        provenance: {
          project: "Modernisation du poste de commande",
          code: "PRJ-001",
          revision: "Current revision",
        },
        scheduledAt: "2026-06-03T14:05:00Z",
      },
    });
  });

  it("gives the grid what the project lists of the creation of a timeline, as the server says it [WF-IHM-0090-A]", async () => {
    await planning();
    expect(grid.given.at(-1)?.timelineCreation).toMatchObject({
      command: "manage_timelines",
      is_available: true,
      missing_conditions: [],
    });
    grid.given = [];
    server.clients = [];
    server.answers = { ...server.answers, "GET /projects/{project_id}": "project_reader" };
    await planning();
    expect(grid.given.at(-1)?.timelineCreation).toBeUndefined();
  });

  it("opens without timelines when the API does not find their list, the rest of the screen shown", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/timelines": { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = await planning();
    expect(page).toMatch(/<th(?:(?!<\/th>).)*>Attached to</);
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

  it("asks the server for the subtree of the post the address names, shows it chosen and active in the banner, with a link that lifts it", async () => {
    const page = await planning({ order_item_id: ITEM, search: "Revue" });
    const [read] = callsOf(NODES);
    expect(read?.query.get("order_item_id")).toBe(ITEM);
    expect(read?.query.get("work_package_id")).toBeNull();
    expect(read?.query.get("search")).toBe("Revue");
    expect(page).toContain(`<option value="${ITEM}" selected="">Order item: Poste 1.1</option>`);
    const chips = /<ul aria-label="Active filters"(?:(?!<\/ul>).)*<\/ul>/.exec(page)?.[0] ?? "";
    expect(chips).toContain("Order item: Poste 1.1");
    expect(chips).toContain(`aria-label="Remove the filter “Order item: Poste 1.1”"`);
  });

  it("asks the subtree of the lot the address names, the post it would name besides not read", async () => {
    const page = await planning({ work_package_id: LOT, order_item_id: ITEM });
    const [read] = callsOf(NODES);
    expect(read?.query.get("work_package_id")).toBe(LOT);
    expect(read?.query.get("order_item_id")).toBeNull();
    expect(page).toContain(`<option value="${LOT}" selected="">Work package: Lot 1</option>`);
    // The chip is the lot's alone: it lifts both parameters, the post left in the address taking the
    // place of the lot (`structure-screens.dom.test.tsx`).
    expect(page).toContain('aria-label="Remove the filter “Work package: Lot 1');
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
      expect(chips).toContain(`aria-label="Remove the filter “Order item: ${ITEM}”"`);
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

describe("the structure the planning reads", () => {
  // The structures of the current revision (`structures`): the main one, the amendment 2, a
  // differential not merged, and the own estimate of the risk of the rewiring.
  const MAIN = "01926f3a-7c00-7000-8000-000000000201";
  const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
  const RISK = "01926f3a-7c00-7000-8000-000000000204";
  /** What the banner offered to choose: each run of a kind, by its name and its structures. */
  function offered() {
    const choice = choices.offered.at(-1);
    return {
      chosen: choice?.chosen,
      label: choice?.label,
      groups: choice?.groups.map(({ name, options }) => ({
        name,
        options: options.map(({ structure_id, text }) => [structure_id, text]),
      })),
    };
  }

  it("reads the main structure when the address names none, and offers every structure of the revision in the banner", async () => {
    await planning();
    const [read] = callsOf(NODES);
    expect(read?.path).toContain(`/structures/${MAIN}/nodes`);
    expect(offered()).toEqual({
      chosen: MAIN,
      label: "Change the structure, “Structure principale” read",
      groups: [
        { name: undefined, options: [[MAIN, "Structure principale"]] },
        { name: "Amendment", options: [[AMENDMENT, "Avenant 2 — reprise des essais"]] },
        {
          name: "Risk estimate",
          options: [
            [RISK, "Risque de reprise du câblage"],
            ["01926f3a-7c00-7000-8000-000000000205", "Retard de livraison des armoires (merged)"],
            ["01926f3a-7c00-7000-8000-000000000206", "Indisponibilité de l'automaticien"],
          ],
        },
      ],
    });
  });

  it("reads the differential the address names, which the banner and the head of the grid name [WF-IHM-0020-A]", async () => {
    // Une grille ouverte sur une structure différentielle nomme cette structure.
    const page = await planning({ structure: AMENDMENT });
    const [read] = callsOf(NODES);
    expect(read?.path).toContain(`/structures/${AMENDMENT}/nodes`);
    const banner =
      /<section aria-label="Reading context"(?:(?!<\/section>).)*<\/section>/.exec(page)?.[0] ?? "";
    expect(banner).toContain("<dd>Avenant 2 — reprise des essais</dd>");
    expect(banner).toMatch(/<dd><span[^>]*>Amendment<\/span><\/dd>/);
    expect(offered().chosen).toBe(AMENDMENT);
    expect(page).toContain("Avenant 2 — reprise des essais ·");
  });

  it("offers the contractualisation of the amendment on its grid, as the revision lists it, and on no other structure [WF-REV-0050-A]", async () => {
    const amendment = await planning({ structure: AMENDMENT });
    expect(amendment).toContain("Contractualise the amendment");
    expect(await planning()).not.toContain("Contractualise the amendment");
  });

  it("lists every differential of the revision, two coexisting in it [WF-REV-0100-A]", async () => {
    // Deux structures différentielles coexistent dans une même révision : the reference revision
    // (`structures_amendments`) bears the amendment 1, merged, and the amendment 2, not merged, and
    // the choice of the structure lists both, each to be read.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures_amendments",
    };
    await planning();
    expect(offered().groups).toContainEqual({
      name: "Amendment",
      options: [
        ["01926f3a-7c00-7000-8000-000000000212", "Avenant 1 — extension du poste (merged)"],
        ["01926f3a-7c00-7000-8000-000000000213", "Avenant 2 — reprise des essais"],
      ],
    });
  });

  it("is not found on a structure the revision does not list", async () => {
    // The amendment 2 of the reference revision, not of the current one.
    await expect(
      planning({ structure: "01926f3a-7c00-7000-8000-000000000213" }),
    ).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(callsOf(NODES)).toEqual([]);
  });

  it.each([
    { kind: "a differential", structure: AMENDMENT },
    { kind: "the own estimate of a risk", structure: RISK },
  ])(
    "never offers the skeleton in the empty grid of $kind, where it does on the main structure",
    async ({ structure }) => {
      // A revision that lists the skeleton available (`revision_without_tasks`), read on the
      // structures of the current revision, each empty: the skeleton fills the main one alone.
      server.answers = {
        ...server.answers,
        "GET /projects/{project_id}/revisions/{revision_id}": "revision_without_tasks",
        [NODES]: "nodes_empty",
      };
      expect(await planning()).toMatch(SKELETON);
      server.clients = [];
      expect(await planning({ structure })).not.toMatch(SKELETON);
    },
  );
});
