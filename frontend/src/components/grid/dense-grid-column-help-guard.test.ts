// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the grids the definitions of the columns know (WF-IHM-0140-A, #1805): the test of
 * completeness, `column-help.test.ts`, reads only the grids it lists, and a grid passed to
 * `<DenseGrid` that it does not list has columns without a definition that nothing notices — so it
 * was for the commands of the editable grid of the sub-projects (US-0670/L4, #1140). Here each
 * `config` given to a `<DenseGrid` is followed to what builds it in its source — the name it is
 * bound to, the constant or the function behind it, as `button-title-guard.test.ts` follows the
 * classes of a button —, and one of those names must be imported by `column-help.test.ts`.
 *
 * A config that arrives as a parameter of a component (the `make` of the reference grids) cannot be
 * followed: any name of the source stands for it, as it receives one of them. What stays with the
 * review: a name listed that the test imports and no longer calls.
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

/** The names a source imports as values, not as types. */
function imported(file: ts.SourceFile): Set<string> {
  const names = new Set<string>();
  for (const statement of file.statements) {
    const clause = ts.isImportDeclaration(statement) ? statement.importClause : undefined;
    if (clause === undefined || clause.phaseModifier === ts.SyntaxKind.TypeKeyword) {
      continue;
    }
    if (clause.name !== undefined) {
      names.add(clause.name.text);
    }
    const bindings = clause.namedBindings;
    if (bindings !== undefined && ts.isNamedImports(bindings)) {
      for (const element of bindings.elements.filter((e) => !e.isTypeOnly)) {
        names.add(element.name.text);
      }
    }
  }
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

/** The identifiers an expression reads, itself included. */
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
 * Whether the config of a `<DenseGrid` is one of the listed. The names it reads are followed
 * through the bindings of the source; one of them must be listed.
 */
function listedConfig(config: ts.Node, file: ts.SourceFile, listed: ReadonlySet<string>): boolean {
  const seen = new Set<string>();
  const state = { parameter: false };
  const follow = (expression: ts.Node) => {
    for (const name of identifiers(expression)) {
      if (seen.has(name)) {
        continue;
      }
      seen.add(name);
      const bound = scoped(name, expression);
      if (bound !== undefined) {
        follow(bound);
      } else if (isParameter(name, expression)) {
        state.parameter = true;
      }
    }
  };
  follow(config);
  if ([...seen].some((name) => listed.has(name))) {
    return true;
  }
  return state.parameter && identifiers(file).some((name) => listed.has(name));
}

/** The `<DenseGrid` of a source whose config is not among the listed, each by its line. */
function unlisted(source: string, listed: ReadonlySet<string>, name = "source.tsx"): string[] {
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
      if (config === undefined || !listedConfig(config, file, listed)) {
        found.push(`${name}:${line.toString()} config ${config?.getText(file) ?? "(none)"}`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

describe("the grids of the front", () => {
  const listed = imported(parse(readFileSync(LIST, "utf-8"), LIST));
  const grids = components().flatMap((file) =>
    unlisted(readFileSync(file, "utf-8"), listed, relative(SOURCES, file)),
  );

  it("are all in the list of column-help.test.ts, which checks their columns have a definition [WF-IHM-0140-A]", () => {
    expect(listed.size).toBeGreaterThan(0);
    expect(grids).toEqual([]);
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

  it("lets a config received as a parameter stand for a name the source holds", () => {
    const known = new Set(["userGrid"]);
    const make =
      "function G({ make }) { const c = useMemo(() => make(1), [make]); return <DenseGrid config={c} />; }";
    expect(unlisted(`${make}\nconst a = userGrid;`, known)).toEqual([]);
    expect(unlisted(make, known)).toHaveLength(1);
  });
});
