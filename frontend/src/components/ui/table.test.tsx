// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./table";

/** The opening tag of the container a table is drawn in. */
function containerOf(markup: string): string {
  return /<div[^>]*data-slot="table-container"[^>]*>/.exec(markup)?.[0] ?? "";
}

/** A table of one cell, with the props given. */
function table(props: { readonly list?: string }): string {
  return renderToStaticMarkup(
    <Table aria-label="Permissions" {...props}>
      <TableBody>
        <TableRow>
          <TableCell>users.read</TableCell>
        </TableRow>
      </TableBody>
    </Table>,
  );
}

describe("Table", () => {
  it("makes the container of a list a group named after it, in the order of the keyboard, its focus an outline inside its edge", () => {
    const container = containerOf(table({ list: "Permissions" }));
    expect(container).toContain('role="group"');
    expect(container).toContain('aria-label="Permissions"');
    expect(container).toContain('tabindex="0"');
    expect(container).toContain("focus-visible:outline-2");
    expect(container).toContain("focus-visible:-outline-offset-2");
  });

  it("gives the container of a dense grid no role, no name and no place in the order of the keyboard", () => {
    const container = containerOf(table({}));
    expect(container).toContain('data-slot="table-container"');
    expect(container).not.toContain("role=");
    expect(container).not.toContain("aria-label=");
    expect(container).not.toContain("tabindex=");
  });

  it("draws a simple table in the style of the grids: their text, their header, a line under each row and none between the columns [WF-IHM-0060-A]", () => {
    // US-2080, #3088, #3090: the permissions of the roles, the bounds of the risks, the thresholds
    // of the indicators, the history of the revisions, the journal of the imports.
    const markup = renderToStaticMarkup(
      <Table aria-label="Permissions">
        <TableHeader>
          <TableRow>
            <TableHead>Fonction</TableHead>
            <TableHead>Lecture</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableHead scope="row">Utilisateurs</TableHead>
            <TableCell>oui</TableCell>
            <TableCell>non</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    );
    const tableTag = /<table[^>]*>/.exec(markup)?.[0] ?? "";
    expect(tableTag).toContain("text-xs");
    expect(tableTag).not.toContain("text-sm");
    const cells = [...markup.matchAll(/<t[hd][^>]*class="([^"]*)"/g)].map(
      (match) => match[1] ?? "",
    );
    expect(cells).toHaveLength(5);
    for (const classes of cells) {
      expect(classes).toContain("border-b");
      expect(classes).not.toMatch(/border-r|border-l/);
    }
    // The header of a column at the height of that of a grid, on the muted background.
    expect(cells[0]).toContain("in-[thead]:h-8");
    expect(cells[0]).toContain("in-[thead]:bg-muted");
  });
});
