// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grids of work of a revision in cards (EP-25, US-2140/L1), measured rather than compared to an
 * image: the planning, the estimate, the remaining to commit and the task tree stay tight — their
 * card is as wide as the window leaves it, in no centred column —, the card fills the window, the
 * grid is as wide as the body of its card, the height of its rows is the one it had (`ROW`), and the
 * planning start date lies in the card, not under the title (WF-IHM-0100-A). That the screens are
 * walked entirely by the keyboard, their contrast measured in both modes and nothing lost at 911
 * points — a zoom of 150 % — is proven by `accessibility.spec.ts`, which draws them from the table
 * of the functions.
 *
 * US-2140/L2 adds the actual costs — their grid in a card of work beside the journal of the imports,
 * a card of its own, the title saying no count of lines —, the timelines — the choice a row of
 * tabs, the creation filled — and the Kanban — its columns panels with the shape of their state.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

const WINDOWS = [
  { width: 1366, height: 900 },
  { width: 911, height: 900 },
] as const;

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The height of a row of a dense grid, in pixels (`h-7`): it does not change with the card. */
const ROW = 28;

/** The margin of a screen of work, in pixels: `px-5` on each side. */
const MARGIN = 20;

/** The vertical padding of a screen of work, in pixels: `py-3` under the card. */
const PADDING = 12;

const GRIDS = [`${REVISION}/planning`, `${REVISION}/estimate`, `${REVISION}/remaining`] as const;

interface Fit {
  readonly main: {
    readonly left: number;
    readonly right: number;
    readonly bottom: number;
    readonly width: number;
  };
  readonly card: { readonly left: number; readonly right: number; readonly bottom: number };
  readonly body: number;
  readonly frame: number;
  readonly table: number;
  readonly row: number;
  /** Whether the date of the planning start is in the card, and the heading of the screen is not. */
  readonly start: boolean | undefined;
}

/** Measure the card of the grid against its screen and its window. */
function measure(page: Page): Promise<Fit> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    const card = main?.querySelector("[data-slot='grid-card']");
    const body = card?.querySelector("[data-slot='card-content']");
    const grid = card?.querySelector("[role='grid'], [role='treegrid']");
    if (!(main instanceof HTMLElement) || !(card instanceof HTMLElement)) {
      throw new Error("the screen has no card of work");
    }
    if (!(body instanceof HTMLElement) || !(grid instanceof HTMLElement)) {
      throw new Error("the card has no body or no grid");
    }
    const frame = grid.parentElement;
    const style = getComputedStyle(body);
    const first = grid.querySelector("tbody tr");
    const date = Array.from(main.querySelectorAll("section")).find((section) =>
      /début de planning/i.test(section.getAttribute("aria-label") ?? ""),
    );
    const box = main.getBoundingClientRect();
    const around = card.getBoundingClientRect();
    return {
      main: { left: box.left, right: box.right, bottom: box.bottom, width: box.width },
      card: { left: around.left, right: around.right, bottom: around.bottom },
      body: body.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
      frame: frame?.getBoundingClientRect().width ?? 0,
      table: grid.getBoundingClientRect().width,
      row: first instanceof HTMLElement ? first.getBoundingClientRect().height : 0,
      start: date === undefined ? undefined : card.contains(date),
    };
  });
}

