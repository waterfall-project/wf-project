// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the paths of the degraded mode ask of the platform: a component of the slot stopped for the
 * time of a path, and always started again, whatever the path found (WF-EXP-0040-A, tableau 12).
 *
 * A component is named by the identifier of its container, which `make e2e-service` gives the way
 * it gives that of the database (`E2E_SERVICE_DATABASE`): the paths stop and start these
 * containers, of the slot of the worktree, by their identifier alone — never by a pattern. Stopping
 * one reaches every path that plays beside, which is why the paths that use this are tagged
 * `@platform-wide` and play alone (`playwright.config.ts`).
 */
import { execFileSync } from "node:child_process";

/** The components the paths stop, and the variable of the environment that names each container. */
const CONTAINERS = {
  cache: "E2E_SERVICE_CACHE",
  directory: "E2E_SERVICE_DIRECTORY",
  worker: "E2E_SERVICE_WORKER",
} as const;

/** A component of the platform the paths stop: Redis, the directory of the enterprise, the worker. */
export type Stoppable = keyof typeof CONTAINERS;

/** The identifier of the container of a component, as `make e2e-service` gave it. */
export function container(component: Stoppable): string {
  const name = process.env[CONTAINERS[component]];
  if (name === undefined || name === "") {
    throw new Error(
      `${CONTAINERS[component]} must name the container of the ${component}: run make e2e-service`,
    );
  }
  return name;
}

/**
 * What Docker says of a container: its health, `healthy` once its check passes — or, for one that
 * has no check, as the worker has none, `healthy` once it runs.
 *
 * That says only that the process of the worker runs, not that it takes tasks: the worker exposes
 * no port nor command that tells it is ready, and adding a check to its image is out of the scope
 * of the paths. The paths that need it wait for what the worker does (a marking run), not for it.
 */
function health(id: string): string {
  const format =
    "{{if .State.Health}}{{.State.Health.Status}}{{else if .State.Running}}healthy{{else}}{{.State.Status}}{{end}}";
  return execFileSync("docker", ["inspect", "--format", format, id], {
    encoding: "utf8",
  }).trim();
}

/** The longest `untilHealthy` waits for one container. */
const HEALTHY_WITHIN = 60_000;

/**
 * The time a hook has to start every component again (`startAllAgain`): the wait of each, and a
 * margin for the `docker start` calls, so that it grows with the components and is never short.
 */
export const START_ALL_AGAIN_TIMEOUT = Object.keys(CONTAINERS).length * HEALTHY_WITHIN + 20_000;

/** Wait, up to a minute, for a container whose health check passes. */
async function untilHealthy(id: string): Promise<void> {
  const until = Date.now() + HEALTHY_WITHIN;
  while (health(id) !== "healthy") {
    if (Date.now() > until) {
      throw new Error(`the container ${id} is not healthy a minute after it started`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

/** Start a container again and wait for its health check; nothing to do for one that runs. */
function startAgain(id: string): Promise<void> {
  const running = execFileSync("docker", ["inspect", "--format", "{{.State.Running}}", id], {
    encoding: "utf8",
  }).trim();
  if (running !== "true") {
    execFileSync("docker", ["start", id], { stdio: "ignore" });
  }
  return untilHealthy(id);
}

/**
 * Empty Redis, every database of it, as a restart of it with nothing kept would: the sessions of
 * the front and the queue of the tasks are gone (WF-ARC-0040-A). The password is the one Redis
 * holds for its own `redis-cli` (`REDISCLI_AUTH` of its container), which this never reads.
 */
export function emptyCache(): void {
  const id = container("cache");
  const redis = (...command: string[]): string =>
    execFileSync("docker", ["exec", id, "redis-cli", ...command], { encoding: "utf8" }).trim();
  // `redis-cli` exits 0 on an error reply (`NOAUTH`, `ERR`): the reply is what says it worked.
  const flushed = redis("FLUSHALL");
  if (flushed !== "OK") {
    throw new Error(`FLUSHALL did not empty Redis: ${flushed}`);
  }
}

/**
 * Start every component the paths stop again, whatever the worker that stopped it became: the
 * `finally` of `whileStopped` does not run for a worker killed on a timeout, so the file that
 * stops a component calls this in an `afterAll`, which Playwright runs in a new worker then.
 */
export async function startAllAgain(): Promise<void> {
  for (const component of Object.keys(CONTAINERS) as Stoppable[]) {
    await startAgain(container(component));
  }
}

/**
 * Run a path while a component is stopped, then start it again and wait for it, so that a path
 * that failed leaves the platform whole for the paths after it. A failure of the path stays the
 * error thrown: the one of the restart is said on the console, never in its place.
 */
export async function whileStopped<T>(component: Stoppable, run: () => Promise<T>): Promise<T> {
  const id = container(component);
  execFileSync("docker", ["stop", "--time", "10", id], { stdio: "ignore" });
  let result: T;
  try {
    result = await run();
  } catch (error) {
    try {
      await startAgain(id);
    } catch (restart) {
      console.error(`the container ${id} did not start again after the path failed:`, restart);
    }
    throw error;
  }
  await startAgain(id);
  return result;
}
