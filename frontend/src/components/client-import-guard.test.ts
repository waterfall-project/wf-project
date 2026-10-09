// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard against a value of a client module imported by a module of the server (#548, défaut
 * n° 12 de `docs/dev/typescript.md`): what a module `"use client"` exports reaches a server
 * component as a reference to the client, not as the value — a key of the settings of a grid read
 * by a page was once such a reference, and the settings were never read again (`RATE_GRID_KEY`,
 * L42a), as a filter called by a page failed before it (US-0210/L1). A component crosses the
 * boundary, which is what the directive is for; any other value lives in a module without
 * directive, which both sides read. The test project `node` ignores the directive, and no unit test
 * sees the defect: the sources are read, as the guard of `useId` reads them. A module of the server
 * is one that does not open on `"use client"` — a page of `src/app`, a module without directive,
 * an action `"use server"` —; a re-export brings what it re-exports as an import would
 * (`export { X } from`, `export * from`, a namespace). An import of types alone (`import type`,
 * `type` before a name) brings nothing at run time, and is let through.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..");

/** Every module of the front: the `.ts` and `.tsx` files of `src/`, tests and types left out. */
function modules(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) =>
        entry.isFile() &&
        /\.tsx?$/.test(entry.name) &&
        !entry.name.endsWith(".d.ts") &&
        !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** Whether a module runs in the browser: it opens on the directive, after its comments if any. */
function isClient(source: string): boolean {
  // A line comment runs to the end of its line: a directive written within it is none.
  // Each alternative opens on its own character, and a block comment ends at its first `*/`: no
  // string can be matched two ways, so the test runs in linear time (CodeQL, inefficient regex).
  return /^(?:\s|\/\/[^\n]*\n|\/\*(?:[^*]|\*(?!\/))*\*\/)*["']use client["']/.test(source);
}

/** A source without its comments: an import written in a comment is none. */
function uncommented(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
}

/** An import or a re-export of a module: where from, and the values it brings. */
interface ValueImport {
  readonly from: string;
  readonly values: readonly string[];
}

/**
 * The names a list of specifiers brings — `{ A, B as C, type D, default as E }` —: each by the name
 * it is exported under, but a default, by the name it is given; the types left out.
 */
function specified(list: string): string[] {
  return list
    .split(",")
    .map((specifier) => specifier.trim())
    .filter((specifier) => specifier !== "" && !/^type\s/.test(specifier))
    .map((specifier) => {
      const [exported = specifier, local] = specifier.split(/\s+as\s+/);
      return exported === "default" && local !== undefined ? local : exported;
    });
}

/**
 * The values a clause of an import brings: the default, by its local name; the namespace, as `*`,
 * apart; the names between braces.
 */
function imported(clause: string): string[] {
  const named = /\{([^}]*)\}/.exec(clause)?.[1];
  const heads = clause
    .replace(/\{[^}]*\}/, "")
    .split(",")
    .map((head) => head.trim())
    .filter((head) => head !== "");
  return [...heads.map((head) => (head.startsWith("*") ? "*" : head)), ...specified(named ?? "")];
}

/**
 * The values each import and each re-export of a source brings — `export { X } from`, and
 * `export * from`, a namespace —; the imports and re-exports of types alone bring none.
 */
function valueImports(source: string): ValueImport[] {
  const code = uncommented(source);
  const imports = [...code.matchAll(/import\s+(type\s+)?([^;]*?)\s*from\s*["']([^"']+)["']/g)].map(
    ([, onlyTypes, clause = "", from = ""]) => ({
      from,
      values: onlyTypes === undefined ? imported(clause) : [],
    }),
  );
  const exports = [
    ...code.matchAll(
      /export\s+(type\s+)?(\*(?:\s+as\s+\w+)?|\{[^}]*\})\s*from\s*["']([^"']+)["']/g,
    ),
  ].map(([, onlyTypes, clause = "", from = ""]) => ({
    from,
    values:
      onlyTypes !== undefined
        ? []
        : clause.startsWith("*")
          ? ["*"]
          : // A default re-exported as the default is judged as the module that exports it.
            specified(clause.slice(1, -1)).filter((name) => name !== "default"),
  }));
  return [...imports, ...exports].filter(({ values }) => values.length > 0);
}

/**
 * Whether a name is that of a component: a name in PascalCase — a capital, then letters and digits,
 * one of them small —, never a constant in capitals (`RATE_GRID_KEY`), a function or a namespace.
 */
function isComponent(name: string): boolean {
  return /^[A-Z][A-Za-z0-9]*$/.test(name) && /[a-z]/.test(name);
}

/** The file of the front a module imports, or `undefined` for a package. */
function resolved(importer: string, from: string): string | undefined {
  const base = from.startsWith("@/")
    ? join(SOURCES, from.slice(2))
    : from.startsWith(".")
      ? join(dirname(importer), from)
      : undefined;
  if (base === undefined) {
    return undefined;
  }
  return [".ts", ".tsx", "/index.ts", "/index.tsx"]
    .map((extension) => `${base}${extension}`)
    .find((file) => existsSync(file));
}

