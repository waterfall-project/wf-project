// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, type Request, test } from "@playwright/test";

import { axeViolations } from "./axe";
import { columnsOf } from "./columns";
import { openHydrated } from "./hydration";
import { rowAt, scrollToPosition } from "./scroll";

// The block is pasted on the amendment 2 (US-0500), a differential not merged of the current
// revision, whose estimate is entered whatever the state of the project (WF-DEV-0050): the fake
// back serves its path the nodes `nodes_amendment`, nine rows of the tree, and the `amendment`
// examples of the paste (#1277). A block pasted is asked of `previewPaste`, whose example is the
// three rows accepted, none refused (`paste_plan_amendment`), and applied by `applyPaste`, whose
// example is those three rows written (`paste_applied_amendment`): the line « Assistance à la
// reprise des essais » (row 7, the node 1293) and the two rows under it, the task « Mise en
// service » and its line, which the answer names « Mise en service de l'installation » and
// « Mise en service et réception sur site ». What the front sends is read in the server action the
// browser posts; what the grid does with a plan that refuses a row is proven on its own example by
// the tests of the grid (`paste.dom.test.tsx`).
//
// Two journeys stay on the own estimate of the risk of the rewiring (`structure=`, the structure
// 204 of `structures`), which the fake back serves the first example of `listNodes` at, the
// structure of the witness at the sizes of §4.6.2, its core first (#376), and which the journeys
// read by marks the generator writes (`test_the_marks_the_journeys_read`,
// tools/tests/test_mockstructure.py): rows 28 to 30, « Heures d'ingénierie », « Heures de mise en
// service » and « Matériel ». The case of an unknown category and the one of a block too wide have
// no example of their own on the amendment, and need none: the front judges neither, and the
// examples of the other differentials, like those of the risks, are EP-16's.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

/** Where a journey pastes: the structure it reads, the node and the row of its active cell. */
interface Site {
  readonly structure: string;
  readonly node: string;
  readonly first: number;
  readonly read: readonly string[];
}

/** The amendment 2 « reprise des essais », a differential of the current revision. */
const AMENDMENT: Site = {
  structure: "01926f3a-7c00-7000-8000-000000000203",
  node: "01926f3a-7c00-7000-8000-000000001293",
  first: 7,
  read: ["Assistance à la reprise des essais", "Mise en service", "Mise en service sur site"],
};
/** The own estimate of the risk of the rewiring, a structure of the current revision. */
const OWN: Site = {
  structure: "01926f3a-7c00-7000-8000-000000000204",
  node: "01926f3a-7c00-7000-8000-000100000028",
  first: 28,
  read: ["Heures d'ingénierie", "Heures de mise en service", "Matériel"],
};

// The columns the journeys read, by their heading (`columnsOf`).
const COLUMNS = {
  label: "Libellé",
  quantity: "Qté",
  reference: "Montant (année de réf.)",
} as const;

// A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
// copies it. The one pasted on the amendment is the one its example names (`paste_plan_amendment`):
// the second row is the task, which takes its label and whose empty cells write nothing.
const BLOCK = [
  ["Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"],
  ["Heures d'essais", "Mise en service", "Technicien de mise en service", "1"],
  ["Matériel de câblage", "Matériel électrique", "", "24"],
];
const AMENDMENT_BLOCK = [
  [
    "Assistance à la reprise des essais de câblage",
    "Mise en service",
    "Technicien de mise en service",
    "2",
  ],
  ["Mise en service de l'installation", "", "", ""],
  [
    "Mise en service et réception sur site",
    "Mise en service",
    "Technicien de mise en service",
    "1",
  ],
];

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * The labels of the three rows from the first of the site — by the position each cell carries, for
 * the report, a modal dialog, hides the grid from the roles while it is open.
 */
function labels(page: Page, site: Site): Promise<string[]> {
  return Promise.all(
    [site.first - 1, site.first, site.first + 1].map((index) =>
      page.locator(`td[data-row="${index.toString()}"][data-column="label"]`).innerText(),
    ),
  );
}

/**
 * Open the estimate of the site hydrated, scrolled to its first row, its label active; the grid,
 * and where its columns are.
 */
