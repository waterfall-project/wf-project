// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated } from "./hydration";
import { rowAt } from "./scroll";

// The journeys that write read the amendment 2 (US-0500), a differential not merged of the current
// revision, whose estimate is entered whatever the state of the project (WF-DEV-0050), on its
// nodes, `nodes_amendment`, nine rows of the tree: row 7, the line « Assistance à la reprise des
// essais », added by the amendment, of labour, 40 hours; row 5, the summary « Essais sur site »,
// whose figures the server computes. A cell validated is written by `updateEstimateLine`, whose
// `amendment` example the fake back serves on the path of the amendment whatever was written
// (#1277): the line of row 7 with its hours at 48, nothing else changed — the fake back keeps
// nothing of what it is sent, so that each cell entered after it differs from the row answered, and
// is written. What the grid does with another answer is proven on its own examples by the tests of
// the grid (`entry.dom.test.tsx`).
//
// The provision of the risk (row 12 of the witness, whose quantity and unit disbursement the server
// computes) is read on the own estimate of the risk of the rewiring (`structure=`, the structure 204
// of `structures`), which the fake back serves the first example of `listNodes` at — only the paths
// of the differentials are served their own (#1219): the amendment holds no provision, and the
// examples of the writes of the other differentials are EP-16's.
//
// Every gesture is a key: the grid is reached by Tab, as a user who never takes the mouse.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
// The amendment 2 « reprise des essais », a differential of the current revision (`structures`).
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
// The own estimate of the risk of the rewiring: the nodes of the main structure, entered.
const OWN = "01926f3a-7c00-7000-8000-000000000204";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

// The columns the journeys enter and read, by their heading (`columnsOf`).
const COLUMNS = {
  label: "Libellé",
  category: "Catégorie",
  role: "Rôle",
  quantity: "Qté",
  hours: "Charge (h)",
  delay: "Délai de paiement (j)",
  reference: "Montant (année de réf.)",
} as const;

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * How long a check of absence waits, in milliseconds: a bound chosen, not an event — when nothing
 * should be sent, no request or response is there to wait for. It is longer than the round trip of
 * a write to the fake back, which a write sent late would have joined.
 */
const ABSENCE = 750;

/** Let the round trips under way come back, which a write sent late would have joined. */
async function settle(page: Page): Promise<void> {
  await page.evaluate(
    (wait) =>
      new Promise<void>((resolve) => {
        setTimeout(resolve, wait);
      }),
    ABSENCE,
  );
}

/** A screen of the journeys: its address, its grid, its columns by heading, the one it opens on. */
interface Screen<K extends string> {
  readonly path: string;
  readonly grid: string;
  readonly columns: Readonly<Record<K, string | RegExp>>;
  readonly first: NoInfer<K>;
}

const OWN_SCREEN: Screen<keyof typeof COLUMNS> = {
  path: `${ESTIMATE}?structure=${OWN}`,
  grid: "Grille de devis",
  columns: COLUMNS,
  first: "label",
};
const AMENDMENT_SCREEN: Screen<keyof typeof COLUMNS> = {
  ...OWN_SCREEN,
  path: `${ESTIMATE}?structure=${AMENDMENT}`,
};

/**
 * Open a screen hydrated, and reach the active cell of its grid by Tab alone, as the keyboard
 * does: past the shell and the bar of the grid, to the one stop of the grid (#182) — each stop a
 * round trip to the browser, which the journey is given the time of (`test.slow`). The columns are
 * those of the grid, by their heading.
 */
async function tabIntoGrid<K extends string>(
  page: Page,
  screen: Screen<K>,
): Promise<{ readonly grid: Locator; readonly at: Readonly<Record<K, number>> }> {
  test.slow();
  await openHydrated(page, screen.path);
  const grid = page.getByRole("treegrid", { name: screen.grid });
  const active = grid.locator('td[tabindex="0"]');
  await expect(active).toHaveCount(1);
  await expect
    .poll(
      async () => {
        await page.keyboard.press("Tab");
        return active.evaluate((element) => element === document.activeElement);
      },
      { intervals: [0], timeout: 30_000 },
    )
    .toBe(true);
  const at = await columnsOf(grid, screen.columns);
  await expect(cellAt(grid, 1, at[screen.first])).toBeFocused();
  return { grid, at };
}

/** The provision of the core, of the witness. */
const PROVISION = 12;
/** The line added by the amendment, and the summary it adds, whose figures the server computes. */
const LINE = 7;
const AMENDMENT_LINE = LINE;
const SUMMARY = 5;

