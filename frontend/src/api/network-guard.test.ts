// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The network guard of eslint.config.mjs, tried on trapped snippets: each known way of
 * reaching the network by hand is linted as if written in a page, or in src/api/server.ts,
 * and must be refused; the same snippet written in src/api/client.ts, the one module that
 * wraps the generated client, must pass the guard. And a client component must not import
 * what calls the API.
 *
 * A snippet is linted as the text of an existing file of the project, so that the typed
 * rules find it in the TypeScript project; nothing is written to the disk. The snippets are
 * data: this file itself calls nothing.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { ESLint, type Linter } from "eslint";
import tseslint from "typescript-eslint";
import { beforeAll, describe, expect, it } from "vitest";

const ROOT = join(import.meta.dirname, "../..");

// Outside the client: a page, and the module beside it. Inside: the client itself.
const PAGE = "src/app/layout.tsx";
const SERVER = "src/api/server.ts";
const CLIENT = "src/api/client.ts";

const NETWORK = "Call the API through the generated client, src/api/client.ts.";
const API_IN_CLIENT = "A client component reaches the API through a server action only.";

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
  "redaxios",
  "ky",
  "ky-universal",
  "got",
  "node-fetch",
  "undici",
  "superagent",
  "cross-fetch",
  "isomorphic-fetch",
  "ofetch",
  "wretch",
  "ws",
  "isomorphic-ws",
  "eventsource",
  "@microsoft/fetch-event-source",
  "happy-dom",
  "openapi-fetch",
  "http",
  "https",
  "http2",
  "node:http",
  "node:https",
  "node:http2",
];

// The other ways of naming a module: a subpath, a type, a re-export.
const IMPORTS: readonly string[] = [
  'import axios from "axios/unsafe/core/Axios.js";\nexport const client = axios;',
  'import type { Client } from "openapi-fetch";\nexport type Api = Client<object>;',
  'export { default } from "ky";',
  'export * from "node:https";',
];

// A dynamic import, by a string or by a template without expressions.
const DYNAMIC: readonly string[] = [
  'export const got = await import("got");',
  'export const http = await import("node:http");',
  "export const ky = await import(`ky`);",
  "export const source = await import(`@microsoft/fetch-event-source`);",
];

// A client component that imports what calls the API, however it names it.
const USE_CLIENT = '"use client";\n';
const IN_CLIENT: readonly string[] = [
  'import { serverClient } from "@/api/server";\nexport const call = serverClient;',
  'import { createApiClient } from "@/api/client";\nexport const make = createApiClient;',
  'import { serverClient } from "../api/server";\nexport const call = serverClient;',
  'export { serverClient } from "@/api/server";',
  'export * from "@/api/client";',
  'export const server = await import("@/api/server");',
  "export const server = await import(`@/api/server`);",
].map((code) => USE_CLIENT + code);

// What a client component may import of src/api/: a server action, and types.
const ALLOWED_IN_CLIENT: readonly string[] = [
  'import { updateProject } from "@/api/actions/projects";\nexport const act = updateProject;',
  'import type { ApiClient } from "@/api/client";\nexport type Api = ApiClient;',
].map((code) => USE_CLIENT + code);

// The dependencies of package.json, each examined for the lists of the guard. A new one
// fails this test until someone has asked whether it reaches the network. next-intl
// (US-0190) does not: it reads the catalogues it is handed, and its message extractor, which
// watches files, is not used. Nor do those of the charter (US-0090): class-variance-authority,
// clsx and tailwind-merge compose class names; lucide-react draws its icons inline, in SVG;
// geist ships its font files, which next/font serves from the front; Tailwind CSS and its
// PostCSS plugin read the sources at build time; axe-core reads the document of a test. Nor do
// the primitives of Radix under the components of shadcn/ui (US-0090/L4), radix-ui: menus,
// tooltips, dialogs and their focus, in the document — its avatar would load an image as an
// <img> does, from an address it is given, and the shell gives it none.
const DEPENDENCIES = [
  "class-variance-authority",
  "clsx",
  "geist",
  "lucide-react",
  "next",
  "next-intl",
  "openapi-fetch",
  "radix-ui",
  "react",
  "react-dom",
  "server-only",
  "tailwind-merge",
];
const DEV_DEPENDENCIES = [
  "@eslint/js",
  "@playwright/test",
  "@tailwindcss/postcss",
  "@testing-library/dom",
  "@testing-library/jest-dom",
  "@testing-library/react",
  "@testing-library/user-event",
  "@types/node",
  "@types/react",
  "@types/react-dom",
  "@vitest/coverage-v8",
  "axe-core",
  "eslint",
  "eslint-config-next",
  "eslint-plugin-jsdoc",
  "happy-dom",
  "openapi-typescript",
  "prettier",
  "tailwindcss",
  "typescript",
  "typescript-eslint",
  "vitest",
];

// A server action of src/api/actions/, which does not exist yet: no file of the TypeScript
// project stands in for it, so it is linted without the typed rules — the guard needs none.
const ACTION = "src/api/actions/load.ts";
const USE_SERVER = '"use server";\n';
const LOAD = [
  'import { serverClient } from "@/api/server";',
  "/** Load the projects. */",
  'export async function load() {\n  return serverClient().GET("/projects");\n}',
].join("\n");
const NO_DIRECTIVE =
  'A module of src/api/actions/ holds server actions: it opens with "use server".';

let eslint: ESLint;
let actions: ESLint;

