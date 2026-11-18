// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The frame of a dense grid in the window, measured (US-0560, #1033, #1041, #1042): on each of the
 * eight screens that fill the window, in a window too low for the grid at its floor, at the two
 * widths of the harness — 1366 points, then 911, what a zoom of 150 % leaves of it —, the frame
 * covers nothing that follows it; the bar above it is as wide as the frame, scroll bars included,
 * and holds on one line; and a grid of a few rows is no taller than its content. No requirement
 * carries this: it is the layout the guide, « Les grilles », states.
 *
 * And the width of a table (US-2080, #3075, #3072), measured rather than compared to an image: its
 * frame at the width of its card, its table the wider of the card and of its columns, its label
 * taking the rest and never less than the width chosen for it, no line between its columns but
 * beside a pinned one, the caption of its totals whole, its pinned columns where they were as it
 * scrolls sideways (WF-IHM-0060).
 */
import { expect, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

/** The window of the harness and the same window at a zoom of 150 %, both lower than any floor. */
const WINDOWS = [
  { width: 1366, height: 300 },
  { width: 911, height: 300 },
] as const;

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The eight screens that fill the window (`Screen`, `fill` or `fillWide`). */
const SCREENS = [
  "/",
  "/portfolio/projects",
  "/admin/audit-log",
  path(`${REVISION}/estimate`),
  path(`${REVISION}/planning`),
  path(`${REVISION}/remaining`),
  path(`${REVISION}/actual-costs`),
  path(`${REVISION}/risks`),
] as const;

/**
 * The screens whose bar holds the three filters of a tree — a lot or a post, « Écarts seulement »,
 * a risk occurred — and the remaining to commit, which holds one: the amendment of the witness.
 */
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
const FILTERED = [
  path(`${REVISION}/estimate?structure=${AMENDMENT}`),
  path(`${REVISION}/planning?structure=${AMENDMENT}`),
  path(`${REVISION}/remaining`),
] as const;

/** The least width, in points, that a filter of the bar keeps when the bar is short of room. */
const FILTER_FLOOR = 90;

/** The height of a bar on one line, in pixels, at most: the buttons are 28 or 32 high. */
const ONE_LINE = 34;

/** Open a screen in a window, until its first grid shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/** What the layout says of each grid of the screen: its frame, its bar, and what follows them. */
interface Measure {
  readonly name: string;
  /** The elements after the frame, at each level up to the page, that its box covers. */
  readonly covered: readonly string[];
  readonly frame: number;
  readonly bar: number;
  readonly barHeight: number;
  /** The children of the bar as laid out in the window: their box, and whether each is a filter. */
  readonly parts: readonly {
    readonly left: number;
    readonly right: number;
    readonly width: number;
    readonly filter: boolean;
  }[];
  readonly narrowBar: {
    readonly width: number;
    readonly height: number;
    /** The widths of the children of the bar, and the gap between them, as laid out when narrowed. */
    readonly children: readonly number[];
    readonly gap: number;
    /** The width of the search, a child with the role of one, when the bar is narrowed. */
    readonly search: number | undefined;
  };
}

/** Measure every grid of the screen, in the page. */
function measureGrids(page: Page): Promise<Measure[]> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    if (main === null) {
      throw new Error("the screen has no main");
    }
    // A bar that folds its filters stacks its line, its panel and its chips: the line is the bar.
    const lineOf = (bar: HTMLElement): HTMLElement => {
      const first = bar.firstElementChild;
      return bar.dataset.folded !== undefined && first instanceof HTMLElement ? first : bar;
    };
    const grids = Array.from(main.querySelectorAll("[role='grid'], [role='treegrid']"));
    return grids.map((grid) => {
      const frame = grid.parentElement;
      const holder = frame?.parentElement;
      const bar = holder?.firstElementChild;
      if (!(frame instanceof HTMLElement) || !(bar instanceof HTMLElement)) {
        throw new Error("the grid has no frame or no bar");
      }
      const box = frame.getBoundingClientRect();
      const covered: string[] = [];
      for (let level: Element | null = frame; level !== null && level !== main;) {
        for (let next = level.nextElementSibling; next !== null; next = next.nextElementSibling) {
          const rect = next.getBoundingClientRect();
          const across = Math.min(rect.right, box.right) - Math.max(rect.left, box.left);
          const down = Math.min(rect.bottom, box.bottom) - Math.max(rect.top, box.top);
          if (rect.height > 0 && across > 1 && down > 1) {
            covered.push(`${next.tagName} ${next.className}`.slice(0, 80));
          }
        }
        level = level.parentElement;
      }
      const line = lineOf(bar);
      const parts = Array.from(line.children).flatMap((child) => {
        const rect = child.getBoundingClientRect();
        return rect.width === 0
          ? []
          : [
              {
                left: rect.left,
                right: rect.right,
                width: rect.width,
                filter: child.querySelector("[aria-haspopup='dialog'], [aria-pressed]") !== null,
              },
            ];
      });
      const measure = {
        parts,
        name: grid.getAttribute("aria-label") ?? "",
        covered,
        frame: frame.offsetWidth,
        bar: bar.offsetWidth,
        barHeight: line.offsetHeight,
      };
      // A table narrower than the bar: the bar keeps what it needs for one line.
      bar.style.width = "100px";
      const children = Array.from(line.children).filter(
        (child): child is HTMLElement => child instanceof HTMLElement,
      );
      const searching = line.querySelector("[role='search']");
      const narrowBar = {
        // A bar that scrolls keeps the width of its frame: what it holds is its scroll width.
        width: Math.max(line.offsetWidth, line.scrollWidth),
        height: line.offsetHeight,
        children: children.map((child) => child.offsetWidth),
        gap: Number.parseFloat(getComputedStyle(line).columnGap) || 0,
        search: searching instanceof HTMLElement ? searching.offsetWidth : undefined,
      };
      bar.style.width = "";
      return { ...measure, narrowBar };
    });
  });
}