/** Press keys, one after the other. */
async function press(page: Page, ...keys: readonly string[]): Promise<void> {
  for (const key of keys) {
    await page.keyboard.press(key);
  }
}

/** A key pressed as many times as there are columns from one to another. */
function times(key: string, count: number): string[] {
  return Array.from({ length: count }, () => key);
}

test("enters a whole line of the estimate without the mouse — label, role, quantity, effort —, and the last cell validated places the cursor on the next row [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, AMENDMENT_SCREEN);
  // Each cell validated leaves by a server action of its own.
  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.headers()["next-action"] !== undefined) {
      writes.push(request.url());
    }
  });
  await press(page, ...times("ArrowDown", LINE - 1));
  await expect(cellAt(grid, LINE, at.label)).toBeFocused();

  // Typed, the label replaces the one read; Tab validates it and goes along the row.
  await page.keyboard.type("Heures de câblage");
  await page.keyboard.press("Tab");
  // The category of a line of labour is computed from its role (WF-DEV-0020): the cell is read
  // only, and the keyboard goes along the row to the role.
  await expect(cellAt(grid, LINE, at.role)).toBeFocused();
  // The role, from its list opened by Enter.
  await page.keyboard.press("Enter");
  await page.keyboard.type("Ingénieur");
  await expect(page.getByRole("combobox", { name: "Rôle" })).toHaveValue(
    "01926f3a-7c00-7000-8000-000000000451",
  );
  await page.keyboard.press("Tab");
  await expect(cellAt(grid, LINE, at.quantity)).toBeFocused();
  await page.keyboard.type("2");
  await page.keyboard.press("Tab");
  await page.keyboard.type("31,5");
  await page.keyboard.press("Enter");

  // The row below, at the cell the line was started from, in view.
  const next = cellAt(grid, LINE + 1, at.label);
  await expect(next).toBeFocused();
  await expect(next).toBeInViewport();
  // The four cells written, one after the other.
  await expect.poll(() => writes.length).toBe(4);
  // The line as the server last answered it — the fake back keeps nothing of what it is sent —,
  // in place of what was typed.
  await expect(rowAt(grid, LINE).getByRole("gridcell")).toHaveText([
    "+Ajouté",
    "25",
    "Assistance à la reprise des essais",
    "Mise en service",
    "Technicien de mise en service",
    "1",
    "48",
    "",
    "0",
    "",
    /3\s600,00$/,
    /3\s600,00$/,
  ]);
  // No refusal told.
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("leaves a cell at its value before when its entry under way is abandoned [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, AMENDMENT_SCREEN);
  await press(
    page,
    ...times("ArrowDown", AMENDMENT_LINE - 1),
    ...times("ArrowRight", at.hours - at.label),
  );
  const hours = cellAt(grid, AMENDMENT_LINE, at.hours);
  await expect(hours).toBeFocused();
  await page.keyboard.type("99");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("99");
  await page.keyboard.press("Escape");
  await expect(hours.getByRole("textbox")).toHaveCount(0);
  await expect(hours).toHaveText("40");
  await expect(hours).toBeFocused();
});

test("traverses the cells of a summary that its node does not accept or the server computes along its row, without entering them [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, AMENDMENT_SCREEN);
  await press(page, ...times("ArrowDown", SUMMARY - 1));
  await expect(rowAt(grid, SUMMARY)).toContainText("Essais sur site");
  await expect(cellAt(grid, SUMMARY, at.label)).toBeFocused();
  // From its label, Tab goes past its category, its role, its quantity and its effort, which its
  // node does not accept (#219) — a summary bears no line of its own —, past its payment delay,
  // which it does not carry (WF-DEV-0020, EP-14/L42s), and past its amounts, which the server
  // computes from its subordinates, to the next row. Its sub-project is a column hidden until shown
  // (US-0480).
  await press(page, "Enter", "Tab");
  await expect(cellAt(grid, SUMMARY + 1, at.label)).toBeFocused();
  for (const column of [at.category, at.role, at.quantity, at.hours, at.delay]) {
    await expect(cellAt(grid, SUMMARY, column)).toHaveAttribute("aria-readonly", "true");
  }
  await expect(grid.getByRole("textbox")).toHaveCount(0);
});

