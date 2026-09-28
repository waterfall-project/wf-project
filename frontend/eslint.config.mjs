// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rule set of the front (WF-QUA-0030), readable here: what is added to the shared
 * configurations, and what is withdrawn, each with its reason.
 *
 * No rule is silenced in the code: inline configuration comments are not honoured
 * (`noInlineConfig`), and `make sources` refuses them. An exception for a kind of file is
 * written below, with its reason. ESLint runs with `--max-warnings 0`.
 */
import js from "@eslint/js";
import nextVitals from "eslint-config-next/core-web-vitals";
import jsdoc from "eslint-plugin-jsdoc";
import { defineConfig, globalIgnores } from "eslint/config";
import tseslint from "typescript-eslint";

// The API is called through the generated client only (WF-ARC-0020): outside src/api/,
// nothing reaches the network. The same message for every way of trying.
const NETWORK = "Call the API through the generated client, in src/api/.";

// The objects of the platform that send a request: fetch, and the older or streaming
// transports a hand-written call could fall back on — XMLHttpRequest, WebSocket,
// EventSource. Refused as bare identifiers and as members (globalThis.X, window.X, an alias
// of them, a destructured property), since a global is also a property of the global object.
const NETWORK_GLOBALS = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource"];

// Members only: navigator.sendBeacon posts a request, and has no global of its own.
const NETWORK_MEMBERS = [...NETWORK_GLOBALS, "sendBeacon"];

// The modules that send requests: the http clients of npm, the WebSocket and EventSource
// clients of Node, the http modules of Node with and without their node: prefix, and
// openapi-fetch itself, which only src/api/client.ts wraps with the types of the contract.
// A subpath of a module (axios/unsafe/…) is refused with it.
const NETWORK_MODULES = [
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
const NETWORK_MODULE = `^(${NETWORK_MODULES.join("|")})(/.*)?$`;

export default defineConfig([
  globalIgnores([
    ".next/**",
    "coverage/**",
    "test-results/**",
    "playwright-report/**",
    "next-env.d.ts",
    "src/api/generated/**",
  ]),
  js.configs.recommended,
  nextVitals,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  jsdoc.configs["flat/recommended-typescript-error"],
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    linterOptions: { noInlineConfig: true, reportUnusedDisableDirectives: "error" },
    rules: {
      // Cyclomatic complexity under 15 (US-0050): ESLint reports a value above the maximum.
      complexity: ["error", 14],
      // 1,000 lines at most, blank lines and comments included (US-0050).
      "max-lines": ["error", { max: 1000, skipBlankLines: false, skipComments: false }],
      // The network guard (WF-ARC-0020, US-0270): see NETWORK_GLOBALS and the lists
      // after it. A member is refused whatever its object, so a third-party API whose own
      // .fetch never touches the network would be excepted here, with its reason, never
      // silenced in the code.
      "no-restricted-globals": [
        "error",
        ...NETWORK_GLOBALS.map((name) => ({ name, message: NETWORK })),
      ],
      "no-restricted-properties": [
        "error",
        ...NETWORK_MEMBERS.map((property) => ({ property, message: NETWORK })),
      ],
      "no-restricted-imports": [
        "error",
        { patterns: [{ regex: NETWORK_MODULE, message: NETWORK }] },
      ],
      // no-restricted-imports reads static imports and re-exports only: a dynamic import()
      // of the same modules is refused here. require() is refused everywhere by
      // @typescript-eslint/no-require-imports, of the strict configuration.
      "no-restricted-syntax": [
        "error",
        {
          selector: `ImportExpression[source.value=/${NETWORK_MODULE.replaceAll("/", "\\/")}/]`,
          message: NETWORK,
        },
      ],
      // A docstring for what is exported; its types are TypeScript's, never repeated.
      "jsdoc/require-jsdoc": [
        "error",
        {
          publicOnly: true,
          require: { FunctionDeclaration: true, ClassDeclaration: true, MethodDefinition: true },
        },
      ],
      "jsdoc/no-types": "error",
      // Withdrawn: a section per parameter or for the returned value would repeat the
      // signature (US-0050); a section is written only when it says something more.
      "jsdoc/require-param": "off",
      "jsdoc/require-returns": "off",
    },
  },
  {
    // The generated client is where the network is called. no-restricted-syntax holds
    // nothing but the network guard so far: a selector added to it for another reason must
    // be repeated here.
    files: ["src/api/**"],
    rules: {
      "no-restricted-globals": "off",
      "no-restricted-properties": "off",
      "no-restricted-imports": "off",
      "no-restricted-syntax": "off",
    },
  },
  {
    // Tests are named for what they check; a docstring would repeat the name.
    files: ["**/*.test.ts", "**/*.test.tsx", "e2e/**"],
    rules: { "jsdoc/require-jsdoc": "off" },
  },
  {
    // Configuration files are not part of the TypeScript project.
    files: ["**/*.mjs"],
    extends: [tseslint.configs.disableTypeChecked],
  },
]);