for (const address of SCREENS) {
  test(`${address}: the frame of each grid covers nothing in a low window, and its bar is as wide as the frame, on one line`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const grids = await measureGrids(page);
      expect(grids.length, `${address} has a grid`).toBeGreaterThan(0);
      for (const grid of grids) {
        const where = `${grid.name} at ${String(size.width)}`;
        expect(grid.covered, `what the frame of ${where} covers`).toEqual([]);
        // The scroll bars the system draws beside the rows are in the width of the frame.
        expect(Math.abs(grid.bar - grid.frame), `the bar of ${where}`).toBeLessThanOrEqual(1);
        expect(grid.barHeight, `the bar of ${where} on one line`).toBeLessThanOrEqual(ONE_LINE);
        expect(
          grid.narrowBar.height,
          `the narrowed bar of ${where} on one line`,
        ).toBeLessThanOrEqual(ONE_LINE);
        // The bar narrowed is the sum of the least its children take, gaps included (`min-w-min`):
        // none is squeezed under its own minimum, the search keeping its `min-w-24` (96 points).
        const { children, gap, width } = grid.narrowBar;
        const least = children.reduce((sum, each) => sum + each, 0) + gap * (children.length - 1);
        expect(
          width,
          `the narrowed bar of ${where} holds its children at their least`,
        ).toBeGreaterThanOrEqual(least - 1);
        if (grid.narrowBar.search !== undefined) {
          expect(
            grid.narrowBar.search,
            `the narrowed search of ${where} keeps its minimal width`,
          ).toBeGreaterThanOrEqual(95);
        }
      }
    }
  });
}

for (const address of FILTERED) {
  test(`${address}: at 911 points each filter of the bar keeps its floor and none overlaps its neighbour, the bar scrolling rather than crushing them`, async ({
    page,
  }) => {
    await compile(page.request, address);
    const [, narrow] = WINDOWS;
    await open(page, address, narrow);
    // The value may be cut to the room: its tooltip says the whole of it (#2916).
    const menu = page.locator("[data-grid-toolbar] button[aria-haspopup='dialog']").first();
    await menu.hover();
    await expect(page.getByRole("tooltip").first()).toContainText(
      "Choix : Tous les lots et postes",
    );
    const grids = await measureGrids(page);
    expect(grids.length, `${address} has a grid`).toBeGreaterThan(0);
    for (const grid of grids) {
      const filters = grid.parts.filter((part) => part.filter);
      expect(filters.length, `the filters of ${grid.name}`).toBeGreaterThan(0);
      for (const part of filters) {
        expect(part.width, `a filter of ${grid.name}`).toBeGreaterThanOrEqual(FILTER_FLOOR);
      }
      for (const [at, part] of grid.parts.slice(1).entries()) {
        const before = grid.parts[at];
        expect(
          part.left,
          `a part of the bar of ${grid.name} overlaps the one before`,
        ).toBeGreaterThanOrEqual((before?.right ?? 0) - 1);
      }
    }
  });
}

