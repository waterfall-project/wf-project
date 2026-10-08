// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the header row of the tables (#508): the header row of every table, a list or a
 * dense grid, is set on the muted background of the charter. `TableHead` sets it on the header of a
 * column (`components/ui/table.tsx`); a head written by hand, `<thead>` outside of it, takes it
 * itself. The rule is in `docs/dev/README.md`, « Une grille »; nothing else holds it: the sources
 * are read, as the guard of `useId` reads them.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..");
/** The table of the interface, whose header cells set the background themselves. */
const TABLE = join("components", "ui", "table.tsx");

/** Every component of the front: the `.tsx` files of `src/`, tests left out. */
function components(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && entry.name.endsWith(".tsx") && !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** A source without its comments: a comment that names `<thead>` is no head. */
function uncommented(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
}

/** The heads written by hand in a source that do not take the muted background, as written. */
function bareHeads(source: string): string[] {
  const heads = uncommented(source).matchAll(/<thead\b[^>]*>/g);
  return [...heads]
    .map(([head]) => head)
    .filter((head) => {
      const classes = /className=(?:"([^"]*)"|\{`([^`]*)`\})/.exec(head);
      const named = classes?.[1] ?? classes?.[2] ?? "";
      return !named.split(/\s+/).includes("bg-muted");
    });
}

describe("the header row of the tables", () => {
  it("is set on the muted background wherever a head is written by hand (#508)", () => {
    const offending = components()
      .filter((file) => relative(SOURCES, file) !== TABLE)
      .filter((file) => bareHeads(readFileSync(file, "utf-8")).length > 0);
    expect(offending.map((file) => relative(SOURCES, file))).toEqual([]);
  });

  it("finds a head without the muted background, whatever else it takes", () => {
    expect(bareHeads("<thead>")).toEqual(["<thead>"]);
    expect(bareHeads('<thead className="text-muted-foreground">')).toHaveLength(1);
    expect(bareHeads('<thead className="bg-muted/50">')).toHaveLength(1);
    expect(bareHeads("<thead className={cn(head)}>")).toHaveLength(1);
  });

  it("finds no fault in a head that takes it, nor in a comment or another element", () => {
    expect(bareHeads('<thead className="bg-muted text-muted-foreground">')).toEqual([]);
    expect(bareHeads("<thead className={`bg-muted ${size}`}>")).toEqual([]);
    expect(bareHeads("// a <thead> written by hand\n/* <thead> */")).toEqual([]);
    expect(bareHeads('<TableHeader><tbody className="x">')).toEqual([]);
  });
});