/**
 * What a module of the server imports of a client module that is no component, as
 * `<module> ← <name> from <import>`; nothing for a client module, which reads another as it is.
 */
function offences(
  file: string,
  source: string,
  clientAt: (file: string) => boolean,
): readonly string[] {
  if (isClient(source)) {
    return [];
  }
  return valueImports(source).flatMap(({ from, values }) => {
    const target = resolved(file, from);
    if (target === undefined || !clientAt(target)) {
      return [];
    }
    return values
      .filter((value) => !isComponent(value))
      .map((value) => `${relative(SOURCES, file)} ← ${value} from ${from}`);
  });
}

describe("the values a module of the server imports from a client module", () => {
  it("are components alone: any other value arrives as a reference to the client (#548)", () => {
    const sources = new Map(modules().map((file) => [file, readFileSync(file, "utf-8")]));
    const clientAt = (file: string) => isClient(sources.get(file) ?? "");
    const found = [...sources].flatMap(([file, source]) => offences(file, source, clientAt));
    expect(found).toEqual([]);
  });

  it("refuse a value that is no component, a constant, a function or a namespace", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    const client = () => true;
    expect(
      offences(page, 'import { RATE_GRID_KEY } from "@/components/reference/rate-grid";', client),
    ).toEqual([
      "app/reference/costs/page.tsx ← RATE_GRID_KEY from @/components/reference/rate-grid",
    ]);
    expect(
      offences(
        page,
        'import { RateGrid, rateHref } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual(["app/reference/costs/page.tsx ← rateHref from @/components/reference/rate-grid"]);
    expect(
      offences(page, 'import * as grid from "@/components/reference/rate-grid";', client),
    ).toHaveLength(1);
  });

  it("read the re-exports, a namespace re-exported as one, and judge a default under the name it is given", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    const client = () => true;
    expect(
      offences(
        page,
        'export { RATE_GRID_KEY, RateGrid } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual([
      "app/reference/costs/page.tsx ← RATE_GRID_KEY from @/components/reference/rate-grid",
    ]);
    expect(offences(page, 'export * from "@/components/reference/rate-grid";', client)).toEqual([
      "app/reference/costs/page.tsx ← * from @/components/reference/rate-grid",
    ]);
    expect(
      offences(page, 'export type { RateRow } from "@/components/reference/rate-grid";', client),
    ).toEqual([]);
    expect(
      offences(page, 'export { default } from "@/components/reference/rate-grid";', client),
    ).toEqual([]);
    expect(
      offences(
        page,
        'import { default as rateKey } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual(["app/reference/costs/page.tsx ← rateKey from @/components/reference/rate-grid"]);
    expect(
      offences(
        page,
        'import { default as RateGrid } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual([]);
  });

  it("report a default and a namespace imported together, each apart", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    expect(
      offences(
        page,
        'import rateKey, * as grid from "@/components/reference/rate-grid";',
        () => true,
      ),
    ).toEqual([
      "app/reference/costs/page.tsx ← rateKey from @/components/reference/rate-grid",
      "app/reference/costs/page.tsx ← * from @/components/reference/rate-grid",
    ]);
    expect(
      offences(
        page,
        'import RateGrid, { rateHref } from "@/components/reference/rate-grid";',
        () => true,
      ),
    ).toEqual(["app/reference/costs/page.tsx ← rateHref from @/components/reference/rate-grid"]);
  });

  it("let a component through, under its name or another, and a default one", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    const client = () => true;
    expect(
      offences(
        page,
        'import { RateGrid as Rates } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual([]);
    expect(
      offences(page, 'import RateGrid from "@/components/reference/rate-grid";', client),
    ).toEqual([]);
  });

  it("let an import of types through, of the declaration or of a name", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    const client = () => true;
    expect(
      offences(page, 'import type { RateRow } from "@/components/reference/rate-grid";', client),
    ).toEqual([]);
    expect(
      offences(
        page,
        'import { type RATE_KEY, RateGrid, type rateRow } from "@/components/reference/rate-grid";',
        client,
      ),
    ).toEqual([]);
  });

  it("judge neither a client module, nor an import of a module of the server, a package or a comment", () => {
    const page = join(SOURCES, "app", "reference", "costs", "page.tsx");
    expect(
      offences(page, '"use client";\nimport { KEY } from "@/components/grid/query";', () => true),
    ).toEqual([]);
    expect(
      offences(page, 'import { OFFSET } from "@/components/grid/query";', () => false),
    ).toEqual([]);
    expect(offences(page, 'import { useId } from "react";', () => true)).toEqual([]);
    expect(
      offences(page, '// import { KEY } from "@/components/grid/query";\nconst a = 1;', () => true),
    ).toEqual([]);
  });
});
