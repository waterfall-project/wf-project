// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar of a grid in a tree that holds a thousand tasks, measured (US-2020, #3089): on the planning,
 * the estimate and the remaining to commit of the witness of volume (PRJ-001, which the fake back
 * serves with a thousand tasks), the bar keeps its height — the search, the filter, « Colonnes » and
 * « Arbre » stay in the window and under the pointer — at 1440 × 900 and in a large window; the
 * grid gives way, down to its floor, and stays in the window under the bar. The flat tables, one
 * of them with the panel of its filters, keep their bar too, « Colonnes » and the panel included. The grids of the other paths hold too
 * few rows to show the defect: the bar, which scrolls sideways, lost its least height and gave up
 * all the room the frame of a thousand rows would not.
 *
 * And the bar of every grid in one order (US-2080, decision of the author of 2026-11-14): the
 * commands of the screen, the search, « Filtres », « Colonnes », « Arbre », then undo and redo, no
 * number of rows in it (#3072); the chips of the filters on in the tint of the primary, in both
 * modes (#3077); the reason undo and redo wait for, read whole by a touch (#3150); and the pages of
 * a flat table at the right under it, in the size of its text, muted, « Précédent » and « Suivant »
 * in their place (#3073). Geometry and colours are measured, never compared as images.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The window of a portable, and a large one. */
const WINDOWS = [
  { width: 1440, height: 900 },
  { width: 3840, height: 2000 },
] as const;

/** The least height, in pixels, of a bar on one line: its buttons are 28 high, its search 28. */
const BAR_FLOOR = 28;

/** The rows a grid of the witness holds at least: a thousand tasks, and their header and totals. */
const VOLUME = 1000;

/** The grids of a thousand tasks, and the filter their bar holds beside the search. */
const TREES = [
  { address: path(`${REVISION}/planning`), filter: "Lot ou poste" },
  { address: path(`${REVISION}/estimate`), filter: "Lot ou poste" },
  { address: path(`${REVISION}/remaining`), filter: "Lot ou poste" },
] as const;

/** The flat tables, whose bar is folded over the panel of their filters. */
const OTHERS = ["/portfolio/projects", "/admin/users", "/admin/audit-log"] as const;

/** The actual costs of the witness, a flat table whose list the server pages. */
const COSTS = path(`${REVISION}/actual-costs`);

/** Open a screen in a window, until its first grid shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/** The height of the bar of the first grid of the screen, as laid out: its line, even under a panel. */
async function barHeight(page: Page): Promise<number> {
  const box = await page.locator("main [data-grid-toolbar]").first().boundingBox();
  return box?.height ?? 0;
}

/** The left edge of a control, as laid out. */
async function leftOf(control: Locator): Promise<number> {
  const box = await control.boundingBox();
  if (box === null) {
    throw new Error("a control of the bar is not laid out");
  }
  return box.x;
}

/** Each control at the right of the one before it on the line of the bar. */
async function expectLeftToRight(controls: readonly [string, Locator][], where: string) {
  const lefts = await Promise.all(controls.map(async ([, control]) => leftOf(control)));
  lefts.slice(1).forEach((left, at) => {
    const before = controls[at]?.[0] ?? "";
    const name = controls[at + 1]?.[0] ?? "";
    expect(left, `« ${name} » after « ${before} » in the bar of ${where}`).toBeGreaterThan(
      lefts[at] ?? Number.POSITIVE_INFINITY,
    );
  });
}

/** A computed style of a probe that bears classes of the charter, as the page draws them. */
async function drawn(page: Page, classes: string, property: "color" | "backgroundColor") {
  return page.evaluate(
    ([named, read]) => {
      const probe = document.createElement("span");
      probe.className = named;
      document.body.append(probe);
      const value = getComputedStyle(probe)[read];
      probe.remove();
      return value;
    },
    [classes, property] as const,
  );
}

for (const { address, filter } of TREES) {
  test(`${address}: the bar of a grid of a thousand tasks keeps its height, its search and its filter in reach, in the order of every grid [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const grid = page.locator("main [role='treegrid'], main [role='grid']").first();
      const rows = Number(await grid.getAttribute("aria-rowcount"));
      expect(rows, `the rows of the grid of ${where}`).toBeGreaterThanOrEqual(VOLUME);
      await expect(grid).toBeInViewport();
      const height = await barHeight(page);
      expect(height, `the height of the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const bar = page.locator("main [data-grid-toolbar]").first();
      const search = bar.getByRole("search");
      await expect(search).toBeVisible();
      await expect(search).toBeInViewport();
      await search.getByRole("searchbox").click({ trial: true });
      const controls: [string, Locator][] = [["Rechercher", search]];
      for (const name of [filter, "Colonnes", "Arbre"]) {
        const control = bar.getByRole("button", { name: new RegExp(name) });
        await expect(control, `« ${name} » of ${where}`).toBeVisible();
        await expect(control, `« ${name} » of ${where}`).toBeInViewport();
        await control.click({ trial: true });
        controls.push([name, control]);
      }
      // Undo and redo, where the grid enters a revision in progress, come last.
      const undo = bar.getByRole("button", { name: "Annuler", exact: true });
      if ((await undo.count()) > 0) {
        controls.push(["Annuler", undo]);
      }
      await expectLeftToRight(controls, where);
    }
  });
}

for (const address of OTHERS) {
  test(`${address}: the bar of a flat table keeps its height, its search, « Filtres » and « Colonnes » in this order, the panel of its filters in reach, and no number of rows [WF-IHM-0060-A] [WF-IHM-0130-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const bar = page.locator("main [data-grid-toolbar]").first();
      // The panel of the filters folds the bar into a frame that holds the line and the panel.
      const folded = await bar.evaluate((el) => el.parentElement?.hasAttribute("data-folded"));
      expect(folded, `the bar of ${where} is folded over its panel`).toBe(true);
      const height = await barHeight(page);
      expect(height, `the height of the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const search = bar.getByRole("search");
      await expect(search).toBeVisible();
      await expect(search).toBeInViewport();
      await search.getByRole("searchbox").click({ trial: true });
      // « Colonnes » and the button of the filters stay in the window and under the pointer, and
      // the panel the button opens shows in the window as well (#3118).
      const columns = bar.getByRole("button", { name: /^Colonnes/ });
      await expect(columns, `« Colonnes » of ${where}`).toBeVisible();
      await expect(columns, `« Colonnes » of ${where}`).toBeInViewport();
      await columns.click({ trial: true });
      const toggle = bar.getByRole("button", { name: /^Filtres( \(|$)/ });
      await expect(toggle, `« Filtres » of ${where}`).toBeInViewport();
      await expectLeftToRight(
        [
          ["Rechercher", search],
          ["Filtres", toggle],
          ["Colonnes", columns],
        ],
        where,
      );
      // The number of rows is said by the totals row alone (#3072).
      const caption = await page
        .locator("main tfoot tr")
        .first()
        .evaluate(
          (row) =>
            [...(row as HTMLTableRowElement).cells]
              .map((cell) => cell.textContent.trim())
              .find((text) => text !== "") ?? "",
        );
      expect(caption, `the totals row of ${where} says what it counts`).not.toBe("");
      await expect(bar, `the bar of ${where}`).not.toContainText(caption);
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      await expect(toggle).toHaveAttribute("aria-controls", /.+/);
      const panel = page.locator(`[id="${(await toggle.getAttribute("aria-controls")) ?? ""}"]`);
      await expect(panel, `the panel of the filters of ${where}`).toBeVisible();
      await expect(panel, `the panel of the filters of ${where}`).toBeInViewport();
    }
  });
}

