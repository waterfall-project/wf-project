// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * What the build of the front keeps of its environment (US-0430): the image of production is
 * built once and published, so nothing the platform sets — the addresses of the API, of Keycloak
 * and of Redis, the secret of the client of the front — may be written into it by `next build`
 * (WF-SEC-0010). Next writes into the build the `env` of its configuration and every
 * `process.env.NEXT_PUBLIC_*` the code reads: the configuration is loaded, and the sources read.
 * The image itself was started and asked by hand when the lot was made; the chain starts it.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import type { NextConfig } from "next";
import { afterEach, describe, expect, it, vi } from "vitest";

const FRONT = join(import.meta.dirname, "..");

/** The configuration of Next, loaded anew under the environment of the build. */
async function loadConfig(standalone: string | undefined): Promise<NextConfig> {
  vi.stubEnv("WATERFALL_STANDALONE", standalone);
  vi.resetModules();
  const loaded = await import("../next.config");
  return loaded.default;
}

/** The code of the front that the build reads: `src/`, tests left out, and the configuration. */
function builtSources(): string[] {
  const sources = readdirSync(join(FRONT, "src"), { recursive: true, withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && /\.tsx?$/.test(entry.name) && !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
  return [...sources, join(FRONT, "next.config.ts")];
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the build of the front", () => {
  it("traces the standalone server only for the image of production", async () => {
    expect((await loadConfig("1")).output).toBe("standalone");
    expect((await loadConfig(undefined)).output).toBeUndefined();
  });

  it("writes no variable of the environment into the build", async () => {
    expect((await loadConfig("1")).env).toBeUndefined();
    const inlined = builtSources()
      .filter((path) => readFileSync(path, "utf8").includes("NEXT_PUBLIC_"))
      .map((path) => relative(FRONT, path));
    expect(inlined).toEqual([]);
  });
});
