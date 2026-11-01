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
 * `userGrid(…).columns`) and that it imports or holds at its top: not a name it merely imports
 * (`commandColumns`, `KEPT_HEADING`), nor a variable of a loop (`catalogue`). What the guard reads of
 * a config: a name of the list, called or not, and its `.columns`; a name bound in the source,
 * followed; each branch of a ternary, of `??`, `||` and `&&`; the function `useMemo` is given,
 * never its dependencies; the first argument of `withDifference`; a list of spreads of grids; an
 * object whose spreads and whose `columns` are grids. The names of properties (`x.userGrid`) and
 * the conditions are not read. Any other form — a call of another function, a literal, a list with a
 * column of its own — is not a grid, and is reported: a false positive is better than a miss.
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
      for (const element of bindings.elements) {
        names.add(element.name.text);
      }
    }
  }
  return names;
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
  // A root is a name the file imports or holds at its top: not a variable of a loop or a callback.
  const known = imported(file);
  for (const statement of file.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const { name } of statement.declarationList.declarations) {
        if (ts.isIdentifier(name)) {
          known.add(name.text);
        }
      }
    }
  }
  const visit = (node: ts.Node) => {
    if (ts.isPropertyAccessExpression(node) && node.name.text === "columns") {
      const name = root(node.expression);
      if (name !== undefined && known.has(name)) {
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
 * The functions that give a config back wrapped, with the position of the argument that holds the
 * config: `withDifference(read, differential)` is the grid `read`, whatever `differential` is.
 */
const WRAPPERS: ReadonlyMap<string, number> = new Map([["withDifference", 0]]);

/** The expressions a function returns: its body, or each `return` of its block. */
function returned(fn: ts.ArrowFunction | ts.FunctionExpression): ts.Expression[] {
  if (!ts.isBlock(fn.body)) {
    return [fn.body];
  }
  const found: ts.Expression[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isFunctionLike(node) && node !== fn) {
      return;
    }
    if (ts.isReturnStatement(node) && node.expression !== undefined) {
      found.push(node.expression);
    }
    ts.forEachChild(node, visit);
  };
  visit(fn.body);
  return found;
}

/**
 * Whether the config of a `<DenseGrid` is a grid the list checks: the names it reads are followed
 * through the bindings of the source, and every part of it that holds columns must be one. A name
 * of the list is one, called or not, and its `.columns`; a ternary, `??` and `||` need each branch;
 * `useMemo` is its function, never its dependencies; `withDifference` is its first argument; a list
 * is spreads of grids; an object is spreads of grids, and a `columns` that is one. Any other form —
 * a call of another function, a literal — is not read, and is reported.
 */
function isListed(config: ts.Node, file: ts.SourceFile, grids: ReadonlySet<string>): boolean {
  const reader: Reader = { file, grids, reading: new Set(), parameter: false };
  return (
    readsGrid(config, reader) ||
    (reader.parameter && identifiers(file).some((name) => grids.has(name)))
  );
}

/** What the reading of a config carries: the grids, the names being followed, a parameter met. */
interface Reader {
  readonly file: ts.SourceFile;
  readonly grids: ReadonlySet<string>;
  readonly reading: Set<string>;
  parameter: boolean;
}

const OR_LIKE = [
  ts.SyntaxKind.QuestionQuestionToken,
  ts.SyntaxKind.BarBarToken,
  ts.SyntaxKind.AmpersandAmpersandToken,
];

/** A node that is what its expression is: a parenthesis, a cast, a spread, a property's owner. */
function isTransparent(
  node: ts.Node,
): node is
  | ts.JsxExpression
  | ts.ParenthesizedExpression
  | ts.AsExpression
  | ts.NonNullExpression
  | ts.SatisfiesExpression
  | ts.SpreadElement
  | ts.SpreadAssignment
  | ts.PropertyAccessExpression {
  return (
    ts.isJsxExpression(node) ||
    ts.isParenthesizedExpression(node) ||
    ts.isAsExpression(node) ||
    ts.isNonNullExpression(node) ||
    ts.isSatisfiesExpression(node) ||
    ts.isSpreadElement(node) ||
    ts.isSpreadAssignment(node) ||
    ts.isPropertyAccessExpression(node)
  );
}

/** Whether an expression is a grid the list checks, by its shape. */
function readsGrid(node: ts.Node | undefined, reader: Reader): boolean {
  if (node === undefined) {
    return false;
  }
  if (isTransparent(node)) {
    return readsGrid(node.expression, reader);
  }
  if (ts.isConditionalExpression(node)) {
    return readsGrid(node.whenTrue, reader) && readsGrid(node.whenFalse, reader);
  }
  if (ts.isBinaryExpression(node)) {
    return (
      OR_LIKE.includes(node.operatorToken.kind) &&
      readsGrid(node.left, reader) &&
      readsGrid(node.right, reader)
    );
  }
  if (ts.isArrayLiteralExpression(node) || ts.isObjectLiteralExpression(node)) {
    return readsLiteral(node, reader);
  }
  if (ts.isCallExpression(node) || ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
    return readsCall(node, reader);
  }
  return ts.isIdentifier(node) && readsName(node, reader);
}

/** A list of spreads of grids; an object whose spreads and whose `columns` are grids. */
function readsLiteral(
  node: ts.ArrayLiteralExpression | ts.ObjectLiteralExpression,
  reader: Reader,
): boolean {
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.every(
      (element) => ts.isSpreadElement(element) && readsGrid(element, reader),
    );
  }
  const columns = node.properties.find(
    (property): property is ts.PropertyAssignment =>
      ts.isPropertyAssignment(property) && property.name.getText(reader.file) === "columns",
  );
  const spreads = node.properties.filter(ts.isSpreadAssignment);
  return (
    (columns !== undefined || spreads.length > 0) &&
    spreads.every((spread) => readsGrid(spread, reader)) &&
    (columns === undefined || readsGrid(columns.initializer, reader))
  );
}

/** A function, by what it returns; a call: of a grid of the list, of `useMemo` (its function), of a wrapper (its config). */
function readsCall(
  node: ts.CallExpression | ts.ArrowFunction | ts.FunctionExpression,
  reader: Reader,
): boolean {
  if (!ts.isCallExpression(node)) {
    const results = returned(node);
    return results.length > 0 && results.every((result) => readsGrid(result, reader));
  }
  const name = root(node.expression);
  if (name !== undefined && reader.grids.has(name)) {
    return true;
  }
  if (name === "useMemo") {
    return readsGrid(node.arguments[0], reader);
  }
  const wrapped = name === undefined ? undefined : WRAPPERS.get(name);
  if (wrapped !== undefined) {
    return readsGrid(node.arguments[wrapped], reader);
  }
  if (name !== undefined && ts.isIdentifier(node.expression)) {
    reader.parameter ||=
      scoped(name, node.expression) === undefined && isParameter(name, node.expression);
  }
  return false;
}

/** A name: of the list, or bound in the source and followed, or a parameter. */
function readsName(node: ts.Identifier, reader: Reader): boolean {
  if (reader.grids.has(node.text)) {
    return true;
  }
  const bound = scoped(node.text, node);
  if (bound === undefined) {
    reader.parameter ||= isParameter(node.text, node);
    return false;
  }
  if (reader.reading.has(node.text)) {
    return false;
  }
  reader.reading.add(node.text);
  const result = readsGrid(bound, reader);
  reader.reading.delete(node.text);
  return result;
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
    for (const other of [
      "commandColumns",
      "KEPT_HEADING",
      "RATE_HEADINGS",
      "estimateReference",
      "catalogue",
    ]) {
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
    // A part that holds columns and is no grid, beside one that is, or around it.
    for (const config of [
      "{ columns: [...userGrid.columns, ...commandColumns()] }",
      "{ ...userGrid(true), columns: [...commandColumns()] }",
      "wrap(NEW, userGrid)",
      "useMemo(() => newGrid(x), [userGrid])",
      "a ?? NEW",
      "a || NEW",
    ]) {
      expect(unlisted(`<DenseGrid config={${config}} />`, known), config).toHaveLength(1);
    }
    // And the forms that are grids.
    for (const config of [
      "{ columns: [...userGrid.columns] }",
      "{ ...userGrid(true), key: 'x' }",
      "withDifference(userGrid(x), difference)",
      "userGrid ?? userGrid",
    ]) {
      expect(unlisted(`<DenseGrid config={${config}} />`, known), config).toEqual([]);
    }
  });

  it("lets a config received as a parameter stand for a grid the source holds", () => {
    const known = new Set(["userGrid"]);
    const make =
      "function G({ make }) { const c = useMemo(() => make(1), [make]); return <DenseGrid config={c} />; }";
    expect(unlisted(`${make}\nconst a = userGrid;`, known)).toEqual([]);
    expect(unlisted(make, known)).toHaveLength(1);
  });
});