/** The screens whose frame is measured again after the window is resized, with no new load. */
const RESIZED = ["/", path(`${REVISION}/planning`)] as const;

for (const address of RESIZED) {
  test(`${address}: the bar follows the frame when the window is resized, with no new load (#1144)`, async ({
    page,
  }) => {
    await compile(page.request, address);
    const [wide, narrow] = WINDOWS;
    await open(page, address, wide);
    for (const size of [narrow, wide]) {
      // The observer of the frame measures it again: only the window changes, the page stays.
      await page.setViewportSize(size);
      await expect
        .poll(
          async () => {
            const grids = await measureGrids(page);
            return grids.every((grid) => Math.abs(grid.bar - grid.frame) <= 1);
          },
          { message: `the bar of ${address} is as wide as its frame at ${String(size.width)}` },
        )
        .toBe(true);
    }
  });
}

/** The top and the bottom of the frame of the first grid of the screen, in the window. */
async function frameBox(page: Page): Promise<{ top: number; bottom: number }> {
  const box = await page
    .locator("main [role='grid'], main [role='treegrid']")
    .first()
    .locator("xpath=..")
    .boundingBox();
  if (box === null) {
    throw new Error("the grid has no frame in the window");
  }
  return { top: box.y, bottom: box.y + box.height };
}

