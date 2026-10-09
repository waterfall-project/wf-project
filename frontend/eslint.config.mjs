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
// JSX, and a string written as a child. The selectors here refuse what it lets through:
//
// - a string in a branch or a concatenation of a child — `{ok ? "Oui" : t("no")}`,
//   `{"Total : " + n}` —, three operators deep at most;
// - the attributes a user reads — spoken by a screen reader, shown on hover, in place of an
//   image or of an empty field, as the label of an option, on a button made of an input —
//   whose value, or a branch or a concatenation of it, is a literal with something to read.
//
// A literal passed to a function, `t(ok ? "yes" : "no")`, is a key, not a text; an empty
// alt, the mark of a decorative image, is no text either, nor the placeholder of next/image,
// `blur`, `empty` or a `data:image/` address. What stays with the review: the props of our
// own components other than `label`, and a string built by a function or a method
// (`.join`, `.concat`), in the JSX or outside it.
const TEXT = "Write the text in the catalogues of messages/, and read it with next-intl.";
const TEXT_VALUE =
  ":matches(Literal[value=/\\S/], TemplateLiteral:has(> TemplateElement[value.raw=/\\S/]))";
const OPERATOR =
  ":matches(ConditionalExpression, LogicalExpression, BinaryExpression[operator='+'])";
const TEXT_CHILD = ":matches(JSXElement, JSXFragment) > JSXExpressionContainer";
const TEXT_ATTRIBUTES = [
  "JSXAttribute[name.name=/^(aria-(label|description|roledescription|valuetext|placeholder)|title|alt|label)$/]",
  "JSXAttribute[name.name='placeholder']:not([value.value=/^((blur|empty)$|data:image\\/)/])",
  "JSXOpeningElement[name.name='input']:has(> JSXAttribute[name.name='type'][value.value=/^(submit|button|reset)$/]) > JSXAttribute[name.name='value']",
];
const TEXT_SYNTAX = [
  ...TEXT_ATTRIBUTES.flatMap((attribute) => [
    `${attribute} > ${TEXT_VALUE}`,
    `${attribute} > JSXExpressionContainer > ${TEXT_VALUE}`,
  ]),
  ...[
    ...TEXT_ATTRIBUTES.map((attribute) => `${attribute} > JSXExpressionContainer`),
    TEXT_CHILD,
  ].flatMap((container) => [
    `${container} > ${OPERATOR} > ${TEXT_VALUE}`,
    `${container} > ${OPERATOR} > ${OPERATOR} > ${TEXT_VALUE}`,
    `${container} > ${OPERATOR} > ${OPERATOR} > ${OPERATOR} > ${TEXT_VALUE}`,
  ]),
].map((selector) => ({ selector, message: TEXT }));

// No colour nor font is written in the code (charter, guide « Charte graphique »): a
// component names a token of src/theme/globals.css — `bg-primary`, `text-muted-foreground`
// —, whose light and dark values the charter holds and checks for contrast. Refused, in any
// string of the code:
//
// - a colour class of the palette of Tailwind, `bg-blue-500`, `text-white`: the charter
//   withdraws the palette, and the class would draw nothing;
// - an arbitrary value of a utility of colour that is neither a length nor a number —
//   `bg-[red]`, `bg-[#027dc6]`, `shadow-[0_0_0_2px_#f00]` —, while `ring-[3px]` and
//   `text-[14px]` pass; an arbitrary font, `font-['Arial']`; and the same utilities given a
//   custom property in parentheses, `bg-(--x)`, `font-(family-name:--x)`, which read a
//   variable no contrast was measured for — a length, `text-(length:--x)`, passes;
// - an arbitrary property that paints or sets a font, or a custom property —
//   `[color:#027dc6]`, `[font-family:Arial]`, `[--primary:#ff0000]` —, and `color-mix(`;
// - a colour written as a string of its own, `"#027dc6"`, `"rgb(2 125 198)"`;
// - the `dark:` variant, which follows the workstation alone and ignores the mode the
//   account forces: a token carries both values, no component asks which mode shows;
//
// and, whatever its value, a property of the `style` of an element that paints, draws a
// border or a shadow, or sets a font, or a custom property, its key a name or a string; and
// a colour given to `fill`, `stroke`, `color` or a stop of an SVG, other than
// `currentColor`, `none` or a `url(…)`, anywhere in its value — a branch included. What stays with the review: a colour built by a
// template with expressions or by a function, and a style or an SVG attribute given a
// variable.
const COLOUR =
  "Name a token of the charter, src/theme/globals.css; never write a colour or a font.";
const DARK = "No variant for the dark mode: a token of src/theme/globals.css carries both modes.";
const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|" +
  "blue|indigo|violet|purple|fuchsia|pink|rose|black|white";
const COLOUR_UTILITIES =
  "bg|text|border(-[xytrblse])?|outline|ring(-offset)?|fill|stroke|decoration|shadow|" +
  "drop-shadow|inset-shadow|inset-ring|text-shadow|accent|caret|divide|placeholder|from|via|to";
