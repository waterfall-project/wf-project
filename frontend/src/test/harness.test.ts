// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { PlaywrightTestConfig } from "@playwright/test";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The platform of `make dev`, whose servers the end-to-end paths must never play against (#150).
const COMPOSE = readFileSync(
  join(import.meta.dirname, "../../../deploy/compose/compose.dev.yaml"),
  "utf-8",
);

/** The ports `make dev` publishes on the workstation: `- "3000:3000"`. */
const DEVELOPMENT_PORTS = [...COMPOSE.matchAll(/- "(\d+):\d+"/g)].map((match) => match[1]);

/** The file of the contract the fake back of `make dev` serves, from the root of the repository. */
const DEVELOPMENT_SPEC = /- \.\.\/\.\.\/(\S+):\/contract\//.exec(COMPOSE)?.[1];

const VARIABLES = [
  "WATERFALL_API_ADDRESS",
  "E2E_API_PORT",
  "E2E_FRONT_PORT",
  "E2E_PRODUCTION_PORT",
  "E2E_PART",
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

beforeEach(() => {
  for (const variable of VARIABLES) {
    vi.stubEnv(variable, undefined);
  }
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
    expect(servers).toHaveLength(3);
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
    // The fake back, the development server and the production server, each on its own port.
    expect(new Set(ports)).toEqual(new Set(["4110", "3100", "3101"]));
    for (const server of servers) {
      expect(server.command).toContain(new URL(server.url ?? "").port);
    }
  });

  it("moves its ports as the environment says", async () => {
    vi.stubEnv("E2E_API_PORT", "4050");
    vi.stubEnv("E2E_FRONT_PORT", "3050");
    vi.stubEnv("E2E_PRODUCTION_PORT", "3051");
    const servers = serversOf(await harness());
    expect(servers.map((server) => new URL(server.url ?? "").port)).toEqual([
      "4050",
      "3050",
      "3051",
    ]);
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
    const servers = serversOf(await harness());
    expect(servers.map((server) => server.command)).not.toContainEqual(
      expect.stringContaining("mock"),
    );
    expect(servers).toHaveLength(2);
    for (const server of servers) {
      expect(server.env).toEqual({ WATERFALL_API_ADDRESS: "http://api.example:8080" });
    }
  });

  it("plays the paths, then the measure once they all passed", async () => {
    expect(projectsOf(await harness())).toEqual([
      ["chromium", []],
      ["production", ["chromium"]],
    ]);
  });

  it("plays the paths alone, which can be spread over runners, with no production build", async () => {
    vi.stubEnv("E2E_PART", "paths");
    const config = await harness();
    expect(projectsOf(config)).toEqual([["chromium", []]]);
    const commands = serversOf(config).map((server) => server.command);
    expect(commands).toHaveLength(2);
    expect(commands).not.toContainEqual(expect.stringContaining("pnpm build"));
  });

  it("plays the measure alone, with no development server", async () => {
    vi.stubEnv("E2E_PART", "measure");
    const config = await harness();
    expect(projectsOf(config)).toEqual([["production", []]]);
    const commands = serversOf(config).map((server) => server.command);
    expect(commands).toHaveLength(2);
    expect(commands).not.toContainEqual(expect.stringContaining("pnpm dev"));
    expect(commands).toContainEqual(expect.stringContaining("pnpm build"));
  });

  it.each(["both", "chromium", "Paths"])("refuses %j as a part", async (named) => {
    vi.stubEnv("E2E_PART", named);
    await expect(harness()).rejects.toThrow("E2E_PART must be one of paths, measure");
  });
});
