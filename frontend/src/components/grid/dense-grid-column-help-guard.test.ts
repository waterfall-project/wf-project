// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the grids the definitions of the columns know (WF-IHM-0140-A, #1805): the test of
 * completeness, `column-help.test.ts`, reads only the grids it lists, and a grid passed to
 * `<DenseGrid` that it does not list has columns without a definition that nothing notices — so it
 * was for the commands of the editable grid of the sub-projects (US-0670/L4, #1140). Here each
 * `config` given to a `<DenseGrid` is followed to what builds it in its source — the name it is
 * bound to, the constant or the function behind it, as `button-title-guard.test.ts` follows the
 * classes of a button —, and the names it reads must be those of grids the list checks.
 *
 * A grid the list checks is a name whose `.columns` that test reads (`ESTIMATE_GRID.columns`,
 * `userGrid(…).columns`): not a name it merely imports (`commandColumns`, `KEPT_HEADING`). Of a
 * ternary, each branch must be one; the condition and the names of properties (`x.userGrid`) are
 * not read; a config built from a list of columns that is not a grid, whatever it holds beside,
 * is not one.
 *
 * What the reading cannot tell stays with the review: a factory is seen by its name, not by the
 * variant it is called for (`subprojectGrid(true)` or not); a `DenseGrid` renamed on import is not
 * found; a `<DenseGrid {...props} />` has no `config` to read and is reported; a config that
 * arrives as a parameter of a component (the `make` of the reference grids) cannot be followed, and
 * any grid name of the source stands for it, as it receives one of them.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import ts from "typescript";
import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..", "..");
const LIST = join(import.meta.dirname, "column-help.test.ts");

function parse(source: string, name: string): ts.SourceFile {
  return ts.createSourceFile(name, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
}

/** Every component of the front: the `.tsx` files of `src/`, tests left out. */
function components(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && entry.name.endsWith(".tsx") && !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** The name at the root of an expression: `userGrid` of `userGrid(x).columns`. */
function root(node: ts.Expression): string | undefined {
  let current = node;
  for (;;) {
    if (ts.isIdentifier(current)) {
      return current.text;
    }
    if (
      ts.isPropertyAccessExpression(current) ||
      ts.isCallExpression(current) ||
      ts.isElementAccessExpression(current) ||
      ts.isNonNullExpression(current) ||
      ts.isParenthesizedExpression(current) ||
      ts.isAsExpression(current)
    ) {
      current = current.expression;
    } else {
      return undefined;
    }
  }
}

/** The grids a test checks: the roots of the `.columns` it reads. */
function gridNames(file: ts.SourceFile): Set<string> {
  const names = new Set<string>();
  const visit = (node: ts.Node) => {
    if (ts.isPropertyAccessExpression(node) && node.name.text === "columns") {
      const name = root(node.expression);
      if (name !== undefined) {
        names.add(name);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return names;
}

/** The expression a name is bound to by the nearest block that binds it, going up from a node. */
function scoped(name: string, from: ts.Node): ts.Expression | undefined {
  for (let node = from.parent; ; node = node.parent) {
    if (ts.isBlock(node) || ts.isSourceFile(node)) {
      for (const statement of node.statements) {
        if (!ts.isVariableStatement(statement)) {
          continue;
        }
        for (const declaration of statement.declarationList.declarations) {
          if (
            ts.isIdentifier(declaration.name) &&
            declaration.name.text === name &&
            declaration.initializer !== undefined
          ) {
            return declaration.initializer;
          }
        }
      }
    }
    if (ts.isSourceFile(node)) {
      return undefined;
    }
  }
}

/** The identifiers a node reads, itself included. */
function identifiers(node: ts.Node): string[] {
  const found: string[] = [];
  const visit = (child: ts.Node) => {
    if (ts.isIdentifier(child)) {
      found.push(child.text);
    }
    ts.forEachChild(child, visit);
  };
  visit(node);
  return found;
}

/** Whether a binding name — a parameter, destructured or not — declares a name. */
function declares(binding: ts.BindingName, name: string): boolean {
  if (ts.isIdentifier(binding)) {
    return binding.text === name;
  }
  return binding.elements.some(
    (element) => ts.isBindingElement(element) && declares(element.name, name),
  );
}

/** Whether a name is a parameter of a function that holds the node. */
function isParameter(name: string, from: ts.Node): boolean {
  for (let node = from.parent; !ts.isSourceFile(node); node = node.parent) {
    if (ts.isFunctionLike(node) && node.parameters.some((p) => declares(p.name, name))) {
      return true;
    }
  }
  return false;
}

/**
 * Whether the config of a `<DenseGrid` is a grid the list checks: the names it reads are followed
 * through the bindings of the source. Each branch of a ternary must be one; any other expression,
 * one of its parts.
 */
function isListed(config: ts.Node, file: ts.SourceFile, grids: ReadonlySet<string>): boolean {
  const seen = new Set<string>();
  const state = { parameter: false };
  const reads = (node: ts.Node): boolean => {
    if (ts.isConditionalExpression(node)) {
      return reads(node.whenTrue) && reads(node.whenFalse);
    }
    if (ts.isPropertyAccessExpression(node)) {
      return reads(node.expression);
    }
    if (ts.isPropertyAssignment(node)) {
      return reads(node.initializer);
    }
    if (ts.isParameter(node)) {
      return false;
    }
    if (ts.isVariableDeclaration(node)) {
      return node.initializer !== undefined && reads(node.initializer);
    }
    if (ts.isIdentifier(node)) {
      if (grids.has(node.text)) {
        return true;
      }
      if (seen.has(node.text)) {
        return false;
      }
      seen.add(node.text);
      const bound = scoped(node.text, node);
      if (bound !== undefined) {
        return reads(bound);
      }
      state.parameter ||= isParameter(node.text, node);
      return false;
    }
    return ts.forEachChild(node, (child) => (reads(child) ? true : undefined)) ?? false;
  };
  return reads(config) || (state.parameter && identifiers(file).some((name) => grids.has(name)));
}

/** The `<DenseGrid` of a source whose config is not a listed grid, each by its line. */
function unlisted(source: string, grids: ReadonlySet<string>, name = "source.tsx"): string[] {
  const file = parse(source, name);
  const found: string[] = [];
  const visit = (node: ts.Node) => {
    if (
      (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) &&
      node.tagName.getText(file) === "DenseGrid"
    ) {
      const config = node.attributes.properties
        .filter(ts.isJsxAttribute)
        .find((attribute) => attribute.name.getText(file) === "config")?.initializer;
      const line = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1;
      if (config === undefined || !isListed(config, file, grids)) {
        found.push(`${name}:${line.toString()} config ${config?.getText(file) ?? "(none)"}`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

describe("the grids of the front", () => {
  const grids = gridNames(parse(readFileSync(LIST, "utf-8"), LIST));
  const found = components().flatMap((file) =>
    unlisted(readFileSync(file, "utf-8"), grids, relative(SOURCES, file)),
  );

  it("are all in the list of column-help.test.ts, which checks their columns have a definition [WF-IHM-0140-A]", () => {
    expect(found).toEqual([]);
  });

  it("takes for the grids of the list those whose columns it checks, not the names it imports", () => {
    for (const grid of ["userGrid", "SUBPROJECT_GRID", "subprojectGrid", "costGrid", "rateGrid"]) {
      expect(grids.has(grid), grid).toBe(true);
    }
    for (const other of ["commandColumns", "KEPT_HEADING", "RATE_HEADINGS", "estimateReference"]) {
      expect(grids.has(other), other).toBe(false);
    }
  });

  it("reads the grids the list has, and names one it does not", () => {
    const known = new Set(["userGrid", "SUBPROJECT_GRID"]);
    expect(unlisted("<DenseGrid config={SUBPROJECT_GRID} />", known)).toEqual([]);
    expect(
      unlisted(
        "function A() { const config = useMemo(() => userGrid(x), [x]); return <DenseGrid config={config} />; }",
        known,
      ),
    ).toEqual([]);
    expect(
      unlisted(
        "const EDITABLE = userGrid(true);\nfunction A() { return <DenseGrid config={EDITABLE} />; }",
        known,
      ),
    ).toEqual([]);
    expect(unlisted("<DenseGrid config={c ? userGrid : SUBPROJECT_GRID} />", known)).toEqual([]);
    expect(
      unlisted(
        "function A() { const config = useMemo(() => forgottenGrid(x), [x]); return <DenseGrid config={config} />; }",
        known,
      ),
    ).toEqual(["source.tsx:1 config {config}"]);
    expect(unlisted("<DenseGrid config={NEW_GRID} rows={[]} />", known, "new-grid.tsx")).toEqual([
      "new-grid.tsx:1 config {NEW_GRID}",
    ]);
  });

  it("names a grid that is not wholly a listed one", () => {
    const known = new Set(["userGrid"]);
    // Columns that are no grid, whatever the grid beside them.
    expect(
      unlisted("<DenseGrid config={{ columns: [...commandColumns()] }} />", known),
    ).toHaveLength(1);
    // A branch of a ternary that is not listed.
    expect(unlisted("<DenseGrid config={c ? userGrid : NEW} />", known)).toHaveLength(1);
    // A name of a property is not the name of a grid.
    expect(unlisted("<DenseGrid config={other.userGrid} />", known)).toHaveLength(1);
    expect(unlisted("<DenseGrid {...props} />", known)).toEqual(["source.tsx:1 config (none)"]);
  });

  it("lets a config received as a parameter stand for a grid the source holds", () => {
    const known = new Set(["userGrid"]);
    const make =
      "function G({ make }) { const c = useMemo(() => make(1), [make]); return <DenseGrid config={c} />; }";
    expect(unlisted(`${make}\nconst a = userGrid;`, known)).toEqual([]);
    expect(unlisted(make, known)).toHaveLength(1);
  });
});