for (const mode of ["light", "dark"] as const) {
  test.describe(`in ${mode} mode`, () => {
    test.use({ colorScheme: mode });

    test(`/admin/users: the chip of a filter on is drawn in the tint of the primary, its words and its cross [WF-IHM-0060-A]`, async ({
      page,
    }) => {
      const address = "/admin/users?is_active=true";
      await compile(page.request, "/admin/users");
      await open(page, address, WINDOWS[0]);
      const chips = page.getByRole("list", { name: "Filtres actifs" }).getByRole("listitem");
      await expect(chips).toHaveCount(1);
      const chip = chips.first();
      await expect(chip).toHaveText("État du compte : Actif");
      await expect(
        chip.getByRole("button", { name: "Retirer le filtre État du compte : Actif" }),
      ).toBeVisible();
      const style = await chip.evaluate((li) => {
        const computed = getComputedStyle(li);
        return { background: computed.backgroundColor, text: computed.color };
      });
      expect(style.background).toBe(await drawn(page, "bg-accent", "backgroundColor"));
      expect(style.text).toBe(await drawn(page, "text-primary", "color"));
      // The tint is no grey: the chip stands out of the muted surfaces it used to share.
      expect(style.background).not.toBe(await drawn(page, "bg-muted", "backgroundColor"));
    });
  });
}

