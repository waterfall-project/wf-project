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
      // The API is called through the generated client only (WF-ARC-0020).
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Call the API through the generated client, in src/api/." },
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
    // The generated client is where the network is called.
    files: ["src/api/**"],
    rules: { "no-restricted-globals": "off" },
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
