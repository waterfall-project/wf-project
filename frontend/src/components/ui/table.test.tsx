// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Table, TableBody, TableCell, TableRow } from "./table";

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
});
