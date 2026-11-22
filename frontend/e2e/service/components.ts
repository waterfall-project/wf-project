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
} as const;

/** A component of the platform the paths stop: Redis, the directory of the enterprise. */
export type Stoppable = keyof typeof CONTAINERS;

/** The identifier of the container of a component, as `make e2e-service` gave it. */
function container(component: Stoppable): string {
  const name = process.env[CONTAINERS[component]];
  if (name === undefined || name === "") {
    throw new Error(
      `${CONTAINERS[component]} must name the container of the ${component}: run make e2e-service`,
    );
  }
  return name;
}

/** What Docker says of a container: its health, `healthy` once its check passes. */
function health(id: string): string {
  return execFileSync("docker", ["inspect", "--format", "{{.State.Health.Status}}", id], {
    encoding: "utf8",
  }).trim();
}

/** Wait, up to a minute, for a container whose health check passes. */
async function untilHealthy(id: string): Promise<void> {
  const until = Date.now() + 60_000;
  while (health(id) !== "healthy") {
    if (Date.now() > until) {
      throw new Error(`the container ${id} is not healthy a minute after it started`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

/**
 * Run a path while a component is stopped, then start it again and wait for it — in a `finally`,
 * so that a path that failed leaves the platform whole for the paths after it.
 */
export async function whileStopped<T>(component: Stoppable, run: () => Promise<T>): Promise<T> {
  const id = container(component);
  execFileSync("docker", ["stop", "--time", "10", id], { stdio: "ignore" });
  try {
    return await run();
  } finally {
    execFileSync("docker", ["start", id], { stdio: "ignore" });
    await untilHealthy(id);
  }
}
