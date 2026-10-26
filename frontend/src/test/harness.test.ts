// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { PlaywrightTestConfig } from "@playwright/test";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The platform of `make dev`, whose servers the end-to-end paths must never play against (#150).
const COMPOSE = readFileSync(
  join(import.meta.dirname, "../../../deploy/compose/compose.dev.yaml"),
  "utf-8",
);

/** The root of the repository, where the Makefile is. */
const REPOSITORY = join(import.meta.dirname, "../../..");

/** The ports `make dev` publishes on the workstation: `- "3000:3000"`. */
const DEVELOPMENT_PORTS = [...COMPOSE.matchAll(/- "(\d+):\d+"/g)].map((match) => match[1]);

/** The file of the contract the fake back of `make dev` serves, from the root of the repository. */
const DEVELOPMENT_SPEC = /- \.\.\/\.\.\/(\S+):\/contract\//.exec(COMPOSE)?.[1];

const VARIABLES = [
  "WATERFALL_API_ADDRESS",
  "WATERFALL_AUTH",
  "E2E_API_PORT",
  "E2E_FRONT_PORT",
  "E2E_PART",
  "E2E_BUILT",
  "E2E_DEV_SERVER",
  "E2E_WORKERS",
  "TEST_PARALLEL_INDEX",
  "CI",
  "NEXT_SERVER_ACTIONS_ENCRYPTION_KEY",
];

/** The configuration of the harness, read anew under the environment of the test. */
async function harness(): Promise<PlaywrightTestConfig> {
  vi.resetModules();
  return (await import("../../playwright.config")).default;
}

/** The projects the harness plays, by name, each with the projects it waits for. */
function projectsOf(config: PlaywrightTestConfig) {
  return (config.projects ?? []).map((project) => [project.name, project.dependencies ?? []]);
}

/** The servers the harness starts. */
function serversOf(config: PlaywrightTestConfig) {
  return [config.webServer ?? []].flat();
}

/** The fronts the harness starts: the servers that are told where the API is. */
function frontsOf(config: PlaywrightTestConfig) {
  return serversOf(config).filter((server) => server.env !== undefined);
}

/** The front the harness starts, when it starts one alone. */
async function frontOf(): Promise<NonNullable<ReturnType<typeof serversOf>[number]>> {
  const fronts = frontsOf(await harness());
  expect(fronts).toHaveLength(1);
  const [front] = fronts;
  if (front === undefined) {
    throw new Error("no front");
  }
  return front;
}

/** Play against the service, as `make e2e-service` does. */
function againstTheService(): void {
  vi.stubEnv("E2E_PART", "service");
  // Read by the configuration from the log of the proxy, which the run of the service has.
  vi.stubEnv("E2E_SERVICE_STARTED", "2026-10-21T00:00:00.000000000Z");
  vi.stubEnv("WATERFALL_API_ADDRESS", "http://127.0.0.1:4210");
}