const COLOUR_FUNCTIONS = "rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix|light-dark";
const CLASS_START = "(^|[\\s:!])-?";
const LENGTH = "-?[\\d.]+(px|r?em|%|vh|vw|vmin|vmax|ch|ex|pt)?|length:[^\\]]+";
const PAINTING =
  "color|background|border|outline|fill|stroke|font|box-shadow|text-shadow|caret-color|" +
  "accent-color|stop-color|flood-color|lighting-color|text-decoration|column-rule|scrollbar-color";
const COLOUR_PATTERNS = [
  `${CLASS_START}(${COLOUR_UTILITIES})-(${PALETTE})(-\\d{2,3})?(/[\\w.]+)?($|\\s)`,
  `${CLASS_START}(${COLOUR_UTILITIES})-\\[(?!(${LENGTH})\\])`,
  `${CLASS_START}font-\\[(?!\\d+\\])`,
  `${CLASS_START}(${COLOUR_UTILITIES}|font)-\\((?!length:)`,
  `\\[(--[\\w-]+|(${PAINTING})[\\w-]*):`,
  `color-mix\\(`,
  `^\\s*(#([\\da-f]{3,4}|[\\da-f]{6}|[\\da-f]{8})|(${COLOUR_FUNCTIONS})\\(.*\\))\\s*$`,
];
const STYLE_PROPERTIES =
  "color|background\\w*|border\\w*|outline\\w*|boxShadow|textShadow|caretColor|accentColor|" +
  "fill|stroke|stopColor|floodColor|lightingColor|font|fontFamily|textDecoration\\w*|" +
  "columnRule\\w*|--[\\w-]*";
const SVG_PAINT =
  "JSXAttribute[name.name=/^(fill|stroke|color|stopColor|floodColor|lightingColor)$/]";
const PAINTLESS = "/^(currentcolor|none|url\\(.*\\))$/i";
const COLOUR_SYNTAX = [
  ...COLOUR_PATTERNS.flatMap((pattern) => [
    `Literal[value=${inSelector(pattern)}i]`,
    `TemplateElement[value.raw=${inSelector(pattern)}i]`,
  ]),
  `JSXAttribute[name.name='style'] Property[key.name=/^(${STYLE_PROPERTIES})$/]`,
  `JSXAttribute[name.name='style'] Property[key.value=/^(${STYLE_PROPERTIES})$/]`,
  `${SVG_PAINT} Literal[value=type(string)]:not([value=${PAINTLESS}])`,
  `${SVG_PAINT} TemplateLiteral[expressions.length=0]:not([quasis.0.value.raw=${PAINTLESS}])`,
]
  .map((selector) => ({ selector, message: COLOUR }))
  .concat(
    [`Literal[value=/(^|[\\s:!])dark:/]`, `TemplateElement[value.raw=/(^|[\\s:!])dark:/]`].map(
      (selector) => ({ selector, message: DARK }),
    ),
  );

// A zone is shown by `Signal` alone (WF-IHM-0070, guide « Charte graphique »): its shape, its
// name and its token go together. A token of a zone given to a utility of colour —
// `text-signal-alert`, `hover:bg-signal-watch` — is refused in any string outside
// src/components/signal/, so that no screen tells two zones apart by the colour alone, as a
// cell of the risk matrix tinted without the shape and the name of its zone would.
const SIGNAL = "Show a zone with Signal, src/components/signal/: its colour never shows alone.";
const SIGNAL_PATTERN = `${CLASS_START}(${COLOUR_UTILITIES})-signal-`;
const SIGNAL_SYNTAX = [
  `Literal[value=${inSelector(SIGNAL_PATTERN)}i]`,
  `TemplateElement[value.raw=${inSelector(SIGNAL_PATTERN)}i]`,
].map((selector) => ({ selector, message: SIGNAL }));

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
      "no-restricted-syntax": [
        "error",
        ...NETWORK_SYNTAX,
        ...CLIENT_SYNTAX,
        ...TEXT_SYNTAX,
        ...COLOUR_SYNTAX,
        ...SIGNAL_SYNTAX,
      ],
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
        ...COLOUR_SYNTAX,
        ...SIGNAL_SYNTAX,
        ACTION_SYNTAX,
      ],
    },
  },
  {
    // The component of the signals draws the tokens of the zones, which SIGNAL_SYNTAX refuses
    // everywhere else: the selectors of the whole front are repeated here, without it.
    files: ["src/components/signal/**"],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...NETWORK_SYNTAX,
        ...CLIENT_SYNTAX,
        ...TEXT_SYNTAX,
        ...COLOUR_SYNTAX,
      ],
    },
  },
  {
    // Tests are named for what they check; a docstring would repeat the name. The text a
    // test renders is its own data — a page in a layout, a label to find —, never shown to
    // a user, and so are the colours it traps: the rules against text and colours written
    // in the code do not apply, and the network guard does, its selectors repeated without
    // TEXT_SYNTAX and COLOUR_SYNTAX.
    files: ["**/*.test.ts", "**/*.test.tsx", "e2e/**"],
    rules: {
      "jsdoc/require-jsdoc": "off",
      "react/jsx-no-literals": "off",
      "no-restricted-syntax": ["error", ...NETWORK_SYNTAX, ...CLIENT_SYNTAX],
    },
  },
  {
    // Configuration files are not part of the TypeScript project.
    files: ["**/*.mjs"],
    extends: [tseslint.configs.disableTypeChecked],
  },
]);
