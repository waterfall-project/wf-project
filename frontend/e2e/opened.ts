// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a gesture opens on a screen, opened by the keyboard and checked as the screen is
 * (US-0710, WF-IHM-0100): what the harness of the screens (`accessibility.spec.ts`) cannot reach
 * by looking at a screen as it opens (#782).
 *
 * - The triggers of a dialog or a menu: what says it opens one — `aria-haspopup="dialog"` or
 *   `"menu"`, which Radix sets on the trigger of a menu, and a command that opens a dialog sets
 *   itself —, shown and enabled, each given the focus and opened by Enter. What opens is the
 *   dialog, or the menu, that shows.
 * - The editor of a cell: in each grid, the first cell that takes an entry — a cell of `DenseGrid`,
 *   which says where it lies (`data-column`) and says it is read only when it takes none
 *   (`aria-readonly`) — given the focus and opened by F2. What opens is the field that takes the
 *   focus in the cell.
 *
 * A dialog is walked by Tab within itself (`walkByTab`): a modal dialog keeps the focus by bringing
 * it back to its first element, the trap it wants, and every element it holds is reached, seen and
 * marked, none outside it. A menu moves the focus among its items by the arrows, and an editor
 * validates on Tab: the focus is checked to have entered them, not walked. What opened is audited
 * by axe — the cell, for an editor —, and the rest of the page by the rules the opening changes
 * there (`axeAudit`), then Escape closes it — a tooltip shown on what has the
 * focus first, as it must close first (WCAG 1.4.13) — and the focus is checked back on the trigger,
 * or on the cell: the one that holds the trigger, for a command a grid gives a row, the grid being
 * one stop. Every check is said apart, named by what it opened (`expect.soft`): a test plays every
 * trigger of a screen, one after the other.
 *
 * Left out: the cells whose own refusal is a dialog (`aria-haspopup` on a cell), which opens only
 * once the server refused; the triggers a grid holds row by row, but on the first row of their
 * column — the same dialog or the same menu, for another row; and what an item of a menu opens,
 * out of reach of Enter on the page.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { axeAudit } from "./axe";
import { faults, NO_FAULTS, walkByTab } from "./tab-walk";

/** What a gesture opens: a dialog, a menu, or the editor of a cell. */
export type Opening = "dialog" | "menu" | "editor";

/** What opens something, and what it opens. */
export interface Opener {
  readonly opens: Opening;
  /** The trigger by its role and its name, or the cell by its column and its grid. */
  readonly said: string;
  /** The trigger, or the cell. */
  readonly at: Locator;
}

/** The triggers of a dialog or of a menu, enabled, but a cell of a grid. */
const TRIGGERS =
  ':is([aria-haspopup="dialog"], [aria-haspopup="menu"]):not(td, th, :disabled, [aria-disabled="true"])';

/** The grids, whose first cell that takes an entry opens its editor. */
const GRIDS = '[role="grid"], [role="treegrid"]';

/** A cell of `DenseGrid` that takes an entry: placed by its column, and not read only. */
const ENTERABLE = "td[data-column]:not([aria-readonly])";

/** What opens a dialog, and what opens a menu. */
const OPENED = {
  dialog: '[role="dialog"], [role="alertdialog"]',
  menu: '[role="menu"]',
} as const;

/** What shows of a trigger, read in the page: whether it shows, what it opens, its name. */
interface Seen {
  readonly shown: boolean;
  readonly opens: string;
  readonly name: string;
  /** The column of the grid whose cell holds it, if a cell does, and the name of the grid. */
  readonly column: string | undefined;
}

/**
 * What opens something on the page as it is now, in the order of the page, the triggers before the
 * cells: each trigger shown, one per kind and name — one per column for those a grid holds row by
 * row, which open the same for each row —; the first cell of each grid that takes an entry.
 */
export async function openers(page: Page): Promise<Opener[]> {
  const triggers = page.locator(TRIGGERS);
  const seen = await triggers.evaluateAll(
    (elements, grids) =>
      elements.map((element): Seen => {
        const by = (element.getAttribute("aria-labelledby") ?? "")
          .split(" ")
          .map((id) => document.getElementById(id)?.textContent ?? "")
          .join(" ");
        const name = [element.getAttribute("aria-label"), by, element.textContent].find(
          (text) => typeof text === "string" && text.trim() !== "",
        );
        const cell = element.closest("td[data-column]");
        const grid = cell?.closest(grids)?.getAttribute("aria-label") ?? "";
        return {
          shown:
            element.checkVisibility({ visibilityProperty: true }) &&
            element.closest("[inert]") === null,
          opens: element.getAttribute("aria-haspopup") ?? "",
          name: (name ?? "").replace(/\s+/g, " ").trim(),
          column:
            cell === null ? undefined : `${cell.getAttribute("data-column") ?? ""} of « ${grid} »`,
        };
      }),
    GRIDS,
  );
  const found: Opener[] = [];
  const said = new Set<string>();
  for (const [index, { shown, opens, name, column }] of seen.entries()) {
    const role = `${opens === "menu" ? "menu" : "dialog"} « ${name} »`;
    const key = column === undefined ? role : `${opens} of the column ${column}`;
    if (shown && !said.has(key)) {
      said.add(key);
      found.push({
        opens: opens === "menu" ? "menu" : "dialog",
        said: `the trigger of the ${role}`,
        at: triggers.nth(index),
      });
    }
  }
  const grids = page.locator(GRIDS);
  for (const [index, name] of (
    await grids.evaluateAll((elements) => elements.map((grid) => grid.getAttribute("aria-label")))
  ).entries()) {
    const cell = grids.nth(index).locator(ENTERABLE).first();
    if ((await cell.count()) > 0 && (await cell.isVisible())) {
      const column = (await cell.getAttribute("data-column")) ?? "";
      found.push({
        opens: "editor",
        said: `the editor of the cell ${column} of the grid « ${name ?? ""} »`,
        at: cell,
      });
    }
  }
  return found;
}

/** Whether the focus is within an element, on it or on what it holds. */
function holdsFocus(element: Element): boolean {
  return element.contains(document.activeElement);
}

/** Whether the focus is in an element, on what it holds, and not on the element itself. */
function focusInside(element: Element): boolean {
  return element !== document.activeElement && element.contains(document.activeElement);
}

/**
 * Whether the focus is back on a trigger, or on the cell of a grid that holds it: a command of a
 * row gives the focus back to the cell, the one stop of the grid.
 */
function focusBack(trigger: Element): boolean {
  const focused = document.activeElement;
  return focused === trigger || (focused !== null && focused === trigger.closest("td"));
}

/** The assertions that say their failure and let the test go on. */
const softly = expect.configure({ soft: true });

/**
 * Open what an opener opens, by the keyboard, and say whether it opened: the dialog or the menu,
 * shown, or the editor, which took the focus in its cell.
 */
async function open(page: Page, opener: Opener): Promise<Locator | undefined> {
  // A trigger a cell holds is pressed from its cell, which the grid makes its active one, as the
  // arrows would: the grid gives the focus back to it.
  await opener.at.evaluate((at) => {
    const cell = at.closest("td");
    if (cell !== at && cell instanceof HTMLElement) {
      cell.focus();
    }
  });
  await opener.at.focus();
  await page.keyboard.press(opener.opens === "editor" ? "F2" : "Enter");
  if (opener.opens === "editor") {
    const entered = await expect
      .poll(() => opener.at.evaluate(focusInside))
      .toBe(true)
      .then(
        () => true,
        () => false,
      );
    expect.soft(entered, `${opener.said}: F2 opens it, the focus in the cell`).toBe(true);
    return entered ? page.locator(":focus") : undefined;
  }
  const opened = page.locator(OPENED[opener.opens]).filter({ visible: true });
  const shown = await expect(opened)
    .toHaveCount(1)
    .then(
      () => true,
      () => false,
    );
  expect.soft(shown, `${opener.said}: Enter opens one ${opener.opens}, shown`).toBe(true);
  return shown ? opened : undefined;
}

/**
 * Open what an opener opens, check it at the width of the window, and close it: a dialog walked by
 * Tab within itself, the focus checked in a menu or an editor, the page audited by axe, then
 * Escape, the focus back on the trigger or the cell. Every fault is said apart, named by the
 * opener and the width; what was found open still is closed by reloading the page (`reopen`), so
 * that the next opener starts from the screen.
 */
export async function checkOpened(
  page: Page,
  opener: Opener,
  width: string,
  reopen: () => Promise<void>,
): Promise<void> {
  const named = `${width}, ${opener.said}`;
  const errors = test.info().errors.length;
  const opened = await open(page, { ...opener, said: named });
  if (opened === undefined) {
    await reopen();
    return;
  }
  if (opener.opens === "dialog") {
    expect
      .soft(await opened.evaluate(holdsFocus), `${named}: the focus enters the dialog`)
      .toBe(true);
    const walk = await walkByTab(page, opened);
    expect.soft(walk.reached.length, `${named}: elements reached`).toBeGreaterThan(0);
    expect.soft(faults(walk), named).toEqual(NO_FAULTS);
  } else if (opener.opens === "menu") {
    expect
      .soft(await opened.evaluate(focusInside), `${named}: the focus enters the menu`)
      .toBe(true);
  }
  const { breaches, unmeasured } = await axeAudit(
    page,
    opener.opens === "editor" ? opener.at : opened,
  );
  expect.soft(breaches, `${named}: axe's rules for WCAG A and AA`).toEqual([]);
  if (Object.keys(unmeasured).length > 0) {
    test.info().annotations.push({
      type: "contrast left unmeasured by axe",
      description: `${named}: ${Object.entries(unmeasured)
        .map(([reason, count]) => `${reason}: ${String(count)}`)
        .join(", ")}`,
    });
  }
  // The tooltip of what has the focus closes on Escape first, as it must (WCAG 1.4.13).
  const tooltip = page.getByRole("tooltip");
  if ((await tooltip.count()) > 0) {
    await page.keyboard.press("Escape");
    await expect.soft(tooltip, `${named}: Escape closes the tooltip first`).toHaveCount(0);
  }
  await page.keyboard.press("Escape");
  if (opener.opens === "editor") {
    await expect.soft(opener.at, `${named}: Escape closes it, the focus on the cell`).toBeFocused();
  } else {
    await expect.soft(opened, `${named}: Escape closes it`).toHaveCount(0);
    await softly
      .poll(() => opener.at.evaluate(focusBack), {
        message: `${named}: the focus back on the trigger, or on the cell that holds it`,
      })
      .toBe(true);
  }
  if (test.info().errors.length > errors) {
    await reopen();
  }
}