test("the height of a grid is measured again when the panel of its filters or their chips open or close above it, its totals kept in the window [WF-IHM-0060-A]", async ({
  page,
}) => {
  // The bar of the selection lies over the bar of the grid, in its place, and moves nothing: the
  // path of the selection of the accounts measures it (`admin.spec.ts`). The journal of audit holds
  // it: the screen of the accounts is no longer a screen that fills the window (US-2100).
  const address = "/admin/audit-log";
  await compile(page.request, address);
  const toggle = page.getByRole("button", { name: /^Filtres( \(|$)/ });
  const totals = page.getByRole("grid").getByRole("row").last().locator("td, th").first();
  // The totals span every column, the width of the table: they are in the window when they lie
  // between its top and its bottom, whatever the columns the frame scrolls sideways.
  const expectTotalsInWindow = async () => {
    await expect
      .poll(async () => {
        const place = await totals.boundingBox();
        const window = page.viewportSize();
        return (
          place !== null &&
          window !== null &&
          place.y >= 0 &&
          place.y + place.height <= window.height
        );
      })
      .toBe(true);
  };
  // In a tall window, where the panel opened lies: how far it pushes the frame down.
  await open(page, address, { width: 1366, height: 1400 });
  const closed = await frameBox(page);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect.poll(async () => (await frameBox(page)).top).toBeGreaterThan(closed.top);
  const panel = (await frameBox(page)).top - closed.top;
  // A window that leaves the frame of the open panel 200 points, under the content of the
  // accounts (260) and over the floor (160): the frame is bounded to the room left below it.
  const room = 200;
  const height = Math.ceil(closed.top + panel + room);
  await page.setViewportSize({ width: 1366, height });
  await expect.poll(async () => (await frameBox(page)).bottom).toBeLessThanOrEqual(height + 1);
  const opened = await frameBox(page);
  expect(opened.bottom - opened.top).toBeLessThanOrEqual(room + 1);
  await expectTotalsInWindow();

  // Closed, the frame goes back up and takes the room the panel left.
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect.poll(async () => (await frameBox(page)).top).toBe(closed.top);
  const shut = await frameBox(page);
  expect(shut.bottom).toBeLessThanOrEqual(height + 1);
  expect(shut.bottom - shut.top).toBeGreaterThan(opened.bottom - opened.top);
  await expectTotalsInWindow();

  // A filter on: its chip under the bar pushes the frame down, bounded still; lifted, it comes back.
  await open(page, `${address}?object_kind=risk`, { width: 1366, height });
  const chipped = await frameBox(page);
  expect(chipped.top).toBeGreaterThan(closed.top);
  expect(chipped.bottom).toBeLessThanOrEqual(height + 1);
  await expectTotalsInWindow();
  await page.getByRole("button", { name: /^Retirer le filtre Nature de l’objet/ }).click();
  await expect(page.getByRole("list", { name: "Filtres actifs" })).toHaveCount(0, {
    timeout: WORKING,
  });
  await expect.poll(async () => (await frameBox(page)).top).toBe(closed.top);
  expect((await frameBox(page)).bottom).toBeLessThanOrEqual(height + 1);
  await expectTotalsInWindow();
});

test("a grid of a few rows is no taller than its content, in a window that would hold more", async ({
  page,
}) => {
  await compile(page.request, "/admin/users");
  await open(page, "/admin/users", { width: 1366, height: 1400 });
  const heights = await page.evaluate(() => {
    const grid = document.querySelector("main [role='grid']");
    const frame = grid?.parentElement;
    if (!(grid instanceof HTMLElement) || !(frame instanceof HTMLElement)) {
      throw new Error("the screen has no grid");
    }
    return { frame: frame.offsetHeight, table: grid.offsetHeight };
  });
  // The table and the two borders of the frame: no band under the totals (#1041).
  expect(heights.frame).toBeLessThanOrEqual(heights.table + 2);
});

/**
 * The screens whose key figures lie in cards above their grid (US-0550), at the two widths of the
 * harness, in a window 768 high: the totals of the grid stay in the window at both. Two ways hold
 * the criterion at 911 (US-0710, #1209): on the estimate and the remaining to commit, `folded`, the cards are
 * folded into a summary that unfolds (`FoldingFigures`, below 1024 points) and are hidden; on the
 * others they stay visible, the actual costs, whose grid and journal of imports lie one under the
 * other below 1024, bounding the grid to the height of the window less where it starts
 * (`useRoomBelow`, `max-h-svh` alone not being enough). The risks hold with the chart of their
 * matrix folded between the cards and the grid (US-0550/L4b, #1252): unfolded, it takes its 288
 * points and the page scrolls.
 */
const CARD_SCREENS = [
  { address: path(`${REVISION}/estimate`), widths: [1366, 911], height: 768, folded: true },
  { address: path(`${REVISION}/remaining`), widths: [1366, 911], height: 768, folded: true },
  { address: path(`${REVISION}/actual-costs`), widths: [1366, 911], height: 768, folded: false },
  { address: path(`${REVISION}/risks`), widths: [1366, 911], height: 768, folded: false },
] as const;

for (const { address, widths, height, folded } of CARD_SCREENS) {
  test(`${address}: the cards of figures leave the totals of the grid in the window at 911 points as at 1366 [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const width of widths) {
      await open(page, address, { width, height });
      const cards = page.locator("main [data-slot='card'][role='region']");
      expect(await cards.count(), `the cards of ${address}`).toBeGreaterThan(0);
      if (folded && width < 1024) {
        await expect(
          cards.first(),
          `the folded cards of ${address} at ${String(width)}`,
        ).toBeHidden();
      } else {
        await expect(cards.first(), `the cards of ${address} at ${String(width)}`).toBeVisible();
      }
      const grid = page.locator("main [role='grid'], main [role='treegrid']").first();
      // The totals stick to the foot of the grid: the cell that holds them tells where they are.
      await expect(
        grid.getByRole("row").last().locator("td, th").first(),
        `the totals of ${address} at ${String(width)}`,
      ).toBeInViewport({ ratio: 1 });
    }
  });
}

/**
 * A header of a grid as laid out: its column, its width, the width its handle announces and the
 * narrowest it takes it to, if it widens, and whether its column takes the rest of the card — its
 * `<col>` given no width.
 */
interface Header {
  readonly column: string;
  readonly width: number;
  readonly announced: number | undefined;
  readonly least: number | undefined;
  readonly stretched: boolean;
}

/** What the layout says of the width of a grid, its columns, its lines and its totals (US-2080). */
interface Width {
  readonly name: string;
  /** The width of the frame, and of what holds it and its bar. */
  readonly frame: number;
  readonly holder: number;
  /** The room inside the frame, its borders and its scroll bar out, and the width of its table. */
  readonly room: number;
  readonly table: number;
  readonly bar: number;
  readonly headers: readonly Header[];
  /** The cells of the first row that draw a line on a side, and whether each is pinned. */
  readonly lined: readonly { readonly column: string; readonly pinned: boolean }[];
  /** Whether the words of the caption of the totals are cut; none for a grid without totals. */
  readonly cut: boolean | undefined;
  /** The right edge of the pages under the table, if the screen sets some beside it, and the frame's. */
  readonly pages: number | undefined;
  readonly right: number;
}

/** Measure the width of each grid of the screen. */
function measureWidths(page: Page): Promise<Width[]> {
  return page.evaluate(() => {
    const headersOf = (grid: Element) => {
      const cols = Array.from(grid.querySelectorAll<HTMLElement>("colgroup col"));
      return Array.from(grid.querySelectorAll<HTMLElement>("thead th")).map((th, at) => {
        const handle = th.querySelector("[role='separator']");
        const value = (name: string) =>
          handle === null ? undefined : Number(handle.getAttribute(name));
        return {
          column: th.dataset.column ?? "",
          width: th.getBoundingClientRect().width,
          announced: value("aria-valuenow"),
          least: value("aria-valuemin"),
          stretched: cols[at]?.style.width === "",
        };
      });
    };
    const linedOf = (grid: Element) => {
      const row = grid.querySelector("tbody tr[aria-rowindex]");
      return Array.from(row?.querySelectorAll<HTMLElement>("td") ?? []).flatMap((cell) => {
        const style = getComputedStyle(cell);
        const sides =
          Number.parseFloat(style.borderLeftWidth) + Number.parseFloat(style.borderRightWidth);
        const pinned = cell.style.left !== "" || cell.style.right !== "";
        return sides > 0 ? [{ column: cell.dataset.column ?? "", pinned }] : [];
      });
    };
    const cutOf = (grid: Element) => {
      const caption = Array.from(grid.querySelectorAll<HTMLElement>("tfoot td")).find(
        (cell) => cell.textContent !== "",
      );
      if (caption === undefined) {
        return undefined;
      }
      const words = caption.querySelector("span") ?? caption;
      return (
        caption.scrollWidth > caption.clientWidth + 1 || words.scrollWidth > words.clientWidth + 1
      );
    };
    const grids = Array.from(
      document.querySelectorAll("main [role='grid'], main [role='treegrid']"),
    );
    const after = (one: Node, other: Node) =>
      (one.compareDocumentPosition(other) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
    // The pages of a grid: the first after it in the page, before the next grid.
    const pagesOf = (grid: Element, at: number) => {
      const next = grids[at + 1];
      return Array.from(document.querySelectorAll("main [data-slot='pagination']")).find(
        (pages) => after(grid, pages) && (next === undefined || after(pages, next)),
      )?.parentElement;
    };
    return grids.map((grid, at) => {
      const frame = grid.parentElement;
      const holder = frame?.parentElement;
      const bar = holder?.firstElementChild;
      if (
        !(frame instanceof HTMLElement) ||
        !(holder instanceof HTMLElement) ||
        !(bar instanceof HTMLElement)
      ) {
        throw new Error("the grid has no frame");
      }
      const pages = pagesOf(grid, at);
      return {
        name: grid.getAttribute("aria-label") ?? "",
        frame: frame.offsetWidth,
        holder: holder.clientWidth,
        room: frame.clientWidth,
        table: grid.getBoundingClientRect().width,
        bar: bar.offsetWidth,
        headers: headersOf(grid),
        lined: linedOf(grid),
        cut: cutOf(grid),
        pages: pages?.getBoundingClientRect().right,
        right: frame.getBoundingClientRect().right,
      };
    });
  });
}

/** Check the widths of a grid: its frame, its bar, its table, its columns. */
function expectWidths(grid: Width, where: string) {
  expect(
    Math.abs(grid.frame - grid.holder),
    `the frame of ${where} in its card`,
  ).toBeLessThanOrEqual(1);
  expect(Math.abs(grid.bar - grid.frame), `the bar of ${where}`).toBeLessThanOrEqual(1);
  const stretched = grid.headers.filter((header) => header.stretched);
  expect(stretched.length, `the column of ${where} that takes the rest`).toBe(1);
  const others = grid.headers
    .filter((header) => !header.stretched)
    .reduce((sum, header) => sum + (header.announced ?? header.width), 0);
  // The table: the wider of the room of its frame and of its columns.
  expect(
    Math.abs(grid.table - Math.max(grid.room, others + (stretched[0]?.width ?? 0))),
    `the table of ${where}`,
  ).toBeLessThanOrEqual(2);
  for (const header of grid.headers.filter((each) => each.announced !== undefined)) {
    // Each handle announces the width its column shows.
    expect(
      Math.abs(header.width - (header.announced ?? 0)),
      `${header.column} of ${where} as announced`,
    ).toBeLessThanOrEqual(1);
    if (header.stretched) {
      // Never narrower than what the other columns leave it, which is its least; that width
      // when the table is no wider than its card.
      const rest = Math.max(40, grid.room - others);
      expect(
        Math.abs((header.least ?? 0) - rest),
        `the least of ${header.column} of ${where}`,
      ).toBeLessThanOrEqual(1);
      expect(header.width, `${header.column} of ${where} takes the rest`).toBeGreaterThanOrEqual(
        rest - 1,
      );
      if (grid.table <= grid.room + 1) {
        expect(
          Math.abs(header.width - rest),
          `${header.column} of ${where} takes the rest`,
        ).toBeLessThanOrEqual(2);
      }
    }
  }
}

/**
 * The screens of flat tables and of a tree measured for their width: the reference of the costs —
 * the natures, the categories, the grid of the rates, wider than its card —, that of the resources
 * — the tree of the organisation, the roles, the calendars —, the accounts and their pages.
 */
const WIDTH_SCREENS = ["/reference/costs", "/reference/resources", "/admin/users"] as const;

for (const address of WIDTH_SCREENS) {
  test(`${address}: each table takes the width of its card, its label the rest and never less than its width chosen, no line between its columns but beside a pinned one, its bar, its pages and the caption of its totals whole [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    // « Les colonnes masquées et les largeurs choisies sont retrouvées à la réouverture » : the
    // width chosen for the label becomes its least, the label taking the rest of the card (#3075,
    // #3079, #3072).
    await compile(page.request, address);
    for (const { width } of WINDOWS) {
      await open(page, address, { width, height: 900 });
      const grids = await measureWidths(page);
      expect(grids.length, `${address} has a grid`).toBeGreaterThan(0);
      for (const grid of grids) {
        const where = `${grid.name} at ${String(width)}`;
        expectWidths(grid, where);
        for (const cell of grid.lined) {
          expect(cell.pinned, `the line beside ${cell.column} of ${where}`).toBe(true);
        }
        expect(grid.lined.length, `the lines of ${where}`).toBeLessThanOrEqual(2);
        expect(grid.cut, `the caption of the totals of ${where}`).not.toBe(true);
        if (grid.pages !== undefined) {
          expect(Math.abs(grid.pages - grid.right), `the pages of ${where}`).toBeLessThanOrEqual(1);
        }
      }
    }
  });
}

test("a table wider than its card scrolls in its frame, its label at its width chosen, its pinned columns and the caption of its totals where they were [WF-IHM-0060-A]", async ({
  page,
}) => {
  // « Après défilement de mille lignes, en-têtes et totaux sont toujours visibles, de même que la
  // colonne de libellé après défilement horizontal » : the grid of the rates, fifteen years wide.
  const address = "/reference/costs";
  await compile(page.request, address);
  for (const { width } of WINDOWS) {
    await open(page, address, { width, height: 900 });
    const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
    // Where the pinned cells of the header and of the first row, and the words of the caption of
    // the totals, stand in the frame; and how far the frame scrolls sideways.
    const placed = () =>
      grid.evaluate((table) => {
        const frame = table.parentElement;
        const start = frame?.getBoundingClientRect().left ?? 0;
        const at = (cell: Element) => {
          const rect = cell.getBoundingClientRect();
          return { left: rect.left - start, right: rect.right - start };
        };
        const pinned = (cells: NodeListOf<HTMLElement> | undefined) =>
          Array.from(cells ?? [])
            .filter((cell) => cell.style.left !== "")
            .map(at);
        const caption = Array.from(table.querySelectorAll<HTMLElement>("tfoot td")).find(
          (cell) => cell.textContent !== "",
        );
        const words = caption?.querySelector("span") ?? caption;
        return {
          headers: pinned(table.querySelectorAll<HTMLElement>("thead th")),
          cells: pinned(table.querySelector("tbody tr[aria-rowindex]")?.querySelectorAll("td")),
          words: words === undefined ? undefined : at(words).left,
          scroll: (frame?.scrollWidth ?? 0) - (frame?.clientWidth ?? 0),
        };
      });
    const before = await placed();
    expect(
      before.scroll,
      `the rates at ${String(width)} are wider than their card`,
    ).toBeGreaterThan(100);
    const [grids] = (await measureWidths(page)).filter(
      (each) => each.name === "Grille des taux horaires",
    );
    if (grids === undefined) {
      throw new Error("no grid of the rates");
    }
    expectWidths(grids, `the rates at ${String(width)}`);
    // The pinned columns follow one another, each where the one before it ends.
    expect(before.headers.length).toBeGreaterThan(1);
    for (const [at, header] of before.headers.slice(1).entries()) {
      expect(Math.abs(header.left - (before.headers[at]?.right ?? 0))).toBeLessThanOrEqual(1);
    }
    expect(before.cells).toEqual(before.headers);
    await grid.locator("xpath=..").evaluate((frame) => {
      frame.scrollLeft = 100;
    });
    await expect.poll(async () => (await placed()).headers).toEqual(before.headers);
    const after = await placed();
    expect(after.cells).toEqual(before.cells);
    expect(after.words, "the caption of the totals where it was").toBe(before.words);
  }
});

/** The first flat table of the reference of the costs no wider than its card, by its name. */
async function narrowTable(page: Page): Promise<string> {
  const grids = await measureWidths(page);
  const found = grids.find(
    (grid) => grid.table <= grid.room + 1 && grid.headers.some((header) => header.stretched),
  );
  if (found === undefined) {
    throw new Error("no table narrower than its card");
  }
  return found.name;
}

test("the column that takes the rest of its card widens from its visible edge, which follows the pointer, and narrows no further than the rest of its card, its handle announcing the width it shows [WF-IHM-0060-A]", async ({
  page,
}) => {
  // « Les colonnes masquées et les largeurs choisies sont retrouvées à la réouverture » : the width
  // the handle writes is the one seen (#3075).
  const address = "/reference/costs";
  await compile(page.request, address);
  await open(page, address, { width: 1366, height: 900 });
  const grid = page.locator(`main [role='grid'][aria-label="${await narrowTable(page)}"]`);
  const stretched = grid
    .locator("thead th")
    .nth(
      await grid.evaluate((table) =>
        Array.from(table.querySelectorAll<HTMLElement>("colgroup col")).findIndex(
          (col) => col.style.width === "",
        ),
      ),
    );
  const handle = stretched.getByRole("separator");
  const box = async () => {
    const bounds = await stretched.boundingBox();
    return { width: bounds?.width ?? 0, right: (bounds?.x ?? 0) + (bounds?.width ?? 0) };
  };
  const shown = await box();
  // The handle announces the width the column shows, which is the narrowest it goes.
  await expect(handle).toHaveAttribute("aria-valuenow", String(Math.round(shown.width)));
  await expect(handle).toHaveAttribute("aria-valuemin", String(Math.round(shown.width)));
  const grip = await handle.boundingBox();
  const x = (grip?.x ?? 0) + (grip?.width ?? 0) / 2;
  const y = (grip?.y ?? 0) + (grip?.height ?? 0) / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  // Sixty points right: the edge follows the pointer, and the table passes its card.
  await page.mouse.move(x + 60, y, { steps: 4 });
  await expect.poll(async () => (await box()).right - shown.right).toBeCloseTo(60, 0);
  await expect(handle).toHaveAttribute("aria-valuenow", String(Math.round(shown.width) + 60));
  const scroll = await grid.evaluate(
    (table) => (table.parentElement?.scrollWidth ?? 0) - (table.parentElement?.clientWidth ?? 0),
  );
  expect(scroll, "the table passes its card").toBeGreaterThan(50);
  // A hundred points left of where it was pressed: the column at the rest of its card, no narrower.
  await page.mouse.move(x - 100, y, { steps: 4 });
  await expect.poll(async () => (await box()).right - shown.right).toBeCloseTo(0, 0);
  await page.mouse.up();
  await expect(handle).toHaveAttribute("aria-valuenow", String(Math.round(shown.width)));
});

test("the row under the pointer is tinted, apart from the others [WF-IHM-0060-A]", async ({
  page,
}) => {
  const address = "/reference/costs";
  await compile(page.request, address);
  await open(page, address, { width: 1366, height: 900 });
  const grid = page.locator(`main [role='grid'][aria-label="${await narrowTable(page)}"]`);
  const rows = grid.locator("tbody tr[aria-rowindex]");
  expect(await rows.count(), "the table has two rows").toBeGreaterThan(1);
  // The background of the cell of the label, which no shade of a computed column covers.
  const tint = (row: number) =>
    rows
      .nth(row)
      .locator("td[data-column='label']")
      .evaluate((cell) => getComputedStyle(cell).backgroundColor);
  await page.mouse.move(0, 0);
  const plain = await tint(1);
  expect(await tint(0)).toBe(plain);
  await rows.nth(0).locator("td[data-column='label']").hover();
  await expect.poll(() => tint(0)).not.toBe(plain);
  expect(await tint(1)).toBe(plain);
});

test("scrolled to its end, the caption of the totals of a narrowed label stays over the pinned columns, its words cut where they end [WF-IHM-0060-A]", async ({
  page,
}) => {
  // Decision 3 of #3072: the caption, wider than the pinned columns once the label is narrowed,
  // never covers a figure scrolled under it — its words are cut at the edge of the pinned columns.
  const address = path(`${REVISION}/estimate`);
  await compile(page.request, address);
  await open(page, address, { width: 911, height: 900 });
  const grid = page.locator("main [role='treegrid']").first();
  const label = grid.locator("thead th[data-column='label']");
  const handle = label.getByRole("separator");
  const grip = await handle.boundingBox();
  const y = (grip?.y ?? 0) + (grip?.height ?? 0) / 2;
  await page.mouse.move((grip?.x ?? 0) + 2, y);
  await page.mouse.down();
  await page.mouse.move(0, y, { steps: 5 });
  await page.mouse.up();
  await expect(handle).toHaveAttribute("aria-valuenow", "40");
  await grid.locator("xpath=..").evaluate((frame) => {
    frame.scrollLeft = frame.scrollWidth;
  });
  const placed = () =>
    grid.evaluate((table) => {
      const caption = Array.from(table.querySelectorAll<HTMLElement>("tfoot td")).find(
        (cell) => cell.textContent !== "",
      );
      const words = caption?.querySelector("span");
      const header = table.querySelector("thead th[data-column='label']");
      const edges = (element: Element | null | undefined) => {
        const rect = element?.getBoundingClientRect();
        return { left: rect?.left ?? 0, right: rect?.right ?? 0 };
      };
      return {
        cell: caption?.getBoundingClientRect().right ?? 0,
        words: edges(words),
        label: edges(header),
        scrolled: table.parentElement?.scrollLeft ?? 0,
      };
    });
  await expect.poll(async () => (await placed()).scrolled).toBeGreaterThan(400);
  const after = await placed();
  // The caption ends where the label does; its words start where the label does, and run past
  // its end, cut there.
  expect(
    Math.abs(after.cell - after.label.right),
    "the caption ends with the label",
  ).toBeLessThanOrEqual(1);
  expect(
    Math.abs(after.words.left - after.label.left),
    "the words of the caption start with the label",
  ).toBeLessThanOrEqual(1);
  expect(after.words.right - after.cell, "the words of the caption are cut").toBeGreaterThan(8);
});