beforeEach(() => {
  for (const variable of VARIABLES) {
    vi.stubEnv(variable, undefined);
  }
  // One worker, one front, unless a test says otherwise.
  vi.stubEnv("E2E_WORKERS", "1");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the end-to-end harness", () => {
  it("reads the ports and the contract of make dev", () => {
    expect(DEVELOPMENT_PORTS).toEqual(["4010", "3000"]);
    expect(DEVELOPMENT_SPEC).toBe("docs/api/waterfall.mock.json");
  });

  it("starts every server it plays against, and refuses a port already taken", async () => {
    const servers = serversOf(await harness());
    expect(servers).toHaveLength(2);
    for (const server of servers) {
      expect(server.reuseExistingServer).toBe(false);
    }
  });

  it("plays on ports of its own, none of make dev's", async () => {
    const config = await harness();
    const servers = serversOf(config);
    const addresses = [
      config.use?.baseURL,
      ...(config.projects ?? []).map((project) => project.use?.baseURL),
      ...servers.map((server) => server.url),
    ].filter((address) => address !== undefined);
    const ports = addresses.map((address) => new URL(address).port);
    // The fake back and the front, each on its own port.
    expect(new Set(ports)).toEqual(new Set(["4110", "3100"]));
    for (const server of servers) {
      expect(server.command).toContain(new URL(server.url ?? "").port);
    }
  });

  it("moves its ports as the environment says", async () => {
    vi.stubEnv("E2E_API_PORT", "4050");
    vi.stubEnv("E2E_FRONT_PORT", "3050");
    const servers = serversOf(await harness());
    expect(servers.map((server) => new URL(server.url ?? "").port)).toEqual(["4050", "3050"]);
    expect(servers[0]?.command).toContain("MOCK_PORT=4050");
  });

  it.each(["0", "65536", "30.5", "port", ""])("refuses %j as a port", async (named) => {
    vi.stubEnv("E2E_FRONT_PORT", named);
    await expect(harness()).rejects.toThrow("E2E_FRONT_PORT must be a port");
  });

  it("writes the contract its fake back serves where make dev does not read it", async () => {
    const mock = serversOf(await harness()).find((server) =>
      server.command.startsWith("make -C .. mock"),
    );
    const spec = / MOCK_SPEC=(\S+)/.exec(mock?.command ?? "")?.[1];
    expect(spec).toBeDefined();
    expect(spec).not.toBe(DEVELOPMENT_SPEC);
  });

  it("plays against the API the environment names, and starts no fake back for it", async () => {
    vi.stubEnv("WATERFALL_API_ADDRESS", "http://api.example:8080");
    vi.stubEnv("NEXT_SERVER_ACTIONS_ENCRYPTION_KEY", "a-key-of-the-server-actions");
    const servers = serversOf(await harness());
    expect(servers.map((server) => server.command)).not.toContainEqual(
      expect.stringContaining("mock"),
    );
    expect(servers).toHaveLength(1);
    expect(servers[0]?.env).toEqual({
      WATERFALL_API_ADDRESS: "http://api.example:8080",
      WATERFALL_API_CONNECTIONS: "closed",
      WATERFALL_E2E: "1",
      NEXT_SERVER_ACTIONS_ENCRYPTION_KEY: "a-key-of-the-server-actions",
    });
  });

  it("gives the front built against a named API a key of its server actions, which it does not start without", async () => {
    vi.stubEnv("WATERFALL_API_ADDRESS", "http://api.example:8080");
    const key = (await frontOf()).env?.NEXT_SERVER_ACTIONS_ENCRYPTION_KEY ?? "";
    // The 32 bytes of an AES-256 key, as Next reads it.
    expect(Buffer.from(key, "base64")).toHaveLength(32);
  });

  it("has the front send the token of the fake back, and say it is the harness that builds it for production", async () => {
    expect((await frontOf()).env).toMatchObject({ WATERFALL_AUTH: "mock", WATERFALL_E2E: "1" });
  });

  it("says it is the harness against the service too, where the real authentication stands (#1265)", async () => {
    againstTheService();
    const { env } = await frontOf();
    expect(env).toMatchObject({ WATERFALL_E2E: "1", WATERFALL_API_CONNECTIONS: "closed" });
    expect(env).not.toHaveProperty("WATERFALL_AUTH");
  });

  it("has the front open a connection of its own for each request to the API, which Prism closes when idle (#1145)", async () => {
    expect((await frontOf()).env?.WATERFALL_API_CONNECTIONS).toBe("closed");
  });

  it("warms no route before the paths: the built front compiles nothing on demand", async () => {
    expect((await harness()).globalSetup).toBeUndefined();
  });

  it("plays the paths, then the measure once they all passed, against one front", async () => {
    const config = await harness();
    expect(projectsOf(config)).toEqual([
      ["chromium", []],
      ["measure", ["chromium"]],
    ]);
    for (const project of config.projects ?? []) {
      expect(project.use?.baseURL).toBeUndefined();
    }
  });

  it.each([
    ["the whole harness", undefined],
    ["the paths alone", "paths"],
    ["the measure alone", "measure"],
  ])("plays %s against the front built for production, built first", async (_part, named) => {
    vi.stubEnv("E2E_PART", named);
    const { command } = await frontOf();
    expect(command).toBe(
      "WATERFALL_API_ADDRESS=http://127.0.0.1:9 pnpm build && pnpm start --hostname 127.0.0.1 --port 3100",
    );
  });

  it("builds the front with no API to reach, as make build-front does (#131)", () => {
    const makefile = readFileSync(join(import.meta.dirname, "../../../Makefile"), "utf-8");
    const nowhere = /^NOWHERE := (\S+)$/m.exec(makefile)?.[1];
    expect(nowhere).toBe("http://127.0.0.1:9");
    expect(makefile).toContain("build-front: export WATERFALL_API_ADDRESS = $(NOWHERE)");
  });

  it("starts the front built already when E2E_BUILT says so", async () => {
    vi.stubEnv("E2E_BUILT", "1");
    expect((await frontOf()).command).toBe("pnpm start --hostname 127.0.0.1 --port 3100");
  });

  it("plays the paths against the service on the built front, listening on every interface", async () => {
    againstTheService();
    vi.stubEnv("E2E_BUILT", "1");
    const config = await harness();
    expect(serversOf(config).map((server) => server.command)).toEqual([
      "pnpm start --hostname 0.0.0.0 --port 3100",
    ]);
    expect(projectsOf(config).map(([name]) => name)).not.toContain("measure");
  });

  it("plays the paths alone, which can be spread over runners", async () => {
    vi.stubEnv("E2E_PART", "paths");
    expect(projectsOf(await harness())).toEqual([["chromium", []]]);
  });

  it("plays the measure alone", async () => {
    vi.stubEnv("E2E_PART", "measure");
    expect(projectsOf(await harness())).toEqual([["measure", []]]);
  });

  it.each(["both", "chromium", "Paths"])("refuses %j as a part", async (named) => {
    vi.stubEnv("E2E_PART", named);
    await expect(harness()).rejects.toThrow("E2E_PART must be one of paths, measure");
  });

  it.each(["E2E_BUILT", "E2E_DEV_SERVER"])("refuses %s other than 1", async (variable) => {
    vi.stubEnv(variable, "yes");
    await expect(harness()).rejects.toThrow(`${variable} must be 1, or unset: yes`);
  });
});