test(`${COSTS}: the pages of a flat table are at the right under it, in the size of its text, muted, « Précédent » and « Suivant » in their place [WF-IHM-0060-A]`, async ({
  page,
}) => {
  await compile(page.request, COSTS);
  await open(page, COSTS, WINDOWS[0]);
  const grid = page.getByRole("grid", { name: "Coûts réels" });
  const nav = page.getByRole("navigation", { name: "Pages des coûts réels" });
  await expect(nav).toBeVisible();
  // The witness serves its costs on one page: both links are there, inert.
  for (const name of ["Précédent", "Suivant"]) {
    await expect(nav.getByRole("link", { name })).toHaveAttribute("aria-disabled", "true");
  }
  await expect(nav).toContainText(/Page 1 sur 1/);
  const range = page.getByText(/^\d+–\d+ sur \d+$/);
  await expect(range).toBeVisible();
  const line = nav.locator("xpath=..");
  const [frame, pages, holder, inset] = await Promise.all([
    grid.locator("xpath=..").boundingBox(),
    nav.boundingBox(),
    line.locator("xpath=..").boundingBox(),
    // The holder is the content of a card of work, which keeps its own padding at the right.
    line
      .locator("xpath=..")
      .evaluate((element) => Number.parseFloat(getComputedStyle(element).paddingRight)),
  ]);
  if (frame === null || pages === null || holder === null) {
    throw new Error("the grid or its pages are not laid out");
  }
  // Under the frame the table scrolls in, at the right of what holds them.
  expect(pages.y, "the pages under the table").toBeGreaterThanOrEqual(frame.y + frame.height - 1);
  expect(
    Math.abs(pages.x + pages.width - (holder.x + holder.width - inset)),
    "the pages at the right",
  ).toBeLessThanOrEqual(1);
  // In the size of the text of the table, muted.
  const cellSize = await grid
    .getByRole("gridcell")
    .first()
    .evaluate((cell) => getComputedStyle(cell).fontSize);
  for (const text of [range, nav.getByRole("link", { name: "Suivant" })]) {
    const style = await text.evaluate((el) => ({
      size: getComputedStyle(el).fontSize,
      colour: getComputedStyle(el).color,
      weight: getComputedStyle(el).fontWeight,
    }));
    expect(style.size).toBe(cellSize);
    expect(style.weight).toBe("400");
  }
  const rangeColour = await range.evaluate((el) => getComputedStyle(el).color);
  expect(rangeColour).toBe(await drawn(page, "text-muted-foreground", "color"));
});

test.describe("the reason undo and redo wait for", () => {
  test.use({ hasTouch: true });

  test(`${path(`${REVISION}/remaining`)}: is read whole by a touch, beside the bar (#3150) [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    const address = path(`${REVISION}/remaining`);
    await compile(page.request, address);
    await open(page, address, { width: 911, height: 800 });
    const reason = "Indisponibles tant que le serveur ne conserve pas l’historique des saisies.";
    const pressed = page.locator("main [data-grid-toolbar]").first().getByRole("button", {
      name: reason,
    });
    await expect(pressed).toBeInViewport();
    await pressed.tap();
    const whole = page.getByRole("dialog", {
      name: "Pourquoi annuler et rétablir sont indisponibles",
    });
    await expect(whole).toBeInViewport({ ratio: 1 });
    await expect(whole).toHaveText(reason);
    const cut = await whole
      .getByText(reason)
      .evaluate((text) => text.scrollWidth > text.clientWidth);
    expect(cut, "the reason is read whole").toBe(false);
  });
});
