// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { BASE_PARAMETER } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { gridAddress, mainStructure, readGridScreen } from "./grid-screen";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

// One client for the whole of a reading, made at its first call.
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

type Comparison = components["schemas"]["RevisionComparison"];

const STRUCTURES = example("structures") as components["schemas"]["CostStructure"][];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
// The current revision of the witness, a copy of the reference; the offer v1.0, marked before it.
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const MAIN = "01926f3a-7c00-7000-8000-000000000201";
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const COMPARISON = "GET /projects/{project_id}/revisions/comparison";

/** What a grid reads in these tests: the finish of a task besides what every grid reads, tasks alone. */
const GRID = {
  key: "planning",
  sortable: ["label"],
  kinds: ["task"],
  fields: { node: [], task: ["finish"], line: [] },
  chooses: true,
} as const;

/** Read the grid of a screen of the current revision at the query given. */
function read(screen: string, search: Record<string, string> = {}) {
  return readGridScreen(
    gridAddress({ projectId: PROJECT, revisionId: CURRENT }, search, screen),
    GRID,
  );
}

/** The calls of a route, as the client received them. */
function callsOf(route: string) {
  return server.clients.flatMap((client) => client.calls).filter((call) => call.route === route);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    [NODES]: "nodes_planning",
    [COMPARISON]: "comparison_current",
  };
});

describe("the main structure of a revision", () => {
  it("is the one the revision lists as main, whatever its place among the others", () => {
    const main = STRUCTURES.find((structure) => structure.kind === "main");
    expect(main).toBeDefined();
    expect(mainStructure([...STRUCTURES].reverse())).toBe(main);
  });

  it("is an unexpected answer when the revision lists none, which the contract rules out", () => {
    const others = STRUCTURES.filter((structure) => structure.kind !== "main");
    expect(() => mainStructure(others)).toThrow(
      expect.objectContaining({ name: "UnexpectedAnswer", operation: "listCostStructures" }),
    );
    expect(() => mainStructure([])).toThrow(expect.objectContaining({ name: "UnexpectedAnswer" }));
  });
});