describe("the paths against the development server, on a workstation (E2E_DEV_SERVER)", () => {
  it("plays the paths against next dev, and leaves the measure out of the whole harness", async () => {
    vi.stubEnv("E2E_DEV_SERVER", "1");
    const config = await harness();
    expect(projectsOf(config)).toEqual([["chromium", []]]);
    expect(serversOf(config).map((server) => server.command)).toContainEqual(
      "pnpm dev --hostname 127.0.0.1 --port 3100",
    );
  });

  it("plays the paths against the service on next dev, on every interface", async () => {
    againstTheService();
    vi.stubEnv("E2E_DEV_SERVER", "1");
    expect((await frontOf()).command).toBe("pnpm dev --hostname 0.0.0.0 --port 3100");
  });

  it("never plays the measure against it: the measure alone is built and started", async () => {
    vi.stubEnv("E2E_DEV_SERVER", "1");
    vi.stubEnv("E2E_PART", "measure");
    const config = await harness();
    expect(projectsOf(config)).toEqual([["measure", []]]);
    expect((await frontOf()).command).toContain("pnpm build && pnpm start");
  });

  it("fails the run in the chain, saying so", async () => {
    vi.stubEnv("E2E_DEV_SERVER", "1");
    vi.stubEnv("CI", "true");
    await expect(harness()).rejects.toThrow(
      "E2E_DEV_SERVER=1 plays the paths against next dev, on a workstation only",
    );
  });

  it("is not needed in the chain, which plays against the built front", async () => {
    vi.stubEnv("CI", "true");
    vi.stubEnv("E2E_BUILT", "1");
    expect((await frontOf()).command).toBe("pnpm start --hostname 127.0.0.1 --port 3100");
  });
});

