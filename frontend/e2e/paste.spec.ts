// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, type Request, test } from "@playwright/test";

import { axeViolations } from "./axe";
import { columnsOf } from "./columns";
import { openHydrated } from "./hydration";
import { rowAt, scrollToPosition } from "./scroll";

// The estimate is read on the amendment 2 its address names (`structure=`, US-0500), a differential
// not merged of the current revision, at its version 2, which lists the estimate entered whatever
// the state of the project (`structures`), where the main structure of the project in progress
// lists it read only (#1176). The fake back serves the nodes of the structure its path names
// (#1219): the installation on site read on the amendment, `nodes_amendment`, nine rows of the tree,
// which the journeys read by their position — rows 7 to 9, « Assistance à la reprise des essais »,
// « Mise en service » and « Mise en service sur site », the first a line added by the amendment,
// past the first rows. A block pasted is asked of `previewPaste`, whose first example the fake
// back serves whatever is sent — three rows accepted, none refused (`paste_plan`) —, and applied by
// `applyPaste`, whose first example is three lines of the witness written (`paste_applied`), which
// the amendment does not hold. What the front sends is read in the server action the browser posts —
// the node of the active cell, in the amendment, and its version; what the grid does with a plan
// that refuses a row, or with rows written, is proven on its own examples by the tests of the grid
// (`paste.dom.test.tsx`, `paste-applied.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The amendment 2 « reprise des essais », a differential of the current revision (`structures`).
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate?structure=${AMENDMENT}`;
// The line « Assistance à la reprise des essais » of the amendment (`nodes_amendment`), the node the
// block is pasted from, at the position FIRST among the rows.
const TARGET = "01926f3a-7c00-7000-8000-000000001293";
const FIRST = 7;

// The columns the journeys read, by their heading (`columnsOf`).
const COLUMNS = {
  label: "Libellé",
  quantity: "Qté",
  reference: "Montant (année de réf.)",
} as const;

const READ = ["Assistance à la reprise des essais", "Mise en service", "Mise en service sur site"];

// A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
// copies it.
const BLOCK = [
  ["Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"],
  ["Heures d'essais", "Mise en service", "Technicien de mise en service", "1"],
  ["Matériel de câblage", "Matériel électrique", "", "24"],
];

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * The labels of the rows 7 to 9 — by the position each cell carries, for the report, a modal
 * dialog, hides the grid from the roles while it is open.
 */
function labels(page: Page): Promise<string[]> {
  return Promise.all(
    [FIRST - 1, FIRST, FIRST + 1].map((index) =>
      page.locator(`td[data-row="${index.toString()}"][data-column="label"]`).innerText(),
    ),
  );
}

/**
 * Open the estimate hydrated, scrolled to the row 7, its label active; the grid, and where its
 * columns are.
 */
async function openOnFirstLine(page: Page): Promise<{
  readonly grid: Locator;
  readonly at: Readonly<Record<keyof typeof COLUMNS, number>>;
}> {
  await openHydrated(page, ESTIMATE);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, COLUMNS);
  const label = (await scrollToPosition(grid, FIRST)).getByRole("gridcell").nth(at.label);
  await label.click();
  await expect(label).toBeFocused();
  return { grid, at };
}

/**
 * Paste a block on the active cell, as a user does: the block copied into the clipboard of the
 * browser — by the journey, which the page never reads but at the event `paste` —, then Ctrl+V.
 */
async function paste(page: Page, block: readonly (readonly string[])[]): Promise<void> {
  const text = block.map((row) => `${row.join("\t")}\n`).join("");
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.evaluate((copied) => navigator.clipboard.writeText(copied), text);
  await page.keyboard.press("ControlOrMeta+V");
}

/** The server actions the page posts, as they leave: the arguments each carries, in their order. */
function actions(page: Page): Request[] {
  const posted: Request[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.headers()["next-action"] !== undefined) {
      posted.push(request);
    }
  });
  return posted;
}

/** The arguments of the server action that carried a field, if one did. */
function argumentsWith(posted: readonly Request[], field: string): unknown[] | undefined {
  const request = posted.find((each) => each.postData()?.includes(`"${field}"`) === true);
  const data = request?.postData();
  return data === null || data === undefined ? undefined : (JSON.parse(data) as unknown[]);
}

test("a block of three rows and four columns pasted from a spreadsheet produces a report before writing, then is written once confirmed, from the node of the amendment and its version", async ({
  page,
}) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page);
  await paste(page, BLOCK);

  const dialog = page.getByRole("dialog", { name: "Coller depuis un tableur" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("3 lignes seront écrites.");
  await expect(dialog).toContainText("Aucune ligne n’est refusée.");
  // The block as copied, from the node and the column of the active cell.
  expect(argumentsWith(posted, "target_column")?.[1]).toEqual({
    target_node_id: TARGET,
    target_column: "label",
    rows: BLOCK,
  });
  // Nothing written before the confirmation; the report is accessible, contrast included.
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page)).toEqual(READ);
  expect(await axeViolations(page, '[role="dialog"]')).toEqual([]);

  await dialog.getByRole("button", { name: "Appliquer le collage" }).click();
  await expect(dialog).toHaveCount(0);
  // One operation: the plan confirmed, with the version of the structure read, the amendment's.
  expect(argumentsWith(posted, "paste_id")?.[1]).toEqual({
    paste_id: "01926f3a-7c00-7000-8000-000000000991",
    confirmed: true,
    lock_version: 2,
  });
  // The rows the server wrote are three lines of the witness, which the amendment does not hold: the
  // rows read stay as they were — what the grid shows of rows written is proven on its own examples
  // (`paste-applied.dom.test.tsx`) —, the focus back on the cell.
  expect(await labels(page)).toEqual(READ);
  await expect(cellAt(grid, FIRST, at.label)).toBeFocused();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("a block whose cell names an unknown category is sent as copied for the server to judge, and modifies no row once abandoned [WF-IHM-0050-A]", async ({
  page,
}) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page);
  const unknown = [BLOCK[0] ?? [], ["Heures d'essais", "Essais", "", "1"], BLOCK[2] ?? []];
  await paste(page, unknown);

  const dialog = page.getByRole("dialog", { name: "Coller depuis un tableur" });
  await expect(dialog).toContainText("lignes seront écrites.");
  // The front judges nothing of the block: the unknown category leaves as it was copied.
  expect(argumentsWith(posted, "target_column")?.[1]).toEqual({
    target_node_id: TARGET,
    target_column: "label",
    rows: unknown,
  });
  // Abandoned, by Escape: nothing more is asked, and no row changes.
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(cellAt(grid, FIRST, at.label)).toBeFocused();
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page)).toEqual(READ);
  await expect(cellAt(grid, FIRST + 2, at.quantity)).toHaveText("1");
});

test("a paste wider than the grid is refused, saying so [WF-IHM-0050-A]", async ({ page }) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page);
  // Eighteen columns from the label, where a line has seventeen in the contract (#223, #424).
  await paste(
    page,
    BLOCK.map((row) => [...row, ...Array.from({ length: 14 }, () => "")]),
  );

  const alert = page.getByRole("main").getByRole("alert");
  await expect(alert).toContainText("Les données collées ont plus de colonnes que la grille.");
  await expect(alert).toContainText(
    "La grille accepte au plus 17 colonnes à partir de cette cellule.",
  );
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(argumentsWith(posted, "target_column")).toBeUndefined();
  expect(await labels(page)).toEqual(READ);
  await expect(cellAt(grid, FIRST, at.label)).toBeFocused();
});