describe("a grid compared to the base its address names", () => {
  it.each(["planning", "estimate", "remaining"])(
    "reads on the %s the comparison of the revision read to the base, with the same fields, filters and sort, its rows bearing the mark of a differential",
    async (screen) => {
      // La base est portée par l'adresse (US-2330) : la grille lit `compareRevisions` à la place de
      // `listNodes`, avec les mêmes filtres, le même tri, la même recherche et les mêmes champs.
      const grid = await read(screen, {
        [BASE_PARAMETER]: REFERENCE,
        sort_by: "label",
        sort_order: "desc",
        search: "Montage",
      });
      expect(callsOf(NODES)).toHaveLength(0);
      const [compared] = callsOf(COMPARISON);
      const { fields, ...query } = Object.fromEntries(compared?.query ?? []);
      expect(query).toEqual({
        from_revision_id: REFERENCE,
        to_revision_id: CURRENT,
        sort_by: "label",
        sort_order: "desc",
        search: "Montage",
        kinds: "task",
      });
      expect(fields?.split(",")).toContain("task.finish");
      // The rows of the comparison, each with its mark; the tasks alone, as the grid asked them.
      const { items } = example("comparison_current") as Comparison;
      const tasks = items.filter((node) => node.kind === "task");
      expect(grid.nodes.items.map((row) => [row.node_id, row.difference])).toEqual(
        tasks.map((node) => [node.node_id, node.difference]),
      );
      expect(grid.nodes.items.some((row) => row.difference !== "unchanged")).toBe(true);
    },
  );

  it("offers no comparison on a grid opened on a differential structure, whatever its address names [WF-IHM-0150-A]", async () => {
    // Une grille ouverte sur une structure différentielle n'offre pas la comparaison : éprouvé contre
    // le faux back, qui seul sert un différentiel avant EP-08.
    const amendment = await read("estimate", { [BASE_PARAMETER]: REFERENCE, structure: AMENDMENT });
    expect(amendment.kind).toBe("amendment");
    expect(amendment.base).toBeUndefined();
    expect(callsOf(COMPARISON)).toHaveLength(0);
    expect(amendment.nodes.items.every((row) => row.base === undefined)).toBe(true);
  });

  it("reads the structure itself without a base, and on a structure other than the main one", async () => {
    // Sur une autre structure que la principale, le bandeau n'offre pas de base (US-2330).
    await read("planning");
    const amendment = await read("planning", { [BASE_PARAMETER]: REFERENCE, structure: AMENDMENT });
    expect(callsOf(COMPARISON)).toHaveLength(0);
    expect(callsOf(NODES).map((call) => call.path)).toEqual([
      expect.stringContaining(`/structures/${MAIN}/nodes`),
      expect.stringContaining(`/structures/${AMENDMENT}/nodes`),
    ]);
    expect(amendment.base).toBeUndefined();
  });

  it("offers for base the marked revisions but the one read: the one it is a copy of, then the reference, then the others", async () => {
    // Le bandeau offre pour base les révisions marquées du projet, hors la révision lue (US-2330,
    // #3176) : celle dont la révision lue est issue, puis la référence, puis les autres.
    const grid = await read("estimate", { [BASE_PARAMETER]: OFFER });
    expect(grid.base?.chosen).toBe(OFFER);
    expect(grid.base?.offered.map((revision) => revision.revision_id)).toEqual([REFERENCE, OFFER]);
    const uncompared = await read("remaining");
    expect(uncompared.base).toEqual({ chosen: undefined, offered: grid.base?.offered });
  });

  it("offers no base on a grid that compares nothing, and compares nothing there", async () => {
    // US-2330 : « la base est portée par l'adresse, et par les liens entre ces trois grilles
    // seulement ; les autres écrans ne la portent pas, et elle n'est gardée ni dans les préférences
    // du compte ni avec le dernier contexte du projet : une grille ouverte sans elle ne compare
    // rien ».
    const grid = await read("task-tree", { [BASE_PARAMETER]: REFERENCE });
    expect(grid.base).toBeUndefined();
    expect(callsOf(COMPARISON)).toHaveLength(0);
  });

  it("says a base under way as any refusal of a read, never a grid half read", async () => {
    // Une base que l'adresse nomme et qui n'est pas une révision marquée du projet est dite par
    // l'écran comme tout refus de lecture, sans grille à moitié lue (US-2330).
    server.answers = {
      ...server.answers,
      [COMPARISON]: {
        problem: example("comparison_revision_draft") as Problem & { status: 409 },
      },
    };
    await expect(read("planning", { [BASE_PARAMETER]: CURRENT })).rejects.toMatchObject({
      name: "UnexpectedAnswer",
      operation: "compareRevisions",
      status: 409,
    });
  });

  it("is not found for a base that is no revision of the project", async () => {
    server.answers = {
      ...server.answers,
      [COMPARISON]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(read("estimate", { [BASE_PARAMETER]: AMENDMENT })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});

describe("a grid filtered by a risk occurred", () => {
  const RISKS = "GET /projects/{project_id}/risks";
  const STRUCTURES_ROUTE = "GET /projects/{project_id}/revisions/{revision_id}/structures";
  const OCCURRED = "01926f3a-7c00-7000-8000-000000000751";

  it("handles the rejection of the risks read when the structures fail first, never leaving the retained origin unhandled [US-2640] [#1972]", async () => {
    const unhandled = vi.fn();
    process.on("unhandledRejection", unhandled);
    server.answers = {
      ...server.answers,
      [STRUCTURES_ROUTE]: { problem: { code: "INTERNAL_ERROR", status: 500 } },
      [RISKS]: { problem: { code: "INTERNAL_ERROR", status: 500 } },
    };
    try {
      await expect(
        readGridScreen(
          gridAddress(
            { projectId: PROJECT, revisionId: CURRENT },
            { origin_risk_ids: OCCURRED },
            "planning",
          ),
          { ...GRID, byOrigin: true },
        ),
      ).rejects.toMatchObject({ name: "UnexpectedAnswer" });
      // Node reports an unhandled rejection once the microtasks of the turn are drained: a macrotask
      // queued now runs after that report, with no delay to guess.
      await new Promise((resolve) => setImmediate(resolve));
      expect(unhandled).not.toHaveBeenCalled();
    } finally {
      process.off("unhandledRejection", unhandled);
    }
  });
});