describe("the fronts of the harness, one for each worker of the paths (#1477)", () => {
  it("starts a front for each worker, on the ports after the first, the first alone building it", async () => {
    vi.stubEnv("E2E_WORKERS", "3");
    const config = await harness();
    expect(config.workers).toBe(3);
    expect(frontsOf(config).map((server) => [server.command, server.url])).toEqual([
      [
        "WATERFALL_API_ADDRESS=http://127.0.0.1:9 pnpm build && pnpm start --hostname 127.0.0.1 --port 3100",
        "http://127.0.0.1:3100",
      ],
      ["pnpm start --hostname 127.0.0.1 --port 3101", "http://127.0.0.1:3101"],
      ["pnpm start --hostname 127.0.0.1 --port 3102", "http://127.0.0.1:3102"],
    ]);
  });

  it.each([
    ["0", "http://127.0.0.1:3050"],
    ["2", "http://127.0.0.1:3052"],
    ["4", "http://127.0.0.1:3051"],
  ])("has the worker of place %s play against its own front", async (index, front) => {
    vi.stubEnv("E2E_WORKERS", "3");
    vi.stubEnv("E2E_FRONT_PORT", "3050");
    vi.stubEnv("TEST_PARALLEL_INDEX", index);
    expect((await harness()).use?.baseURL).toBe(front);
  });

  it.each([
    [12, 6],
    [4, 2],
    [3, 1],
    [1, 1],
  ])(
    "plays on %i processors with %i workers, half of them, when the environment names no number of workers",
    async (processors, expected) => {
      vi.doMock("node:os", async (original) => ({
        ...(await original<typeof import("node:os")>()),
        availableParallelism: () => processors,
      }));
      vi.stubEnv("E2E_WORKERS", undefined);
      vi.stubEnv("E2E_BUILT", "1");
      try {
        const config = await harness();
        expect(config.workers).toBe(expected);
        expect(frontsOf(config)).toHaveLength(expected);
      } finally {
        vi.doUnmock("node:os");
      }
    },
  );

  it.each([
    ["the measure alone", { E2E_PART: "measure" }],
    ["the development server", { E2E_DEV_SERVER: "1" }],
  ])("starts one front alone for %s", async (_part, environment) => {
    vi.stubEnv("E2E_WORKERS", "3");
    for (const [variable, value] of Object.entries(environment)) {
      vi.stubEnv(variable, value);
    }
    expect(frontsOf(await harness())).toHaveLength(1);
  });

  it("starts one front alone against the service, whose realm knows the address of one", async () => {
    againstTheService();
    vi.stubEnv("E2E_WORKERS", "3");
    vi.stubEnv("TEST_PARALLEL_INDEX", "2");
    const config = await harness();
    expect(frontsOf(config)).toHaveLength(1);
    expect(config.use?.baseURL).toBe("http://127.0.0.1:3100");
  });

  it.each(["0", "-1", "2.5", "two"])("refuses %j as a number of workers", async (named) => {
    vi.stubEnv("E2E_WORKERS", named);
    await expect(harness()).rejects.toThrow("E2E_WORKERS must be a whole number of workers");
  });

  it.each([
    ["3", "3"],
    ["", ""],
  ])(
    "is told the workers by make e2e WORKERS=%j, which passes none to Playwright itself",
    (named, told) => {
      // The recipe of make e2e run, its installation and its Playwright replaced: what Playwright
      // would be started under, and with which arguments.
      const run = execFileSync(
        "make",
        [
          "-s",
          "e2e",
          `WORKERS=${named}`,
          "E2E_BUILT=1",
          "TESTS=e2e/accessibility.spec.ts",
          "PNPM=true",
          "PNPM_HEAVY=printenv E2E_WORKERS; echo",
        ],
        { cwd: REPOSITORY, encoding: "utf-8" },
      );
      const [workersTold, playwright] = run.trimEnd().split("\n");
      expect(workersTold).toBe(told);
      expect(playwright).toBe("exec playwright test e2e/accessibility.spec.ts");
    },
  );
});