beforeAll(() => {
  eslint = new ESLint({ cwd: ROOT });
  actions = new ESLint({ cwd: ROOT, overrideConfig: tseslint.configs.disableTypeChecked });
});

/** The messages of the guard on a snippet written in a file, and the fatal ones. */
async function lint(code: string, file: string): Promise<Linter.LintMessage[]> {
  const [result] = await eslint.lintText(code, { filePath: file });
  const messages = result?.messages ?? [];
  return messages.filter((m) => m.fatal === true || GUARD.has(m.ruleId ?? ""));
}

/** Check that a snippet is refused in a file by a rule of the guard, as an error. */
async function refused(code: string, rule: string, file = PAGE, message = NETWORK) {
  const messages = await lint(code, file);
  // Severity 2 is an error: it fails `make lint-front`, and so the chain (WF-QUA-0030).
  expect(messages.map((m) => [m.ruleId, m.severity, m.message])).toContainEqual([
    rule,
    2,
    expect.stringContaining(message),
  ]);
}

describe("the network guard", { timeout: 60_000 }, () => {
  it.each(GLOBALS)("refuses the global %s outside the client [WF-ARC-0020-A]", async (_, code) => {
    await refused(code, "no-restricted-globals");
  });

  it.each(MEMBERS)("refuses the member in %j outside the client [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-properties");
  });

  it.each(CLIENTS)("refuses an import of %s outside the client [WF-ARC-0020-A]", async (name) => {
    await refused(
      `import * as client from "${name}";\nexport default client;`,
      "no-restricted-imports",
    );
  });

  it.each(IMPORTS)("refuses %j outside the client [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-imports");
  });

  it.each(DYNAMIC)("refuses the dynamic %j outside the client [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-syntax");
  });

  it("refuses them in src/api/ beside the client too [WF-ARC-0020-A]", async () => {
    await refused(GLOBALS[0]?.[1] ?? "", "no-restricted-globals", SERVER);
    await refused(MEMBERS[1] ?? "", "no-restricted-properties", SERVER);
    await refused(IMPORTS[0] ?? "", "no-restricted-imports", SERVER);
    await refused(DYNAMIC[0] ?? "", "no-restricted-syntax", SERVER);
  });

  it("refuses require() anywhere, the client included [WF-ARC-0020-A]", async () => {
    const code = 'export const axios: unknown = require("axios");';
    for (const file of [PAGE, CLIENT]) {
      const [result] = await eslint.lintText(code, { filePath: file });
      expect(result?.messages.map((m) => m.ruleId)).toContain(
        "@typescript-eslint/no-require-imports",
      );
    }
  });

  it("lets every trapped snippet through in the client [WF-ARC-0020-A]", async () => {
    const imports = CLIENTS.map(
      (name) => `import * as client from "${name}";\nexport default client;`,
    );
    const snippets = [
      ...GLOBALS.map(([, code]) => code),
      ...MEMBERS,
      ...imports,
      ...IMPORTS,
      ...DYNAMIC,
    ];
    for (const code of snippets) {
      expect(await lint(code, CLIENT), code).toEqual([]);
    }
  });

  it("lets a page call the API through the server client", async () => {
    const code = [
      'import { serverClient } from "@/api/server";',
      'export const projects = await serverClient().GET("/projects");',
    ].join("\n");
    expect(await lint(code, PAGE)).toEqual([]);
  });

  it.each(IN_CLIENT)("refuses %j in a client component [WF-ARC-0020-A]", async (code) => {
    await refused(code, "no-restricted-syntax", PAGE, API_IN_CLIENT);
  });

  it.each(ALLOWED_IN_CLIENT)("lets %j through in a client component", async (code) => {
    expect(await lint(code, PAGE)).toEqual([]);
  });

  it("refuses a module of actions without the use server directive [WF-ARC-0020-A]", async () => {
    const [result] = await actions.lintText(LOAD, { filePath: ACTION });
    expect(result?.messages.map((m) => [m.ruleId, m.severity, m.message])).toEqual([
      ["no-restricted-syntax", 2, NO_DIRECTIVE],
    ]);
  });

  it("lets a module of server actions through", async () => {
    const [result] = await actions.lintText(USE_SERVER + LOAD, { filePath: ACTION });
    expect(result?.messages).toEqual([]);
  });

  it("keeps the rest of the guard in the actions [WF-ARC-0020-A]", async () => {
    const code = USE_SERVER + (DYNAMIC[0] ?? "");
    const [result] = await actions.lintText(code, { filePath: ACTION });
    expect(result?.messages.map((m) => [m.ruleId, m.message])).toContainEqual([
      "no-restricted-syntax",
      NETWORK,
    ]);
  });

  it("knows every dependency of package.json", () => {
    const text = readFileSync(join(ROOT, "package.json"), "utf-8");
    const manifest = JSON.parse(text) as {
      dependencies: Record<string, string>;
      devDependencies: Record<string, string>;
    };
    const examine =
      "a dependency was added or removed: ask whether it reaches the network, add it to " +
      "NETWORK_MODULES of eslint.config.mjs if it does, then to the lists of this test";
    expect(
      Object.keys(manifest.dependencies).sort((a, b) => a.localeCompare(b)),
      examine,
    ).toEqual(DEPENDENCIES);
    expect(
      Object.keys(manifest.devDependencies).sort((a, b) => a.localeCompare(b)),
      examine,
    ).toEqual(DEV_DEPENDENCIES);
  });
});
