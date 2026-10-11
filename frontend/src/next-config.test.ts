// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * What the build of the front keeps of its environment (US-0430): the image of production is
 * built once and published, so nothing the platform sets — the addresses of the API, of Keycloak
 * and of Redis, the secret of the client of the front — may be written into it by `next build`
 * (WF-SEC-0010). Next writes into the build the `env` of its configuration and every
 * `process.env.NEXT_PUBLIC_*` the code reads: the configuration is loaded, and the sources read.
 * The image itself was started and asked by hand when the lot was made; no work of the chain
 * starts it yet. A check of the chain that builds and starts it on the pull requests is to come,
 * and with it what these tests do not see — a page prerendered by the build.
 *
 * `next build` also writes keys of its own into its output, and so into the image: the key of
 * the closures of the server actions (`encryptionKey`, `.next/server/server-reference-manifest.*`)
 * and those of the draft mode (`previewMode*`, `.next/prerender-manifest.json`). They protect
 * nothing as long as the front has no closure for Next to encrypt and no draft mode: a server
 * action lives in a module of `src/api/actions/` that opens on `"use server"`, never inline in a
 * function, and nothing reads `draftMode`. The last tests hold it; the key of the server actions
 * is to be set at start by `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, which Next reads before the one
 * of the build (#825).
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

/** A source without its comments: a directive or a name written in a comment is none. */
function uncommented(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
}

/**
 * A directive that makes a server function, whose closure Next encrypts with the key of the
 * build: `"use server"`, and `"use cache"` in each of its forms, which Next compiles alike.
 */
const DIRECTIVE = /["']use (?:server|cache)\b[^"'\n]*["']/g;

/**
 * What a module of the build, named from the root of the front, writes that a key of the build
 * would protect: every directive of a server function but the one that opens a module of
 * `src/api/actions/`, and every use of `draftMode`.
 */
function keyed(path: string, source: string): string[] {
  const code = uncommented(source);
  const directives = [...code.matchAll(DIRECTIVE)].map(([directive]) => directive);
  const opening =
    path.startsWith("src/api/actions/") && /^\s*["']use server["']/.test(code) ? 1 : 0;
  const draft = /\bdraftMode\b/.test(code) ? ["draftMode"] : [];
  return [...directives.slice(opening), ...draft];
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the build of the front", () => {
  it("traces the standalone server only for the image of production", async () => {
    expect((await loadConfig("1")).output).toBe("standalone");
    expect((await loadConfig(undefined)).output).toBeUndefined();
  });

  it("has no env in its configuration, and no source reads a NEXT_PUBLIC_ variable", async () => {
    expect((await loadConfig("1")).env).toBeUndefined();
    const inlined = builtSources()
      .filter((path) => readFileSync(path, "utf8").includes("NEXT_PUBLIC_"))
      .map((path) => relative(FRONT, path));
    expect(inlined).toEqual([]);
  });

  it("gives its keys nothing to protect: no inline server action, no draft mode", () => {
    const offending = builtSources().flatMap((path) => {
      const name = relative(FRONT, path);
      return keyed(name, readFileSync(path, "utf8")).map((found) => `${name}: ${found}`);
    });
    expect(offending).toEqual([]);
  });

  it("allows a server directive only where it opens a module of the actions", () => {
    const opening = '// SPDX\n/** The actions. */\n"use server";\n\nexport async function a() {}\n';
    expect(keyed("src/api/actions/load.ts", opening)).toEqual([]);
    expect(
      keyed("src/api/actions/load.ts", opening.replace('"use server"', "'use server'")),
    ).toEqual([]);
    expect(keyed("src/app/page.tsx", opening)).toEqual(['"use server"']);
    expect(keyed("src/api/server.ts", opening)).toEqual(['"use server"']);
  });

  it("finds a server function written inline, in a module of the actions or elsewhere", () => {
    const inline = 'export async function a() {\n  "use server";\n}\n';
    expect(keyed("src/app/page.tsx", inline)).toEqual(['"use server"']);
    expect(keyed("src/api/actions/load.ts", inline)).toEqual(['"use server"']);
    expect(keyed("src/api/actions/load.ts", `"use server";\n${inline}`)).toEqual(['"use server"']);
    expect(keyed("src/app/page.tsx", 'async function c() {\n  "use cache: private";\n}\n')).toEqual(
      ['"use cache: private"'],
    );
  });

  it("finds draftMode, and neither it nor a directive in a comment", () => {
    expect(keyed("src/app/page.tsx", 'import { draftMode } from "next/headers";\n')).toEqual([
      "draftMode",
    ]);
    const commented =
      '// "use server" and draftMode are not used\n/* "use cache" */\nconst a = 1;\n';
    expect(keyed("src/app/page.tsx", commented)).toEqual([]);
  });
});
