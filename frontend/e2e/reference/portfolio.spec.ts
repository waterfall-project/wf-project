// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The portfolio of three hundred projects, against the service, on the reference set restored
 * (US-2950/L3, `make e2e-reference`). `../portfolio.spec.ts` reads the same screen against the fake
 * back, whose first example answers whatever is asked, with the values of `fixtures/api/volume/`;
 * the set engendered never holds those values (US-2950: « le témoin reste l'oracle des valeurs »).
 * What these paths affirm is what does not hold to a value: the count of the projects, the pages
 * the server cuts them in, the filters that narrow them, the order it sorts them in — each read
 * from what the screen says of itself and compared with its other readings, never with a label or
 * a number expected of the fake back. They play as the manager of their worker, who sees every
 * project of the portfolio.
 */
import { expect, type Locator, type Page } from "@playwright/test";

import { WORKING } from "../bounds";
import { test } from "../mode";

const PROJECTS = "/portfolio/projects";
/** The three states a portfolio retains: the set holds its three hundred projects among them. */
const ALL_STATES = `${PROJECTS}?states=in_progress%2Cpricing%2Ccompleted`;
/** The projects of the set, at least: three hundred, and the witness the set starts from. */
const SET = 300;

/** The grid of the projects of the portfolio. */
function gridOf(page: Page): Locator {
  return page.getByRole("grid", { name: "Projets du portefeuille" });
}

/**
 * The number of projects the totals row of the grid says it retains; none when the header says the
 * perimeter holds none (no totals row is drawn for an empty list).
 */
async function retained(page: Page): Promise<number> {
  const cell = gridOf(page).getByRole("gridcell", { name: /^\d+ projets? retenus?$/ });
  const none = page.getByRole("main").getByText(/· aucun projet ·/);
  await expect(cell.or(none)).toHaveCount(1, { timeout: WORKING });
  if ((await cell.count()) === 0) return 0;
  const name = (await cell.getAttribute("aria-label")) ?? (await cell.innerText());
  return Number(/\d+/.exec(name)?.[0]);
}

/**
 * The rows the grid holds for its page, as it says them (`aria-rowcount`, the header and the totals
 * row apart): the grid renders only the rows in view, so the rows read are fewer than the page.
 */
async function pageRows(page: Page): Promise<number> {
  const count = await gridOf(page).getAttribute("aria-rowcount");
  return Number(count) - 2;
}

/** The codes of the rows the grid shows, in the order it shows them. */
async function codes(page: Page): Promise<string[]> {
  const grid = gridOf(page);
  await expect(grid.getByRole("row").nth(2)).toBeVisible({ timeout: WORKING });
  const cells = await grid.getByRole("gridcell", { name: /^[A-Z]+-\d+$/ }).allInnerTexts();
  return cells.map((text) => text.trim());
}

/**
 * Whether the order of the characters, which `sort` follows, is the order the server gives for these
 * codes. The collation of PostgreSQL may weigh the dash and the case apart, but it orders alike the
 * codes of three capital letters, a dash and digits, where each prefix keeps one width of digits
 * (`PRJ-001`, `REF-0001`): the letters decide before the dash, and the digits of one width compare
 * as numbers.
 */
function collationSafe(read: string[]): boolean {
  const widths = new Map<string, Set<number>>();
  for (const code of read) {
    const [prefix = "", digits = ""] = code.split("-");
    if (!/^[A-Z]{3}$/.test(prefix) || !/^\d+$/.test(digits)) return false;
    widths.set(prefix, (widths.get(prefix) ?? new Set<number>()).add(digits.length));
  }
  return [...widths.values()].every((set) => set.size === 1);
}

/** The rows of the grid that are projects: those with a code, the totals row left out. */
function projectRows(page: Page): Locator {
  return gridOf(page)
    .getByRole("row")
    .filter({ has: page.getByRole("gridcell", { name: /^[A-Z]+-\d+$/ }) });
}

/** The rows of a page and the rows shown, as the pages of the grid say them: « 51–100 sur 300 ». */
async function range(page: Page): Promise<{ from: number; to: number; of: number }> {
  const text = page.getByText(/^\d+–\d+ sur \d+$/);
  await expect(text).toBeVisible({ timeout: WORKING });
  const [from, to, of] = (await text.innerText()).match(/\d+/g)?.map(Number) ?? [];
  return { from: from ?? 0, to: to ?? 0, of: of ?? 0 };
}

test("reads the three hundred projects of the set: the count its header, its totals row and its pages agree on [US-2950]", async ({
  page,
}) => {
  test.slow();
  await page.goto(ALL_STATES);
  const total = await retained(page);
  expect(total).toBeGreaterThanOrEqual(SET);
  // The pages say the same count, and the first holds the first rows of it.
  const first = await range(page);
  expect(first.from).toBe(1);
  expect(first.of).toBe(total);
  expect(first.to).toBeLessThan(total);
  const pages = page.getByRole("navigation", { name: "Pages des projets" });
  await expect(pages).toContainText(`Page 1 sur ${String(Math.ceil(total / first.to))}`);
  // The perimeter by default, in progress and in pricing, is a part of it, whose count its header
  // and its totals row both say.
  await page.goto(PROJECTS);
  const perimeter = await retained(page);
  expect(perimeter).toBeLessThan(total);
  await expect(page.getByRole("main")).toContainText(`· ${String(perimeter)} projets ·`, {
    timeout: WORKING,
  });
});

test("turns the pages of the three hundred projects, each page the next rows of a list that no row is in twice [US-2950]", async ({
  page,
}) => {
  test.slow();
  const sorted = `${ALL_STATES}&sort_by=code&sort_order=asc`;
  await page.goto(sorted);
  const total = await retained(page);
  const size = (await range(page)).to;
  const last = Math.ceil(total / size);
  const pages = page.getByRole("navigation", { name: "Pages des projets" });
  const first = await codes(page);
  // The page is as long as the server cut it, and shorter than the list: there are pages to turn.
  // The codes read are those in view (the grid renders no more), the rows the grid holds are counted.
  expect(size).toBeLessThan(total);
  expect(await pageRows(page)).toBe(size);
  await expect(pages.getByRole("link", { name: /^Précédent/ })).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  // The second page, by « Suivant »: its range and its page, and none of the rows of the first.
  await pages.getByRole("link", { name: /^Suivant/ }).click();
  await expect(page).toHaveURL(new RegExp(`offset=${String(size)}`), { timeout: WORKING });
  await expect(pages).toContainText(`Page 2 sur ${String(last)}`, { timeout: WORKING });
  await expect(
    page.getByText(`${String(size + 1)}–${String(2 * size)} sur ${String(total)}`),
  ).toBeVisible();
  expect(await pageRows(page)).toBe(size);
  const second = await codes(page);
  expect(second.filter((code) => first.includes(code))).toEqual([]);
  // The last page, asked by its address: the rows left, and « Suivant » inert.
  await page.goto(`${sorted}&offset=${String((last - 1) * size)}`);
  await expect(pages).toContainText(`Page ${String(last)} sur ${String(last)}`, {
    timeout: WORKING,
  });
  await expect(pages.getByRole("link", { name: /^Suivant/ })).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  await expect(
    page.getByText(`${String((last - 1) * size + 1)}–${String(total)} sur ${String(total)}`),
  ).toBeVisible();
  expect(await pageRows(page)).toBe(total - (last - 1) * size);
});

test("sorts the three hundred projects by the server: a list the order of which follows the sort, and the other way round [US-2950]", async ({
  page,
}) => {
  test.slow();
  await page.goto(`${ALL_STATES}&sort_by=code&sort_order=asc`);
  const ascending = await codes(page);
  await page.goto(`${ALL_STATES}&sort_by=code&sort_order=desc`);
  await expect(gridOf(page).getByRole("columnheader", { name: "Code" })).toHaveAttribute(
    "aria-sort",
    "descending",
    { timeout: WORKING },
  );
  const descending = await codes(page);
  expect(ascending.length).toBeGreaterThan(1);
  expect(descending.length).toBeGreaterThan(1);
  // Each list is in the order it was asked in; the two lists are not the same one. `sort` follows
  // the order of the characters, the server that of the collation of PostgreSQL: they agree on the
  // codes of the set, which the lists are asserted to have the shape of.
  expect(collationSafe(ascending)).toBe(true);
  expect(collationSafe(descending)).toBe(true);
  expect(ascending).toEqual([...ascending].sort());
  expect(descending).toEqual([...descending].sort().reverse());
  expect(descending[0]).not.toBe(ascending[0]);
});

test("filters the three hundred projects by the server: a state added widens the list, a zone keeps a part of it [US-2950]", async ({
  page,
}) => {
  test.slow();
  await page.goto(PROJECTS);
  const perimeter = await retained(page);
  // The projects completed, added to the perimeter: more of them; one state alone, fewer or as
  // many.
  await page.goto(ALL_STATES);
  expect(await retained(page)).toBeGreaterThan(perimeter);
  // The states are disjoint: the counts of each state alone sum to the count of the three together.
  const total = await retained(page);
  let sum = 0;
  for (const state of ["in_progress", "pricing", "completed"]) {
    await page.goto(`${PROJECTS}?states=${state}`);
    const alone = await retained(page);
    expect(alone).toBeLessThanOrEqual(total);
    sum += alone;
  }
  expect(sum).toBe(total);
  // The projects of which an index is nominal: a part of the perimeter, and every row the page shows
  // carries that zone, whatever the projects of the set are.
  await page.goto(`${PROJECTS}?zones=nominal`);
  const nominal = await retained(page);
  expect(nominal).toBeLessThanOrEqual(perimeter);
  expect(nominal).toBeGreaterThan(0);
  expect((await codes(page)).length).toBeGreaterThan(0);
  const rows = await projectRows(page).all();
  expect(rows.length).toBeGreaterThan(0);
  for (const row of rows) {
    await expect(row.getByRole("img", { name: "Nominal" }).first()).toBeVisible();
  }
});