for (const address of GRIDS) {
  for (const size of WINDOWS) {
    test(`${address}: the card of the grid is as wide as the window, the grid as wide as the card, its rows as tall as ever, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
      page,
    }) => {
      const url = path(address);
      await compile(page.request, url);
      await page.setViewportSize(size);
      await page.goto(url);
      await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
        timeout: WORKING,
      });
      await untilHydrated(page);
      const fit = await measure(page);
      // Tight, in no centred column: the card spans the window less the margin of the screen.
      expect(fit.card.left, "the card at the left margin").toBeCloseTo(fit.main.left + MARGIN, 0);
      expect(fit.card.right, "the card at the right margin").toBeCloseTo(
        fit.main.right - MARGIN,
        0,
      );
      // It fills the window: its foot is at the foot of the window, less the padding of `main`.
      expect(fit.main.bottom, "main reaches the foot of the window").toBeCloseTo(size.height, 0);
      expect(fit.card.bottom, "the foot of the card at the foot of the window").toBeCloseTo(
        fit.main.bottom - PADDING,
        0,
      );
      expect(
        Math.abs(fit.frame - fit.body),
        "the frame is as wide as the body",
      ).toBeLessThanOrEqual(1);
      expect(fit.table, "the table fills its frame").toBeGreaterThanOrEqual(fit.frame - 2);
      expect(fit.row, "the grid has at least one row").toBeGreaterThan(0);
      // Measured: the cells of the planning hold an editable control as tall as the row, `h-7`, and
      // the row adds its bottom border, 1 px, 29 px in all. The planning had the same height before
      // the card: on 2026-11-15, on the tree before US-2140/L1 (the planning in no card, 1366 x 900
      // points), a probe read 29 px for each of the first three rows of its treegrid. These 29 px are
      // not new (#3423).
      expect(fit.row, "the height of a row").toBeCloseTo(
        address.endsWith("/planning") ? ROW + 1 : ROW,
        0,
      );
      if (address.endsWith("/planning")) {
        expect(fit.start, "the planning start date is in the card").toBe(true);
      }
    });
  }
}

test("the task tree is in a card as wide as the window, no centred column [WF-IHM-0100-A]", async ({
  page,
}) => {
  const url = path(`${REVISION}/task-tree`);
  await compile(page.request, url);
  await page.setViewportSize(WINDOWS[0]);
  await page.goto(url);
  await expect(page.getByRole("tree")).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  const { main, card } = await page.evaluate(() => {
    const screen = document.querySelector("main")?.getBoundingClientRect();
    const around = document.querySelector("main [data-slot='grid-card']")?.getBoundingClientRect();
    if (screen === undefined || around === undefined) {
      throw new Error("no card in the task tree");
    }
    return { main: screen, card: around };
  });
  expect(card.left).toBeCloseTo(main.left + MARGIN, 0);
  expect(card.right).toBeCloseTo(main.right - MARGIN, 0);
  expect(main.bottom, "main reaches the foot of the window").toBeCloseTo(WINDOWS[0].height, 0);
  expect(card.bottom, "the foot of the card at the foot of the window").toBeCloseTo(
    main.bottom - PADDING,
    0,
  );
});

test("the actual costs hold their grid in a card that fills the window, and the journal of the imports in a card of its own, the title saying no count [WF-IHM-0100-A]", async ({
  page,
}) => {
  const url = path(`${REVISION}/actual-costs`);
  await compile(page.request, url);
  await page.setViewportSize(WINDOWS[0]);
  await page.goto(url);
  await expect(page.locator("main [role='grid']").first()).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  const { main, card, body, table, journal } = await page.evaluate(() => {
    const screen = document.querySelector("main");
    const work = screen?.querySelector("[data-slot='grid-card']");
    const inside = work?.querySelector("[data-slot='card-content']");
    const frame = work?.querySelector("[role='grid']")?.parentElement;
    const region = document.querySelector("main section[aria-label='Journal des imports']");
    if (!screen || !work || !inside || !frame) {
      throw new Error("the actual costs have no card of work");
    }
    return {
      main: screen.getBoundingClientRect(),
      card: work.getBoundingClientRect(),
      body: inside.getBoundingClientRect().width,
      table: frame.getBoundingClientRect().width,
      journal: region?.querySelector("[data-slot='card']") !== null,
    };
  });
  expect(card.left, "the card at the left margin").toBeCloseTo(main.left + MARGIN, 0);
  expect(card.bottom, "the foot of the card at the foot of the window").toBeCloseTo(
    main.bottom - PADDING,
    0,
  );
  expect(table, "the frame of the grid is held by its card").toBeLessThanOrEqual(body);
  expect(journal, "the journal of the imports is a card").toBe(true);
  // The count of lines retained is no longer under the title: the total line says it.
  await expect(page.getByText(/^\d+ lignes? retenues?$|^aucune ligne retenue$/)).toHaveCount(0);
  await expect(page.getByRole("row", { name: /^Total général des lignes retenues/ })).toBeVisible();
});

test("the timelines are chosen by a row of tabs, the one that creates being the only filled command [WF-IHM-0100-A]", async ({
  page,
}) => {
  const url = path(`${REVISION}/timelines`);
  await compile(page.request, url);
  await page.goto(url);
  const tabs = page.getByRole("navigation", { name: "Chronologie affichée" });
  await expect(tabs).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  const links = tabs.getByRole("link");
  expect(await links.count(), "the project has several timelines").toBeGreaterThan(1);
  const transparent = "rgba(0, 0, 0, 0)";
  const fill = (locator: Locator) =>
    locator.evaluate((element) => getComputedStyle(element).backgroundColor);
  // A tab has no fill, the current one is underlined and said by `aria-current`.
  for (const link of await links.all()) {
    expect(await fill(link), "a tab is not a filled button").toBe(transparent);
  }
  const current = tabs.locator("[aria-current='true']");
  await expect(current).toHaveCount(1);
  expect(
    await current.evaluate((element) => getComputedStyle(element).borderBottomWidth),
    "the current tab is underlined",
  ).toBe("2px");
  // « Nouvelle chronologie », which creates, is filled; the deletion beside it is outlined.
  const create = page.getByRole("button", { name: "Nouvelle chronologie" });
  const remove = page.getByRole("button", { name: /^Supprimer la chronologie/ });
  expect(await fill(create), "the creation is filled").not.toBe(transparent);
  expect(await fill(create), "the deletion is outlined, not filled").not.toBe(await fill(remove));
});

test("the Kanban columns are panels, each titled by the shape of its state [WF-IHM-0100-A]", async ({
  page,
}) => {
  const url = path(`${REVISION}/kanban`);
  await compile(page.request, url);
  await page.goto(url);
  const started = page.getByRole("region", { name: "Démarrées", exact: true });
  await expect(started).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
  for (const name of ["Non démarrées", "Démarrées", "Terminées"]) {
    const column = page.getByRole("region", { name, exact: true });
    const look = await column.evaluate((element) => {
      const style = getComputedStyle(element);
      const inner = element.querySelector("li");
      return {
        radius: parseFloat(style.borderTopLeftRadius),
        border: parseFloat(style.borderTopWidth),
        fill: style.backgroundColor,
        card: inner === null ? undefined : getComputedStyle(inner).backgroundColor,
        shape: element.querySelector("h2 svg") !== null,
      };
    });
    expect(look.radius, `${name}: rounded`).toBeGreaterThan(0);
    expect(look.border, `${name}: bordered`).toBeGreaterThan(0);
    expect(look.fill, `${name}: a panel, not the page`).not.toBe("rgba(0, 0, 0, 0)");
    if (look.card !== undefined) {
      expect(look.fill, `${name}: the cards stand out of their panel`).not.toBe(look.card);
    }
    expect(look.shape, `${name}: the shape of its state`).toBe(true);
  }
});