async function openOnFirstLine(
  page: Page,
  site: Site,
): Promise<{
  readonly grid: Locator;
  readonly at: Readonly<Record<keyof typeof COLUMNS, number>>;
}> {
  await openHydrated(page, `${ESTIMATE}?structure=${site.structure}`);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, COLUMNS);
  const label = (await scrollToPosition(grid, site.first)).getByRole("gridcell").nth(at.label);
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

test("a block of three rows and four columns pasted from a spreadsheet produces a report before writing, then the three rows expected once confirmed [WF-IHM-0050-A]", async ({
  page,
}) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page, AMENDMENT);
  await paste(page, AMENDMENT_BLOCK);

  const dialog = page.getByRole("dialog", { name: "Coller depuis un tableur" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("3 lignes seront écrites.");
  await expect(dialog).toContainText("Aucune ligne n’est refusée.");
  // The block as copied, from the node and the column of the active cell.
  expect(argumentsWith(posted, "target_column")?.[1]).toEqual({
    target_node_id: AMENDMENT.node,
    target_column: "label",
    rows: AMENDMENT_BLOCK,
  });
  // Nothing written before the confirmation; the report is accessible, contrast included.
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page, AMENDMENT)).toEqual(AMENDMENT.read);
  expect(await axeViolations(page, '[role="dialog"]')).toEqual([]);

  await dialog.getByRole("button", { name: "Appliquer le collage" }).click();
  await expect(dialog).toHaveCount(0);
  // One operation: the plan confirmed, with the version of the structure read, the amendment's.
  expect(argumentsWith(posted, "paste_id")?.[1]).toEqual({
    paste_id: "01926f3a-7c00-7000-8000-000000000994",
    confirmed: true,
    lock_version: 2,
  });
  // The three rows the server wrote, in place of those read; the focus back on the cell.
  const first = AMENDMENT.first;
  await expect(cellAt(grid, first, at.label)).toHaveText(
    "Assistance à la reprise des essais de câblage",
  );
  expect(await labels(page, AMENDMENT)).toEqual([
    "Assistance à la reprise des essais de câblage",
    "Mise en service de l'installation",
    "Mise en service et réception sur site",
  ]);
  await expect(cellAt(grid, first, at.quantity)).toHaveText("2");
  await expect(cellAt(grid, first, at.reference)).toHaveText(/^7\s200,00/);
  await expect(cellAt(grid, first + 2, at.quantity)).toHaveText("1");
  await expect(cellAt(grid, first + 2, at.reference)).toHaveText(/^9\s000,00/);
  await expect(cellAt(grid, first, at.label)).toBeFocused();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("a block whose cell names an unknown category is sent as copied for the server to judge, and modifies no row once abandoned [WF-IHM-0050-A]", async ({
  page,
}) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page, OWN);
  const unknown = [BLOCK[0] ?? [], ["Heures d'essais", "Essais", "", "1"], BLOCK[2] ?? []];
  await paste(page, unknown);

  const dialog = page.getByRole("dialog", { name: "Coller depuis un tableur" });
  await expect(dialog).toContainText("lignes seront écrites.");
  // The front judges nothing of the block: the unknown category leaves as it was copied.
  expect(argumentsWith(posted, "target_column")?.[1]).toEqual({
    target_node_id: OWN.node,
    target_column: "label",
    rows: unknown,
  });
  // Abandoned, by Escape: nothing more is asked, and no row changes.
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(cellAt(grid, OWN.first, at.label)).toBeFocused();
  expect(argumentsWith(posted, "paste_id")).toBeUndefined();
  expect(await labels(page, OWN)).toEqual(OWN.read);
  await expect(cellAt(grid, OWN.first + 2, at.quantity)).toHaveText("2");
});

test("a paste wider than the grid is refused, saying so [WF-IHM-0050-A]", async ({ page }) => {
  const posted = actions(page);
  const { grid, at } = await openOnFirstLine(page, OWN);
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
  expect(await labels(page, OWN)).toEqual(OWN.read);
  await expect(cellAt(grid, OWN.first, at.label)).toBeFocused();
});
