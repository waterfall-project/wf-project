// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A planning the account of the run writes in the service, for the paths of the grid and of the
 * Gantt that play against it (US-1470): the witness holds no task in the service before its filler
 * (US-1480), and the account of the run is no contributor of PRJ-001 (#2193), so each path writes a
 * project of its own, as a user does — the project made from the home, its revision opened — and its
 * first tasks by the API, under the token of its creator. The same tasks every time, in the order of
 * the plan:
 *
 *   1 Études (summary)            2 Études de détail   3 Revue de conception   4 Réception des études
 *   5 Installation sur site       6 Mise en service
 *
 * A path asks for more by `extras`: the links of the plan and a task in conflict (`links`), a work
 * breakdown with two order items (`breakdown`) — each by the operations of the service, under the
 * token of the creator. The states of the tasks cannot be seeded: `setTaskProgress` needs a project in
 * progress (`project_in_progress`), which a project reaches by designating a reference revision that
 * bears tasks and lines (WF-CYC-0030), and no question about the lines is registered before EP-07
 * (`revision_has_tasks_and_lines`).
 */
import { type APIRequestContext, type Browser, expect, type Page } from "@playwright/test";

import { createOwnProject, openRevision, type OwnProject } from "./own-project";
import { API, frontToken, type LocalPerson } from "./service/realm";

/** The labels of the planning seeded, by row number. */
export const SEEDED = {
  1: "Études",
  2: "Études de détail",
  3: "Revue de conception",
  4: "Réception des études",
  5: "Installation sur site",
  6: "Mise en service",
} as const;

/** What a path keeps of the planning it seeded. */
export interface Seeded {
  readonly own: OwnProject;
  /** The address of the revision in progress, under which the screens are. */
  readonly revision: string;
  /** The address of its planning. */
  readonly planning: string;
  /** The identifiers of the project, of the revision and of the main structure. */
  readonly ids: { readonly project: string; readonly revision: string; readonly structure: string };
  /** The identifier of each task, by row number. */
  readonly nodes: Readonly<Record<number, string>>;
  /** The headers of the creator of the project, to write by the API as she does. */
  readonly headers: { readonly Authorization: string };
  /** The order items of the work breakdown written (`breakdown`), by their label. */
  readonly orderItems: Readonly<Record<string, string>>;
}

/** What a path asks of the planning beyond its six tasks. */
export interface Extras {
  /**
   * The links of the plan — 3 follows 2, 4 follows 3, 5 follows 4, all finish to start — and a 7th
   * task, « Livraison anticipée », made manual with dates before the finish of 5, which it follows:
   * a link in conflict.
   */
  readonly links?: boolean;
  /** A work package « Lot A » with the order items « Poste A1 » and « Poste A2 ». */
  readonly breakdown?: boolean;
}

/** The label of the 7th task, in conflict with its predecessor (`Extras.links`). */
export const EARLY = "Livraison anticipée";

/** The labels of the work breakdown written (`Extras.breakdown`). */
export const WORK_PACKAGE = "Lot A";
export const ORDER_ITEMS = ["Poste A1", "Poste A2"] as const;

interface Created {
  nodes: { node_id: string }[];
}

/** The tasks, each by its place: the row of its parent (0, none), and its duration in days. */
const TASKS: readonly (readonly [parent: number, label: string, days: string])[] = [
  [0, SEEDED[1], "1"],
  [1, SEEDED[2], "5"],
  [1, SEEDED[3], "3"],
  [1, SEEDED[4], "0"],
  [0, SEEDED[5], "10"],
  [0, SEEDED[6], "2"],
];

type Headers = Readonly<Record<string, string>>;

/** Put the links of the plan, and the manual task in conflict, in the structure at `base`. */
async function seedLinks(
  calls: APIRequestContext,
  headers: Headers,
  base: string,
  nodes: Record<number, string>,
): Promise<void> {
  /** The lock version of a node as the service holds it now. */
  const lockOf = async (node: string): Promise<number> => {
    const read = await calls.get(`${base}/nodes`, { headers });
    expect(read.status(), "GET nodes").toBe(200);
    const found = (
      (await read.json()) as { items: { node_id: string; lock_version: number }[] }
    ).items.find((item) => item.node_id === node);
    if (found === undefined) {
      throw new Error("a node seeded is read");
    }
    return found.lock_version;
  };
  for (const [row, predecessor] of [
    [3, 2],
    [4, 3],
    [5, 4],
  ] as const) {
    const node = nodes[row] ?? "";
    const linked = await calls.put(`${base}/nodes/${node}/predecessors`, {
      headers,
      data: {
        predecessors: [
          {
            predecessor_node_id: nodes[predecessor] ?? "",
            link_type: "finish_to_start",
            lag: { value: "0", unit: "d" },
          },
        ],
        lock_version: await lockOf(node),
      },
    });
    expect(linked.status(), `PUT predecessors of ${String(row)}`).toBe(200);
  }
  const early = await calls.post(`${base}/nodes`, {
    headers,
    data: {
      kind: "task",
      parent_id: null,
      task: { label: EARLY, duration: { value: "2", unit: "d" } },
    },
  });
  expect(early.status(), "POST nodes early").toBe(201);
  const created = ((await early.json()) as Created).nodes[0]?.node_id ?? "";
  nodes[7] = created;
  const linked = await calls.put(`${base}/nodes/${created}/predecessors`, {
    headers,
    data: {
      predecessors: [
        {
          predecessor_node_id: nodes[5] ?? "",
          link_type: "finish_to_start",
          lag: { value: "0", unit: "d" },
        },
      ],
      lock_version: await lockOf(created),
    },
  });
  expect(linked.status(), "PUT predecessors of 7").toBe(200);
  // Manual, its dates entered a Monday to a Friday long before the finish of its predecessor.
  const manual = await calls.patch(`${base}/nodes/${created}/task`, {
    headers,
    data: {
      scheduling_mode: "manual",
      start: { date: "2020-01-06" },
      finish: { date: "2020-01-10" },
      lock_version: await lockOf(created),
    },
  });
  expect(manual.status(), "PATCH task 7 manual").toBe(200);
}

/** Write the work breakdown of the project, and name its order items by their label. */
async function seedBreakdown(
  calls: APIRequestContext,
  headers: Headers,
  project: string,
): Promise<Record<string, string>> {
  const orderItems: Record<string, string> = {};
  const url = `${API}/projects/${project}/work-breakdown`;
  const read = await calls.get(url, { headers });
  expect(read.status(), "GET work-breakdown").toBe(200);
  const { lock_version } = (await read.json()) as { lock_version: number };
  const written = await calls.put(url, {
    headers,
    data: {
      work_packages: [
        {
          label: WORK_PACKAGE,
          order_items: ORDER_ITEMS.map((label) => ({ label, deliverables: [] })),
        },
      ],
      lock_version,
    },
  });
  expect(written.status(), "PUT work-breakdown").toBe(200);
  const body = (await written.json()) as {
    work_packages: { order_items: { order_item_id: string; label: string }[] }[];
  };
  for (const item of body.work_packages.flatMap((lot) => lot.order_items)) {
    orderItems[item.label] = item.order_item_id;
  }
  return orderItems;
}

/**
 * Create a project from the home, open its revision, and write the six tasks of the planning under
 * the token of its creator. The sequence of the tasks is the order of the plan: each is created after
 * the last of its siblings.
 */
export async function seedPlanning(
  page: Page,
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson | undefined,
  prefix: string,
  extras: Extras = {},
): Promise<Seeded> {
  if (creator === undefined) {
    throw new Error("the manager of the worker is made against the service");
  }
  const own = await createOwnProject(page, prefix);
  await openRevision(page, own);
  // The address of the revision opened names it by `revision_id`, on the screen of the revisions.
  const opened = new URL(page.url()).searchParams.get("revision_id");
  if (opened === null) {
    throw new Error("the revision opened is not named by its address");
  }
  const revision = `${own.path}/revisions/${opened}`;
  const ids = {
    project: own.path.split("/").at(-1) ?? "",
    revision: revision.split("/").at(-1) ?? "",
    structure: "",
  };
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  const structures = await calls.get(
    `${API}/projects/${ids.project}/revisions/${ids.revision}/structures`,
    { headers },
  );
  expect(structures.status(), "GET structures").toBe(200);
  const main = ((await structures.json()) as { structure_id: string; kind: string }[]).find(
    ({ kind }) => kind === "main",
  );
  if (main === undefined) {
    throw new Error("a revision opened has a main structure");
  }
  const structure = main.structure_id;
  const nodes: Record<number, string> = {};
  let row = 0;
  // The summary comes before its subordinates in the plan, which the order of TASKS keeps; a task
  // created under a leaf makes it a summary, so the order of the rows is that of the plan.
  for (const [parent, label, days] of TASKS) {
    row += 1;
    const created = await calls.post(
      `${API}/projects/${ids.project}/revisions/${ids.revision}/structures/${structure}/nodes`,
      {
        headers,
        data: {
          kind: "task",
          parent_id: parent === 0 ? null : (nodes[parent] ?? null),
          task: { label, duration: { value: days, unit: "d" } },
        },
      },
    );
    expect(created.status(), `POST nodes ${label}`).toBe(201);
    const body = (await created.json()) as Created;
    const node = body.nodes[0];
    if (node === undefined) {
      throw new Error("a node created is answered");
    }
    nodes[row] = node.node_id;
  }
  const base = `${API}/projects/${ids.project}/revisions/${ids.revision}/structures/${structure}`;
  if (extras.links === true) {
    await seedLinks(calls, headers, base, nodes);
  }
  const orderItems =
    extras.breakdown === true ? await seedBreakdown(calls, headers, ids.project) : {};
  return {
    own,
    revision,
    planning: `${revision}/planning`,
    ids: { ...ids, structure },
    nodes,
    headers,
    orderItems,
  };
}