test("traverses the computed cells of a line entered along its row, without entering them [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, OWN_SCREEN);
  await press(page, ...times("ArrowDown", PROVISION - 1));
  await expect(rowAt(grid, PROVISION)).toContainText("Provision");
  await expect(cellAt(grid, PROVISION, at.label)).toBeFocused();
  // From its label, Tab goes past its quantity and its unit disbursement, which the server
  // computes, past its category, its role and its effort, which its node does not accept (#219),
  // past its payment delay, which it does not carry (WF-DEV-0020, EP-14/L42s), and past its
  // amounts, to the next row. Its sub-project, the one its risk designates (EP-14/L42p), is a
  // column hidden until shown (US-0480).
  await press(page, "Enter", "Tab");
  await expect(cellAt(grid, PROVISION + 1, at.label)).toBeFocused();
  for (const column of [at.category, at.role, at.quantity, at.hours, at.delay]) {
    await expect(cellAt(grid, PROVISION, column)).toHaveAttribute("aria-readonly", "true");
  }
  await expect(grid.getByRole("textbox")).toHaveCount(0);
});

test("opens the entry of the effort on a digit typed, and the refusal of the amount, with no field, on the same digit [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, AMENDMENT_SCREEN);
  await press(
    page,
    ...times("ArrowDown", AMENDMENT_LINE - 1),
    ...times("ArrowRight", at.hours - at.label),
  );
  const hours = cellAt(grid, AMENDMENT_LINE, at.hours);
  await expect(hours).toBeFocused();
  // The effort of a line of labour is entered: a digit opens its entry, with it.
  await page.keyboard.press("7");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("7");
  await page.keyboard.press("Escape");
  await expect(hours).toHaveText("40");
  // Its amount is computed: the arrows reach it, the same digit opens no field but its refusal.
  await press(page, ...times("ArrowRight", at.reference - at.hours));
  const amount = cellAt(grid, AMENDMENT_LINE, at.reference);
  await expect(amount).toBeFocused();
  await expect(amount).toHaveAttribute("aria-readonly", "true");
  await page.keyboard.press("7");
  await expect(page.getByRole("dialog", { name: "Valeur calculée" })).toBeVisible();
  await expect(grid.getByRole("textbox")).toHaveCount(0);
});

// The remaining to commit of the same revision is entered where the estimate of its main structure
// is not: the main structure lists `edit_remaining` available (WF-RAE-0040). Row 10 is a line of labour,
// « Raccordement des borniers » (`test_the_marks_the_journeys_read`); its figures are re-estimated
// by `setLineRemaining`, whose first example the fake back serves whatever was written.
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const REMAINING_LINE = 10;

test("re-estimates the figures of a line of the remaining to commit from the keyboard, the entry abandoned leaving the figure as it was, the entry validated writing it [WF-IHM-0040-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page, {
    path: REMAINING,
    grid: "Grille de reste à engager",
    // « Charge (h) » alone: the column of the review before is headed the same, and goes on.
    columns: { label: "Libellé", hours: /^Charge \(h\)$/ },
    first: "label",
  });
  const writes: string[] = [];
  page.on("request", (request) => {
    // A write is a server action (the header `next-action`) whose body carries the version of the
    // node it changes (`lock_version`, in the body of `setLineRemaining`); the read of the totals
    // after it, another action, carries none. This reads the body of the action, and is kept to it.
    const body = request.method() === "POST" ? request.postData() : null;
    if (body?.includes("lock_version") === true && request.headers()["next-action"] !== undefined) {
      writes.push(request.url());
    }
  });

  // A key typed opens the entry of the effort, with it; abandoned, the effort is as it was.
  await press(
    page,
    ...times("ArrowDown", REMAINING_LINE - 1),
    ...times("ArrowRight", at.hours - at.label),
  );
  const hours = cellAt(grid, REMAINING_LINE, at.hours);
  await expect(hours).toBeFocused();
  const before = await hours.innerText();
  await page.keyboard.press("7");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("7");
  await page.keyboard.press("Escape");
  await expect(hours.getByRole("textbox")).toHaveCount(0);
  await expect(hours).toHaveText(before);

  // Validated by Tab, the effort is written once, by the Tab and not by the Escape before it, the
  // entry closed and no refusal told.
  await page.keyboard.press("7");
  await page.keyboard.type("1,5");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("71,5");
  // Nothing was written by the Escape, nor by the typing: a write is a round trip, which a check
  // made at once would not wait for.
  await settle(page);
  expect(writes).toEqual([]);
  await page.keyboard.press("Tab");
  await expect.poll(() => writes.length).toBe(1);
  await expect(hours.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  // And only one: a second write would come later, from the entry validated.
  await settle(page);
  expect(writes).toHaveLength(1);
});
