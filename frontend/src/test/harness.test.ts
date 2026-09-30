// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import config from "../../playwright.config";

// The platform of `make dev`, whose servers the end-to-end paths must never play against (#150).
const COMPOSE = readFileSync(
  join(import.meta.dirname, "../../../deploy/compose/compose.dev.yaml"),
  "utf-8",
);

/** The ports `make dev` publishes on the workstation: `- "3000:3000"`. */
const DEVELOPMENT_PORTS = [...COMPOSE.matchAll(/- "(\d+):\d+"/g)].map((match) => match[1]);

/** The file of the contract the fake back of `make dev` serves, from the root of the repository. */
const DEVELOPMENT_SPEC = /- \.\.\/\.\.\/(\S+):\/contract\//.exec(COMPOSE)?.[1];

const servers = [config.webServer ?? []].flat();

describe("the end-to-end harness", () => {
  it("reads the ports and the contract of make dev", () => {
    expect(DEVELOPMENT_PORTS).toEqual(["4010", "3000"]);
    expect(DEVELOPMENT_SPEC).toBe("docs/api/waterfall.mock.json");
  });

  it("starts every server it plays against, and refuses a port already taken", () => {
    expect(servers).toHaveLength(3);
    for (const server of servers) {
      expect(server.reuseExistingServer).toBe(false);
    }
  });

  it("plays on ports of its own, none of make dev's", () => {
    const addresses = [
      config.use?.baseURL,
      ...(config.projects ?? []).map((project) => project.use?.baseURL),
      ...servers.map((server) => server.url),
    ].filter((address) => address !== undefined);
    const ports = addresses.map((address) => new URL(address).port);
    // The fake back, the development server and the production server, each on its own port.
    expect(new Set(ports).size).toBe(3);
    expect(ports.filter((port) => DEVELOPMENT_PORTS.includes(port))).toEqual([]);
    for (const server of servers) {
      expect(server.command).toContain(new URL(server.url ?? "").port);
    }
  });

  it("writes the contract its fake back serves where make dev does not read it", () => {
    const mock = servers.find((server) => server.command.startsWith("make -C .. mock"));
    const spec = / MOCK_SPEC=(\S+)/.exec(mock?.command ?? "")?.[1];
    expect(spec).toBeDefined();
    expect(spec).not.toBe(DEVELOPMENT_SPEC);
  });
});
