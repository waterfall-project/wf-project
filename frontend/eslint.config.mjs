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

// The API is called through the generated client only (WF-ARC-0020): outside
// src/api/client.ts, the one module that wraps it, nothing reaches the network — not even
// the server actions of src/api/actions/, which call the client like any other code. The
// same message for every way of trying.
const NETWORK = "Call the API through the generated client, src/api/client.ts.";

// The objects of the platform that send a request: fetch, and the older or streaming
// transports a hand-written call could fall back on — XMLHttpRequest, WebSocket,
// EventSource. Refused as bare identifiers and as members (globalThis.X, window.X, an alias
// of them, a destructured property), since a global is also a property of the global object.
const NETWORK_GLOBALS = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource"];

// Members only: navigator.sendBeacon posts a request, and has no global of its own.
const NETWORK_MEMBERS = [...NETWORK_GLOBALS, "sendBeacon"];

// The modules known to send requests: the http clients of npm and their wrappers, the
// WebSocket and EventSource clients, the http modules of Node with and without their node:
// prefix, and openapi-fetch itself, which only src/api/client.ts wraps with the types of
// the contract. A subpath of a module (axios/unsafe/…) is refused with it. The list is
// known, not complete: network-guard.test.ts freezes the dependencies of package.json, so
// that a new one is examined for this list before it is added.
const NETWORK_MODULES = [
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
  // A browser in Node, whose window fetches: the environment of the component tests,
  // which Vitest loads by its name, and nothing imports.
  "happy-dom",
  "openapi-fetch",
  "http",
  "https",
  "http2",
  "node:http",
  "node:https",
  "node:http2",
];

// A pattern written into an esquery selector: its slashes escaped.
const inSelector = (pattern) => `/${pattern.replaceAll("/", "\\/")}/`;
const NETWORK_MODULE = `^(${NETWORK_MODULES.join("|")})(/.*)?$`;

// no-restricted-imports reads static imports and re-exports only: a dynamic import() of
// the same modules, by a string or by a template without expressions, is refused by
// no-restricted-syntax. require() is refused everywhere by
// @typescript-eslint/no-require-imports, of the strict configuration.
const NETWORK_SYNTAX = [
  `ImportExpression[source.value=${inSelector(NETWORK_MODULE)}]`,
  `ImportExpression > TemplateLiteral[expressions.length=0][quasis.0.value.raw=${inSelector(NETWORK_MODULE)}]`,
].map((selector) => ({ selector, message: NETWORK }));

// Only the server of Next calls the API (§4.3.1): a file under the "use client" directive
// imports nothing of src/api/ but its server actions (src/api/actions/), which Next turns
// into references, and types, which the build erases. This is the check of the chain, and
// it sees the direct import only: a module without a directive that imports
// @/api/server, imported in turn by a client component, is left to server-only, imported
// by client.ts and server.ts — the net of `next build`, which no check runs yet (#131).
const CLIENT = "Program:has(> ExpressionStatement[directive='use client'])";
const API_MODULE = inSelector("^(@/|(\\.\\.?/)+)api/(?!actions/)");
const API_IN_CLIENT = "A client component reaches the API through a server action only.";
const CLIENT_SYNTAX = [
  `${CLIENT} ImportDeclaration[importKind!='type'][source.value=${API_MODULE}]`,
  `${CLIENT} ExportNamedDeclaration[exportKind!='type'][source.value=${API_MODULE}]`,
  `${CLIENT} ExportAllDeclaration[exportKind!='type'][source.value=${API_MODULE}]`,
  `${CLIENT} ImportExpression[source.value=${API_MODULE}]`,
  `${CLIENT} ImportExpression > TemplateLiteral[expressions.length=0][quasis.0.value.raw=${API_MODULE}]`,
].map((selector) => ({ selector, message: API_IN_CLIENT }));

// A module of src/api/actions/ is trusted by CLIENT_SYNTAX because Next turns it into
// references: it must then be a module of server actions, under the "use server"
// directive, or a client component importing it would carry the client of the API into
// the browser.
const ACTION_SYNTAX = {
  selector: "Program:not(:has(> ExpressionStatement[directive='use server']))",
  message: 'A module of src/api/actions/ holds server actions: it opens with "use server".',
};

