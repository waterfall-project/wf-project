// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An estimate the account of the run writes in the service, for the paths of the grid of the
 * estimate that play against it (US-1560): the witness holds no line before US-1570, and the account
 * of the run is no project manager of PRJ-001 (#2193), so each path writes a project of its own, as
 * a user does — the project made from the home, its revision opened — and its first nodes by the
 * API, under the token of its creator. The nodes are always the same, in the order of the plan:
 *
 *   1 Phase (summary)    2 Tâche du devis    and under it a line of the category « Matériel
 *   électrique », with a quantity of 1 and a unit disbursement of 1 000,00
 *
 * A path asks for more by the options: the inflation of the project, and a task dated two years
 * after the year of reference of the revision (`dated`).
 */
import {
  type APIRequestContext,
  type Browser,
  expect,
  type Locator,
  type Page,
} from "@playwright/test";

import type { components } from "../src/api/generated/schema";
import { WORKING } from "./hydration";
import { createOwnProject, openRevision, type OwnProject } from "./own-project";
import { API, frontToken, type LocalPerson } from "./service/realm";

/** The labels of the nodes seeded. */
export const PHASE = "Phase";
export const TASK = "Tâche du devis";

/** The category of the line seeded, a category of the reference the witness loads. */
export const CATEGORY = "Matériel électrique";

/** What a path keeps of the estimate it seeded. */
export interface SeededEstimate {
  readonly own: OwnProject;
  /** The address of the revision in progress, under which the screens are. */
  readonly revision: string;
  /** The address of its estimate, and of its planning. */
  readonly estimate: string;
  readonly planning: string;
  /** The identifiers of the project, of the revision and of the main structure. */
  readonly ids: { readonly project: string; readonly revision: string; readonly structure: string };
  /** The identifiers of the nodes seeded: the phase, the task, its first line. */
  readonly nodes: { readonly phase: string; readonly task: string; readonly line: string };
  /** The year of reference of the revision. */
  readonly referenceYear: number;
  /** The headers of the creator of the project, to write by the API as she does. */
  readonly headers: { readonly Authorization: string };
}

/** What a path asks of the estimate beyond its nodes. */
export interface EstimateOptions {
  /** The annual inflation rate of the project, a ratio (`"0.02"`), set before its revision opens. */
  readonly inflation?: string;
  /** Date the task two years after the year of reference of the revision, a manual task. */
  readonly dated?: boolean;
  /** The unit disbursements of the lines of the task, one line each (`["1000.00"]` by default). */
  readonly lines?: readonly string[];
}

type Schemas = components["schemas"];

type Headers = Readonly<Record<string, string>>;

/** The first Monday of March of a year, as a calendar date: a working day for any calendar. */
function mondayOfMarch(year: number): string {
  const first = new Date(Date.UTC(year, 2, 1));
  const shift = (8 - first.getUTCDay()) % 7;
  return new Date(Date.UTC(year, 2, 1 + shift)).toISOString().slice(0, 10);
}

/** The date four days after a Monday: its Friday. */
function fridayAfter(monday: string): string {
  const date = new Date(`${monday}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 4);
  return date.toISOString().slice(0, 10);
}

/** The identifier of the category of the reference that bears a label, read page by page. */
async function categoryOf(
  calls: APIRequestContext,
  headers: Headers,
  label: string,
): Promise<string> {
  for (let offset = 0; ; offset += 50) {
    const read = await calls.get(
      `${API}/reference/cost-categories?limit=50&offset=${String(offset)}`,
      {
        headers,
      },
    );
    expect(read.status(), "GET cost-categories").toBe(200);
    const items = ((await read.json()) as { items: Schemas["CostCategory"][] }).items;
    const found = items.find((item) => item.label === label);
    if (found !== undefined) {
      return found.cost_category_id;
    }
    if (items.length === 0) {
      throw new Error(`no cost category labelled ${label} in the reference`);
    }
  }
}

/** Create a node of the structure at `base`, and name it. */
async function createNode(
  calls: APIRequestContext,
  headers: Headers,
  base: string,
  data: Readonly<Record<string, unknown>>,
): Promise<string> {
  const created = await calls.post(`${base}/nodes`, { headers, data });
  expect(created.status(), "POST nodes").toBe(201);
  const node = ((await created.json()) as Schemas["NodesWritten"]).nodes[0];
  if (node === undefined) {
    throw new Error("a node created is answered");
  }
  return node.node_id;
}

/** The counter of a node as the service holds it now. */
async function lockOf(
  calls: APIRequestContext,
  headers: Headers,
  base: string,
  node: string,
): Promise<number> {
  const read = await calls.get(`${base}/nodes`, { headers });
  expect(read.status(), "GET nodes").toBe(200);
  const found = ((await read.json()) as { items: Schemas["Node"][] }).items.find(
    (item) => item.node_id === node,
  );
  if (found === undefined) {
    throw new Error("a node seeded is read");
  }
  return found.lock_version;
}

/**
 * Create a project from the home, give it its inflation, open its revision, and write a summary
 * task, a task under it and a line of the task, under the token of its creator.
 */
export async function seedEstimate(
  page: Page,
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson | undefined,
  prefix: string,
  options: EstimateOptions = {},
): Promise<SeededEstimate> {
  if (creator === undefined) {
    throw new Error("the manager of the worker is made against the service");
  }
  const own = await createOwnProject(page, prefix);
  const project = own.path.split("/").at(-1) ?? "";
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  if (options.inflation !== undefined) {
    // Before the revision opens: it keeps the inflation rate of the project it is opened on.
    const read = await calls.get(`${API}/projects/${project}`, { headers });
    expect(read.status(), "GET project").toBe(200);
    const { lock_version } = (await read.json()) as Schemas["Project"];
    const updated = await calls.patch(`${API}/projects/${project}`, {
      headers,
      data: { inflation_rate: options.inflation, lock_version },
    });
    expect(updated.status(), "PATCH project").toBe(200);
  }
  await openRevision(page, own);
  // The address of the revision opened names it by `revision_id`, on the screen of the revisions.
  const opened = new URL(page.url()).searchParams.get("revision_id");
  if (opened === null) {
    throw new Error("the revision opened is not named by its address");
  }
  const revision = `${own.path}/revisions/${opened}`;
  const at = `${API}/projects/${project}/revisions/${opened}`;
  const structures = await calls.get(`${at}/structures`, { headers });
  expect(structures.status(), "GET structures").toBe(200);
  const main = ((await structures.json()) as Schemas["CostStructure"][]).find(
    ({ kind }) => kind === "main",
  );
  if (main === undefined) {
    throw new Error("a revision opened has a main structure");
  }
  const base = `${at}/structures/${main.structure_id}`;
  const read = await calls.get(at, { headers });
  expect(read.status(), "GET revision").toBe(200);
  const { reference_year } = (await read.json()) as Schemas["Revision"];

  const phase = await createNode(calls, headers, base, {
    kind: "task",
    parent_id: null,
    task: { label: PHASE, duration: { value: "5", unit: "d" } },
  });
  const task = await createNode(calls, headers, base, {
    kind: "task",
    parent_id: phase,
    task: { label: TASK, duration: { value: "5", unit: "d" } },
  });
  if (options.dated === true) {
    const monday = mondayOfMarch(reference_year + 2);
    const dated = await calls.patch(`${base}/nodes/${task}/task`, {
      headers,
      data: {
        scheduling_mode: "manual",
        start: { date: monday },
        finish: { date: fridayAfter(monday) },
        lock_version: await lockOf(calls, headers, base, task),
      },
    });
    expect(dated.status(), "PATCH task dated").toBe(200);
  }
  const category = await categoryOf(calls, headers, CATEGORY);
  let line = "";
  for (const disbursement of options.lines ?? ["1000.00"]) {
    const created = await createNode(calls, headers, base, {
      kind: "estimate_line",
      parent_id: task,
      estimate_line: { cost_category_id: category, quantity: "1", unit_disbursement: disbursement },
    });
    line = line === "" ? created : line;
  }
  return {
    own,
    revision,
    estimate: `${revision}/estimate`,
    planning: `${revision}/planning`,
    ids: { project, revision: opened, structure: main.structure_id },
    nodes: { phase, task, line },
    referenceYear: reference_year,
    headers,
  };
}

/** The grid is idle: the command that follows is not held by a write under way. */
export function idle(grid: Locator): Promise<void> {
  return expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
}
