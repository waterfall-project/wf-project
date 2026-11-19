// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The sobriety of the charter (guide, « Charte graphique »), for the components of shadcn/ui
 * copied into the repository: no transition, no animation, no gradient, and one shadow only,
 * `shadow-md`, on what floats over the page. What shadcn/ui ships with them is taken out when a
 * component is copied; this test says so when it comes back.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { uncommented } from "@/test/uncommented";

const UI = import.meta.dirname;
const SOURCES = readdirSync(UI)
  .filter((name) => name.endsWith(".tsx") || (name.endsWith(".ts") && !name.includes(".test.")))
  .map((name): [string, string] => [name, readFileSync(join(UI, name), "utf-8")]);

// An ornament, as a class of Tailwind names it; `shadow-md` alone passes.
const ORNAMENT =
  /(^|[\s"'`:!])(transition(-[\w[\]-]+)?|animate-[\w-]+|bg-(linear|radial|conic)-[\w-]+|bg-gradient-[\w-]+|(drop|text|inset)-shadow(-[\w[\]/-]+)?|shadow(?!-md\b)(-[\w[\]/-]+)?)(?=[\s"'`]|$)/;

/** The first ornament a source writes outside its comments, or undefined when it writes none. */
function ornamentOf(source: string): string | undefined {
  return ORNAMENT.exec(uncommented(source))?.[0].trim();
}

describe("the components of shadcn/ui copied into the repository", () => {
  it("are read, every one of them", () => {
    expect(SOURCES.map(([name]) => name)).toContain("sidebar.tsx");
    expect(SOURCES.map(([name]) => name)).toContain("button.tsx");
  });

  it.each(SOURCES)("carry no ornament but the shadow of what floats: %s", (_name, source) => {
    expect(ornamentOf(source)).toBeUndefined();
  });

  it("find an ornament written after a string holding a comment opener [US-2800]", () => {
    for (const source of [
      'const a = "http://x"; const b = "shadow-sm";',
      'const a = "/*";\nconst b = "transition-all";\n// */',
    ]) {
      expect(ornamentOf(source), source).toBeDefined();
    }
  });

  it("tell an ornament from what it is not", () => {
    for (const ornament of [
      '"transition-colors"',
      '"animate-in"',
      '"shadow-sm"',
      '"shadow"',
      '"drop-shadow-md"',
      '"text-shadow-sm"',
      '"inset-shadow-xs"',
    ]) {
      expect(ORNAMENT.test(ornament), ornament).toBe(true);
    }
    for (const plain of ['"shadow-md"', '"truncate"', '"data-[state=open]:bg-accent"']) {
      expect(ORNAMENT.test(plain), plain).toBe(false);
    }
  });
});
