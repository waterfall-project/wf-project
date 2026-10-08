// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createRequire } from "node:module";

import { expect, type Locator, type Page, type Request, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated } from "./hydration";
import { rowAt, scrollToPosition } from "./scroll";

// The fake back serves the first example of `listNodes`, the structure of the witness at the sizes
// of §4.6.2, its core first (#376), which the journeys read by marks the generator writes
// (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py): rows 28 to 30, the first
// lines drawn after the core, « Heures d'ingénierie », « Heures de mise en service » and
// « Matériel », past the rows in view as the grid opens. A block pasted is asked
// of `previewPaste`, whose first example the fake back serves whatever is sent — the three rows
// accepted, none refused (`paste_plan`) —, and applied by `applyPaste`, whose first example is
// those three rows written (`paste_applied`). What the front sends is read in the server action
// the browser posts; what the grid does with a plan that refuses a row is proven on its own
// example by the tests of the grid (`paste.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const LINE_4 = "01926f3a-7c00-7000-8000-000100000028";
const FIRST = 28;

// The columns the journeys read, by their heading (`columnsOf`).
const COLUMNS = {
  label: "Libellé",
  quantity: "Qté",
  reference: "Montant (année de réf.)",
} as const;

const READ = ["Heures d'ingénierie", "Heures de mise en service", "Matériel"];

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
 * The labels of the rows 28 to 30 — by the position each cell carries, for the report, a modal
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
 * Open the estimate hydrated, scrolled to the row 28, its label active; the grid, and where its
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

/** The violations of the rules of axe, WCAG A and AA, on an element of the page. */
async function axeViolations(page: Page, selector: string): Promise<string[]> {
  const require = createRequire(import.meta.url);
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  return page.evaluate(async (scope) => {
    const axe = (window as unknown as { axe: typeof import("axe-core") }).axe;
    const tags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
    const results = await axe.run(scope, { runOnly: { type: "tag", values: tags } });
    return results.violations.map((violation) => violation.id);
  }, selector);
}

test("a block of three rows and four columns pasted from a spreadsheet produces a report before writing, then the three rows expected once confirmed [WF-IHM-0050-A]", async ({
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
    target_node_id: LINE_4,
    target_column: "label",
    rows: BLOCK,
  });
  // Nothing written before the confirmation; the report is accessible, contrast included.
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page)).toEqual(READ);
  expect(await axeViolations(page, '[role="dialog"]')).toEqual([]);

  await dialog.getByRole("button", { name: "Appliquer le collage" }).click();
  await expect(dialog).toHaveCount(0);
  // One operation: the plan confirmed, with the version of the structure read.
  expect(argumentsWith(posted, "paste_id")?.[1]).toEqual({
    paste_id: "01926f3a-7c00-7000-8000-000000000991",
    confirmed: true,
    lock_version: 1,
  });
  // The three rows the server wrote, in place of those read; the focus back on the cell.
  await expect(cellAt(grid, FIRST, at.label)).toHaveText("Heures de câblage et repérage");
  expect(await labels(page)).toEqual([
    "Heures de câblage et repérage",
    "Heures d'essais",
    "Matériel de câblage",
  ]);
  await expect(cellAt(grid, FIRST + 2, at.quantity)).toHaveText("24");
  await expect(cellAt(grid, FIRST + 2, at.reference)).toHaveText(/^42\s379,44/);
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
    target_node_id: LINE_4,
    target_column: "label",
    rows: unknown,
  });
  // Abandoned, by Escape: nothing more is asked, and no row changes.
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(cellAt(grid, FIRST, at.label)).toBeFocused();
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page)).toEqual(READ);
  await expect(cellAt(grid, FIRST + 2, at.quantity)).toHaveText("2");
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
