// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The load of fifty users under which the report of a version is taken (US-2300): its preparation,
 * outside the measure, then k6 started and stopped in its service of the service platform (`load`,
 * `deploy/compose/compose.service.yaml`), which plays `bench/load.ts`.
 *
 * The preparation gives each user of the load its tokens, asked of the identity provider by the
 * code flow of the front (`frontTokens`) — the sign-in is never in the load —, and a task of the
 * planning of its own to write: a task in automatic mode, not started, neither a summary nor a
 * milestone, chosen evenly over the second half of the planning, away from the task the browser of
 * the measure writes, which `targets` finds from the twentieth row on. It writes them, with where the
 * load reads and the seed of its draw, in the file the service mounts (`frontend/.e2e/load/`, ignored
 * by git, readable by its owner alone: it holds tokens), which the measure deletes once the load is
 * stopped.
 *
 * k6 runs in a container of its own, named after the platform of the slot, which the measure stops:
 * k6 ends its users and writes its summary beside the file (`summary.json`), which the report of the
 * version carries.
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import type { Browser } from "@playwright/test";

import type { Place } from "../../bench/screens";
import type { components, operations } from "../../src/api/generated/schema";
import { frontTokens, type Person } from "../service/realm";
import type { Caller } from "./background";

type Schemas = components["schemas"];
type NodeList = operations["listNodes"]["responses"][200]["content"]["application/json"];

/** The directory the service of the load mounts, from the root of the front. */
const DIRECTORY = join(import.meta.dirname, "..", "..", ".e2e", "load");
const FILE = join(DIRECTORY, "load.json");
const SUMMARY = join(DIRECTORY, "summary.json");
const COMPOSE = join(
  import.meta.dirname,
  "..",
  "..",
  "..",
  "deploy",
  "compose",
  "compose.service.yaml",
);

/** The seed of the draw of the load (`bench/draw.ts`): the same gestures, run after run. */
export const SEED = 2300;

/** A task a user of the load writes. */
interface LoadTask {
  readonly node: string;
  readonly label: string;
  readonly lock_version: number;
}

/** The fields of the nodes the choice of the tasks reads. */
const CHOSEN_BY = [
  "node_id",
  "lock_version",
  "task.label",
  "task.is_summary",
  "task.is_milestone",
  "task.scheduling_mode",
  "task.progress",
  "task.work_package_id",
];

/**
 * Where the load reads, and the tasks its users write, one each: read on the main structure of the
 * revision, as the first user of the measure, outside the measure.
 */
export async function placeAndTasks(
  api: Caller,
  project: string,
  revision: string,
  count: number,
): Promise<{ place: Place; tasks: LoadTask[] }> {
  const structures = await api.get<Schemas["CostStructure"][]>(
    `/projects/${project}/revisions/${revision}/structures`,
  );
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    throw new Error("the revision of PRJ-001 has no main structure");
  }
  const fields = CHOSEN_BY.map((field) => `fields=${field}`).join("&");
  const { items } = await api.get<NodeList>(
    `/projects/${project}/revisions/${revision}/structures/${main.structure_id}/nodes?kinds=task&${fields}`,
  );
  const workPackage = items.find((node) => node.task?.work_package_id != null)?.task
    ?.work_package_id;
  const writable = items
    .slice(Math.floor(items.length / 2))
    .filter(
      ({ task }) =>
        task?.is_summary === false &&
        task.is_milestone === false &&
        task.scheduling_mode === "automatic" &&
        task.progress === "not_started",
    );
  if (workPackage == null || writable.length < count) {
    throw new Error(
      `PRJ-001 has ${String(writable.length)} tasks to write in the second half of its planning, ${String(count)} wanted, and a lot: the witness is not loaded`,
    );
  }
  const step = Math.floor(writable.length / count);
  const tasks = Array.from({ length: count }, (_, index) => {
    const node = writable[index * step];
    return {
      node: node?.node_id ?? "",
      label: node?.task?.label ?? "",
      lock_version: node?.lock_version ?? 0,
    };
  });
  return {
    place: { project, revision, structure: main.structure_id, workPackage },
    tasks,
  };
}

/** Write the file of the load: each user its tokens and its task, where to read, the seed. */
export async function prepareLoad(
  browser: Browser,
  users: readonly Person[],
  place: Place,
  tasks: readonly LoadTask[],
): Promise<void> {
  const prepared = [];
  for (const [index, user] of users.entries()) {
    const asked = Date.now();
    const tokens = await frontTokens(browser, user);
    prepared.push({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      expires_at: asked + tokens.expires_in * 1000,
      task: tasks[index],
    });
  }
  mkdirSync(DIRECTORY, { recursive: true });
  rmSync(SUMMARY, { force: true });
  writeFileSync(FILE, JSON.stringify({ seed: SEED, place, users: prepared }), { mode: 0o600 });
}

/** The container of the load, named after the platform of the slot. */
function container(): string {
  const project = process.env.WATERFALL_SERVICE_PROJECT;
  if (project === undefined || project === "") {
    throw new Error(
      "WATERFALL_SERVICE_PROJECT names the service platform: run make measure-version",
    );
  }
  return `${project}-load`;
}

/** Run docker, failing on a refusal with what it said. */
function docker(arguments_: readonly string[]): string {
  const run = spawnSync("docker", arguments_, { encoding: "utf8" });
  if (run.status !== 0) {
    throw new Error(`docker ${arguments_.join(" ")} failed: ${run.stderr}`);
  }
  return run.stdout;
}

/** Start the load: k6 in its container, on the platform of the slot, the file prepared. */
export function startLoad(): void {
  const project = process.env.WATERFALL_SERVICE_PROJECT ?? "";
  docker([
    "compose",
    "--file",
    COMPOSE,
    "--project-name",
    project,
    "--profile",
    "load",
    "run",
    "--detach",
    "--rm",
    "--no-deps",
    "--name",
    container(),
    "load",
  ]);
}

/** What k6 says of the load once stopped (`handleSummary` of `bench/load.ts`). */
export type LoadSummary = Readonly<Record<string, number>>;

/**
 * Stop the load, give k6 the time to end its users and write its summary, and delete the file of
 * the tokens; the summary, or none if k6 wrote none.
 */
export function stopLoad(): LoadSummary | undefined {
  try {
    docker(["stop", "--time", "60", container()]);
    return JSON.parse(readFileSync(SUMMARY, "utf8")) as LoadSummary;
  } catch (error) {
    console.log(`The load: ${error instanceof Error ? error.message : String(error)}`);
    return undefined;
  } finally {
    rmSync(FILE, { force: true });
  }
}
