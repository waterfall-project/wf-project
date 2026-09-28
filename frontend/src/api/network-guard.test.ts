// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The network guard of eslint.config.mjs, tried on trapped snippets: each way of reaching
 * the network by hand is linted as if written in a page, and must be refused; the same
 * snippet written in src/api/, where the generated client lives, must pass the guard.
 *
 * A snippet is linted as the text of an existing file of the project, so that the typed
 * rules find it in the TypeScript project; nothing is written to the disk. The snippets are
 * data: this file itself calls nothing.
 */
import { join } from "node:path";

import { ESLint, type Linter } from "eslint";
import { beforeAll, describe, expect, it } from "vitest";

// Outside src/api/: a page. Inside: the client itself.
const OUTSIDE = "src/app/layout.tsx";
const INSIDE = "src/api/client.ts";

// The rules the guard is made of; any other rule's opinion of a snippet is beside the point.
const GUARD = new Set([
  "no-restricted-globals",
  "no-restricted-properties",
  "no-restricted-imports",
  "no-restricted-syntax",
]);

const GLOBALS: readonly [string, string][] = [
  ["fetch", 'export const answer = fetch("/api/v1/projects");'],
  ["XMLHttpRequest", "export const request = new XMLHttpRequest();"],
  ["WebSocket", 'export const socket = new WebSocket("ws://localhost:4010/api/v1");'],
  ["EventSource", 'export const events = new EventSource("/api/v1/tasks");'],
];

const MEMBERS: readonly string[] = [
  'export const answer = window.fetch("/api/v1/projects");',
  'export const answer = globalThis.fetch("/api/v1/projects");',
  'export const answer = globalThis["fetch"]("/api/v1/projects");',
  "export const request = new window.XMLHttpRequest();",
  "export const request = new globalThis.XMLHttpRequest();",
  'export const socket = new window.WebSocket("ws://localhost:4010/api/v1");',
  'export const socket = new globalThis.WebSocket("ws://localhost:4010/api/v1");',
  'export const events = new window.EventSource("/api/v1/tasks");',
  'export const events = new globalThis.EventSource("/api/v1/tasks");',
  'export const sent = navigator.sendBeacon("/api/v1/projects", "{}");',
  "const { fetch: send } = globalThis;\nexport const answer = send;",
];

const CLIENTS: readonly string[] = [
  "axios",
  "ky",
  "got",
  "node-fetch",
  "undici",
  "superagent",
  "cross-fetch",
  "isomorphic-fetch",
  "ofetch",
  "wretch",
  "ws",
  "eventsource",
  "openapi-fetch",
  "http",
  "https",
  "http2",
  "node:http",
  "node:https",
  "node:http2",
];

// The other ways of naming a module: a subpath, a type, a re-export, a dynamic import.
const IMPORTS: readonly string[] = [
  'import axios from "axios/unsafe/core/Axios.js";\nexport const client = axios;',
  'import type { Client } from "openapi-fetch";\nexport type Api = Client<object>;',
  'export { default } from "ky";',
  'export * from "node:https";',
  'export const got = await import("got");',
  'export const http = await import("node:http");',
];

let eslint: ESLint;

beforeAll(() => {
  eslint = new ESLint({ cwd: join(import.meta.dirname, "../..") });
});

/** The messages of the guard on a snippet written in a file, and the fatal ones. */
async function lint(code: string, file: string): Promise<Linter.LintMessage[]> {
  const [result] = await eslint.lintText(code, { filePath: file });
  const messages = result?.messages ?? [];
  return messages.filter((m) => m.fatal === true || GUARD.has(m.ruleId ?? ""));
}

/** Check that a snippet is refused outside src/api/ by a rule of the guard, as an error. */
async function refused(code: string, rule: string): Promise<void> {
  const messages = await lint(code, OUTSIDE);
  // Severity 2 is an error: it fails `make lint-front`, and so the chain (WF-QUA-0030).
  expect(messages.map((m) => [m.ruleId, m.severity, m.message])).toContainEqual([
    rule,
    2,
    expect.stringContaining("Call the API through the generated client, in src/api/."),
  ]);
}

describe("the network guard", { timeout: 60_000 }, () => {
  it.each(GLOBALS)("refuses the global %s outside src/api/ [WF-ARC-0020-A]", async (_, code) => {
    await refused(code, "no-restricted-globals");
  });

  it.each(MEMBERS)("refuses the member in %j outside src/api/ [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-properties");
  });

  it.each(CLIENTS)("refuses an import of %s outside src/api/ [WF-ARC-0020-A]", async (name) => {
    await refused(
      `import * as client from "${name}";\nexport default client;`,
      "no-restricted-imports",
    );
  });

  it.each(IMPORTS.slice(0, 4))("refuses %j outside src/api/ [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-imports");
  });

  it.each(IMPORTS.slice(4))(
    "refuses the dynamic %j outside src/api/ [WF-ARC-0020-A]",
    async (code) => {
      await refused(code, "no-restricted-syntax");
    },
  );

  it("refuses require() anywhere, src/api/ included [WF-ARC-0020-A]", async () => {
    const code = 'export const axios: unknown = require("axios");';
    for (const file of [OUTSIDE, INSIDE]) {
      const [result] = await eslint.lintText(code, { filePath: file });
      expect(result?.messages.map((m) => m.ruleId)).toContain(
        "@typescript-eslint/no-require-imports",
      );
    }
  });

  it("lets every trapped snippet through in src/api/ [WF-ARC-0020-A]", async () => {
    const imports = CLIENTS.map(
      (name) => `import * as client from "${name}";\nexport default client;`,
    );
    const snippets = [...GLOBALS.map(([, code]) => code), ...MEMBERS, ...imports, ...IMPORTS];
    for (const code of snippets) {
      expect(await lint(code, INSIDE), code).toEqual([]);
    }
  });

  it("lets a page call the API through the server client", async () => {
    const code = [
      'import { serverClient } from "@/api/server";',
      'export const projects = await serverClient().GET("/projects");',
    ].join("\n");
    expect(await lint(code, OUTSIDE)).toEqual([]);
  });
});
