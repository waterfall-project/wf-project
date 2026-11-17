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
import {
  type LoadSummary,
  logText,
  type Refusal,
  refusalsOf,
  type Volumes,
  volumeFailures,
} from "./load-check";

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
  "kind",
  "lock_version",
  "task.label",
  "task.is_summary",
  "task.is_milestone",
  "task.scheduling_mode",
  "task.progress",
  "task.work_package_id",
];

/**
 * Where the load reads, the tasks its users write, one each, and the volumes of the revision: read
 * on the main structure of the revision, as the first user of the measure, outside the measure.
 * The data must be those of §4.6.2 (`volumeFailures`): a thousand tasks, five lines each.
 */
export async function placeAndTasks(
  api: Caller,
  project: string,
  revision: string,
  count: number,
): Promise<{ place: Place; tasks: LoadTask[]; volumes: Volumes }> {
  const structures = await api.get<Schemas["CostStructure"][]>(
    `/projects/${project}/revisions/${revision}/structures`,
  );
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    throw new Error("the revision of PRJ-001 has no main structure");
  }
  const fields = `fields=${CHOSEN_BY.join(",")}`;
  const { items: nodes } = await api.get<NodeList>(
    `/projects/${project}/revisions/${revision}/structures/${main.structure_id}/nodes?${fields}`,
  );
  const items = nodes.filter((node) => node.kind === "task");
  const volumes = { tasks: items.length, estimate_lines: nodes.length - items.length };
  const volumeRefused = volumeFailures(volumes);
  if (volumeRefused.length > 0) {
    throw new Error(
      `PRJ-001 does not have the volumes of §4.6.2 (${volumeRefused.join("; ")}): the witness is not loaded`,
    );
  }
  const workPackage = items.find((node) => node.task?.work_package_id != null)?.task
    ?.work_package_id;
  const writable = items
    .slice(Math.floor(items.length / 2))
    // A projection leaves out a flag that is false: a task neither summary nor milestone has none.
    .filter(
      ({ task }) =>
        task?.scheduling_mode === "automatic" &&
        task.progress === "not_started" &&
        task.is_summary !== true &&
        task.is_milestone !== true,
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
    volumes,
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

/** The container of the load, as `make measure-version` names it (it stops it too). */
function container(): string {
  const name = process.env.WATERFALL_LOAD_CONTAINER;
  if (name === undefined || name === "") {
    throw new Error("WATERFALL_LOAD_CONTAINER names the load: run make measure-version");
  }
  return name;
}

/** Run docker, failing on a refusal with what it said. */
function docker(arguments_: readonly string[]): string {
  const run = spawnSync("docker", arguments_, { encoding: "utf8" });
  if (run.status !== 0) {
    throw new Error(`docker ${arguments_.join(" ")} failed: ${run.stderr}`);
  }
  return run.stdout;
}

/** What the log of the load says; what keeps it from being read is said, not fatal. */
function logOf(name: string): string {
  const run = spawnSync("docker", ["logs", name], {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
  });
  if (run.error !== undefined || run.status !== 0) {
    const why = run.error?.message ?? `docker logs exited ${String(run.status)}: ${run.stderr}`;
    console.log(`The load: log unreadable: ${why}`);
  }
  return logText(run);
}

/** The load once stopped: its summary, if it wrote one, and the refusals its log names. */
export interface StoppedLoad {
  readonly summary: LoadSummary | undefined;
  readonly refusals: readonly Refusal[];
}

/** Start the load: k6 in its container, on the platform of the slot, the file prepared. */
export function startLoad(): void {
  const project = process.env.WATERFALL_SERVICE_PROJECT ?? "";
  const name = container();
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
    name,
    "load",
  ]);
}

/**
 * Stop the load, give k6 the time to end its users and write its summary, and delete the file of
 * the tokens; the summary, or none if k6 wrote none.
 */
export function stopLoad(): StoppedLoad {
  let refusals: Refusal[] = [];
  try {
    // The container is removed once stopped (`--rm`): its log is read before, what it refuses
    // during the seconds of its stop is lost to it, which the summary still counts.
    refusals = refusalsOf(logOf(container()));
    for (const refusal of refusals) {
      console.log(`The load refused ${refusal.kind} ${refusal.name}: ${String(refusal.status)}`);
    }
    docker(["stop", "--time", "60", container()]);
    return { summary: JSON.parse(readFileSync(SUMMARY, "utf8")) as LoadSummary, refusals };
  } catch (error) {
    console.log(`The load: ${error instanceof Error ? error.message : String(error)}`);
    return { summary: undefined, refusals };
  } finally {
    rmSync(FILE, { force: true });
  }
}