// No text for the user is written in the code (WF-QUA-0070): it comes from the catalogues
// of messages/, in the language of the reader. react/jsx-no-literals refuses the text of
// JSX, and a string written as a child. The selectors here refuse what it lets through: a
// string in a branch of a child — `{ok ? "Oui" : t("no")}` —, and the attributes a user
// reads — spoken by a screen reader, shown on hover, in place of an image or of an empty
// field — whose value, or a branch of it, is a literal with something to read. A literal
// passed to a function, `t(ok ? "yes" : "no")`, is a key, not a text; an empty alt, the
// mark of a decorative image, is no text either.
const TEXT = "Write the text in the catalogues of messages/, and read it with next-intl.";
const TEXT_VALUE =
  ":matches(Literal[value=/\\S/], TemplateLiteral:has(> TemplateElement[value.raw=/\\S/]))";
const BRANCH = ":matches(ConditionalExpression, LogicalExpression)";
const TEXT_CHILD = ":matches(JSXElement, JSXFragment) > JSXExpressionContainer";
const TEXT_ATTRIBUTE = "JSXAttribute[name.name=/^(aria-label|title|alt|placeholder)$/]";
const TEXT_SYNTAX = [
  `${TEXT_ATTRIBUTE} > ${TEXT_VALUE}`,
  `${TEXT_ATTRIBUTE} > JSXExpressionContainer > ${TEXT_VALUE}`,
  ...[`${TEXT_ATTRIBUTE} > JSXExpressionContainer`, TEXT_CHILD].flatMap((container) => [
    `${container} > ${BRANCH} > ${TEXT_VALUE}`,
    `${container} > ${BRANCH} > ${BRANCH} > ${TEXT_VALUE}`,
  ]),
].map((selector) => ({ selector, message: TEXT }));

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
      // The network guard (WF-ARC-0020, US-0270): see NETWORK and the lists after it. A
      // member is refused whatever its object, so a third-party API whose own .fetch never
      // touches the network would be excepted here, with its reason, never silenced in the
      // code.
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
      "no-restricted-syntax": ["error", ...NETWORK_SYNTAX, ...CLIENT_SYNTAX, ...TEXT_SYNTAX],
      // See TEXT: the text of JSX, and a string written as a child. The attributes are
      // TEXT_SYNTAX's, which knows which of them a user reads.
      "react/jsx-no-literals": [
        "error",
        { noStrings: true, ignoreProps: true, allowedStrings: [] },
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
    // The client of the API is where the network is called: that one module, not src/api/,
    // where the server actions call the client like any other code. It is no client
    // component, so the selectors of CLIENT_SYNTAX have nothing to find in it, nor JSX for
    // those of TEXT_SYNTAX.
    files: ["src/api/client.ts"],
    rules: {
      "no-restricted-globals": "off",
      "no-restricted-properties": "off",
      "no-restricted-imports": "off",
      "no-restricted-syntax": "off",
    },
  },
  {
    // The options of a rule are replaced whole from one block to the next: the selectors
    // of the whole front are repeated here, with the one of the actions.
    files: ["src/api/actions/**"],
    ignores: ["**/*.test.ts", "**/*.test.tsx"],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...NETWORK_SYNTAX,
        ...CLIENT_SYNTAX,
        ...TEXT_SYNTAX,
        ACTION_SYNTAX,
      ],
    },
  },
  {
    // Tests are named for what they check; a docstring would repeat the name. The text a
    // test renders is its own data — a page in a layout, a label to find —, never shown to
    // a user.
    files: ["**/*.test.ts", "**/*.test.tsx", "e2e/**"],
    rules: { "jsdoc/require-jsdoc": "off", "react/jsx-no-literals": "off" },
  },
  {
    // Configuration files are not part of the TypeScript project.
    files: ["**/*.mjs"],
    extends: [tseslint.configs.disableTypeChecked],
  },
]);
