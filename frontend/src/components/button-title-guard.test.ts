// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the tooltips of the commands (US-0580, #1071): a button bears `CommandTooltip`, never
 * a `title`, which the browser shows late, unstyled, without the dark theme, and never on the focus
 * of the keyboard. The rule is in `docs/dev/README.md`, « Les infobulles des commandes »; nothing
 * else holds it: the sources are read, as the guard of `useId` reads them, here by the parser of
 * TypeScript, which tells an attribute of an element from a word of a comment or of a text.
 *
 * A button is what the user presses: a `<button>`, `Button` and the commands built on it
 * (`CellCommand`, `Command`), a switch, an item or a trigger of a menu, an element of the role
 * `button`, and a link drawn as a button (`buttonVariants`). The commands of objects, of the dialogs,
 * of the headers of the columns and of the computed values pass to `CommandTooltip` with US-0580/L2
 * (#1137): their files are listed here, a closed list that can only shrink — a file listed that
 * bears no `title` on a button any more fails the test too, to be taken off the list.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import ts from "typescript";
import { describe, expect, it } from "vitest";

const SOURCES = join(import.meta.dirname, "..");

/** The files whose buttons still bear a `title`, left to US-0580/L2 (#1137). */
const LEFT_TO_L2: readonly string[] = [
  "components/admin/role-commands.tsx",
  "components/admin/user-cells.tsx",
  "components/projects/subproject-commands.tsx",
  "components/reference/cell-command.tsx",
];

/** Every component of the front: the `.tsx` files of `src/`, tests left out. */
function components(): string[] {
  return readdirSync(SOURCES, { recursive: true, withFileTypes: true })
    .filter(
      (entry) => entry.isFile() && entry.name.endsWith(".tsx") && !entry.name.includes(".test."),
    )
    .map((entry) => join(entry.parentPath, entry.name));
}

/** The components that draw a button, by their name. */
const BUTTON_NAMES = /^(button|Button|CellCommand|Command|Switch|Toggle)$|(MenuItem|Trigger)$/;

/** The value of an attribute written as a string or as an expression, as written. */
function written(attribute: ts.JsxAttribute | undefined, file: ts.SourceFile): string {
  return attribute?.initializer?.getText(file) ?? "";
}

/** Whether an element is a button, by its name, its role or the classes of a button. */
function isButton(
  tag: string,
  attributes: ReadonlyMap<string, ts.JsxAttribute>,
  file: ts.SourceFile,
): boolean {
  return (
    BUTTON_NAMES.test(tag) ||
    /^["'{]*["']button["'][}]*$/.test(written(attributes.get("role"), file)) ||
    written(attributes.get("className"), file).includes("buttonVariants(")
  );
}

/** The buttons of a source that bear a `title`, each by its tag and its line. */
function titledButtons(source: string, name = "source.tsx"): string[] {
  const file = ts.createSourceFile(name, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const attributes = new Map(
        node.attributes.properties
          .filter(ts.isJsxAttribute)
          .map((attribute): [string, ts.JsxAttribute] => [attribute.name.getText(file), attribute]),
      );
      const tag = node.tagName.getText(file);
      if (attributes.has("title") && isButton(tag, attributes, file)) {
        const line = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1;
        found.push(`${tag}:${line.toString()}`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

describe("the buttons of the front", () => {
  const titled = components()
    .map((file): [string, string[]] => [
      relative(SOURCES, file),
      titledButtons(readFileSync(file, "utf-8"), file),
    ])
    .filter(([, buttons]) => buttons.length > 0);

  it("bear no title, the browser's tooltip, but CommandTooltip (US-0580)", () => {
    const offending = titled.filter(([file]) => !LEFT_TO_L2.includes(file));
    expect(offending).toEqual([]);
  });

  it("left to US-0580/L2 are those that still bear one: the list only shrinks (#1137)", () => {
    expect(titled.map(([file]) => file).sort()).toEqual([...LEFT_TO_L2].sort());
  });

  it("finds a title on a button, whatever draws it", () => {
    for (const button of [
      '<button type="button" title="x" />',
      "<Button title={name}>x</Button>",
      "<CellCommand title={unmet} />",
      "<ContextMenuItem title={t('x')} />",
      '<span role="button" title={x} />',
      "<Link href={href} title={x} className={buttonVariants({ size: 'sm' })} />",
    ]) {
      expect(titledButtons(button), button).toHaveLength(1);
    }
  });

  it("finds none on what is no button, nor in a comment or a text", () => {
    for (const plain of [
      "<PageHeader title={t('x')} />",
      "<span title={details}>x</span>",
      '<Input title={form} pattern="[0-9]+" />',
      "<p>{/* <Button title={x} /> */}a button with a title=</p>",
      "// <button title='x' />\nconst a = 1;",
    ]) {
      expect(titledButtons(plain), plain).toEqual([]);
    }
  });
});
