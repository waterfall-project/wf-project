// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screens of the accounts, of the access roles, of the backups and of the journal of audit in
 * cards (EP-25, US-2100), measured rather than compared to an image: at the two widths of the
 * harness — 1366 points, then 911, what a zoom of 150 % leaves of it — each section is a card whose
 * commands stand at the right of its title, on its line, the principal one filled and the others
 * outlined (WF-IHM-0100); the column of the screen is centred and bounded; the card of the accounts
 * ends right under the lowest text or control it shows, within its padding; the matrix of the
 * permissions keeps its header and its column « Fonction » in view as it scrolls (#3088); «
 * Sauvegarder maintenant » is filled, and the deposit of a backup of another installation a card
 * whose « Déposer » stands at the right of its field; the journal of audit is tight, fills its
 * window, its table in a card without a title of section, no count under its title, its column «
 * Projet » whole. That the screens are walked entirely by the keyboard, their contrast measured in
 * both modes and nothing lost at 911 points is proven by `accessibility.spec.ts`, which draws these
 * screens from the table of the functions.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { compile } from "./compile";
import { untilHydrated } from "./hydration";

test.describe.configure({ mode: "parallel" });
test.slow();

const WINDOWS = [
  { width: 1366, height: 900 },
  { width: 911, height: 900 },
] as const;

/** The column bound of a screen of settings or of consultation, in pixels (`--container-column`, 96rem). */
const COLUMN = 1536;

/** The box of an element in the page, measured. */
async function box(element: Locator) {
  const measured = await element.boundingBox();
  if (measured === null) {
    throw new Error("the element is not laid out");
  }
  return {
    ...measured,
    right: measured.x + measured.width,
    bottom: measured.y + measured.height,
    middle: measured.y + measured.height / 2,
  };
}

/** The background a button is painted on. */
function backgroundOf(button: Locator): Promise<string> {
  return button.evaluate((element) => getComputedStyle(element).backgroundColor);
}

/**
 * How far the bottom of a card is under the lowest text or control it shows. Only real content is
 * measured — every text node, by a `Range` over it, so that a text bare beside an element
 * (`<p>Total <b>3</b></p>`) counts as the one in a leaf does, and the controls and icons — never a
 * wrapper, which would stretch with a card stretched itself (flex-1, h-full, min-height): the card
 * must end right under the lowest of them, within its padding.
 */
function slackUnder(card: Locator): Promise<number> {
  return card.evaluate((element) => {
    const bottom = element.getBoundingClientRect().bottom;
    let lowest = 0;
    const note = (rect: DOMRect) => {
      if (rect.height > 0 && rect.width > 0) {
        lowest = Math.max(lowest, rect.bottom);
      }
    };
    for (const control of element.querySelectorAll(
      "button, input, select, textarea, a, svg, img",
    )) {
      note(control.getBoundingClientRect());
    }
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
      if ((node.textContent ?? "").trim() === "") continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        note(rect);
      }
    }
    return bottom - lowest;
  });
}

/** Open a screen in a window, until its first table shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await compile(page.request, address);
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid']").first()).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
}

/** Expect a command at the right of the title of a card, on the line of the title. */
async function expectAtTitle(card: Locator, command: Locator, what: string) {
  const frame = await box(card);
  const heading = await box(card.getByRole("heading", { level: 2 }));
  const button = await box(command);
  expect(button.x, `${what} after the title`).toBeGreaterThan(heading.right);
  expect(frame.right - button.right, `${what} at the right edge of its card`).toBeGreaterThan(0);
  expect(frame.right - button.right, `${what} inside the padding of its card`).toBeLessThanOrEqual(
    32,
  );
  expect(
    Math.abs(button.middle - heading.middle),
    `${what} on the line of the title`,
  ).toBeLessThanOrEqual(8);
}

for (const size of WINDOWS) {
  test(`sets the accounts in a card whose creation is filled at the right of its title, as tall as its content, and the reading of the identity provider in a card of its own, its command outlined at the right of its title, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/users", size);
    const accounts = page.getByRole("region", { name: "Comptes utilisateurs", exact: true });
    const create = accounts.getByRole("button", { name: "Créer un compte local" });
    await expectAtTitle(accounts, create, "« Créer un compte local »");
    const reading = page.getByRole("region", {
      name: "Lecture des comptes du fournisseur d’identité",
      exact: true,
    });
    const read = reading.getByRole("button", { name: "Lire les comptes" });
    await expectAtTitle(reading, read, "« Lire les comptes »");
    // The creation is the one filled command of its card, the reading outlined, its state in the body.
    const filled = await backgroundOf(create);
    expect(filled).not.toBe("rgba(0, 0, 0, 0)");
    expect(await backgroundOf(read), "the reading is outlined, not filled").not.toBe(filled);
    await expect(
      reading
        .getByText("Aucune lecture des comptes n’a encore abouti.")
        .or(reading.getByRole("time")),
    ).toBeVisible();
    // The cards one under the other, none over the next; the card of the accounts takes the height of
    // its content: it ends within its padding under the lowest text or control it shows.
    const first = await box(accounts);
    const second = await box(reading);
    expect(first.bottom, "the accounts above the reading").toBeLessThanOrEqual(second.y);
    const slack = await slackUnder(accounts);
    expect(slack, "the content of the accounts stays inside its card").toBeGreaterThanOrEqual(0);
    expect(slack, "no band under the content of the accounts").toBeLessThanOrEqual(40);
    // No menu « ⋯ » is left.
    await expect(page.getByRole("button", { name: /état et commandes/ })).toHaveCount(0);
  });

  test(`sets the roles in a card whose « Nouveau rôle » is filled at the right of its title, and opens a dialog, no field in line, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/access-roles", size);
    const roles = page.getByRole("region", { name: "Rôles d’habilitation", exact: true });
    const create = roles.getByRole("button", { name: "Nouveau rôle" });
    await expectAtTitle(roles, create, "« Nouveau rôle »");
    expect(await backgroundOf(create)).not.toBe("rgba(0, 0, 0, 0)");
    await expect(page.getByRole("textbox", { name: "Nouveau rôle" })).toHaveCount(0);
    await expect(page.getByRole("form", { name: "Création d’un rôle" })).toHaveCount(0);
    await create.click();
    const dialog = page.getByRole("dialog", { name: "Création d’un rôle" });
    await expect(dialog.getByRole("textbox", { name: "Libellé" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(create).toBeFocused();
  });

  test(`keeps the header of the matrix of the permissions and its column « Fonction » in view as it scrolls, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/access-roles", size);
    const matrix = page.getByRole("table", { name: "Permissions par fonction" });
    const frame = matrix.locator("xpath=..");
    const header = matrix.getByRole("columnheader", { name: "Fonction", exact: true });
    // The frame is bounded: the matrix scrolls within it, a header that stays at its top.
    const scrolls = await frame.evaluate((element) => ({
      vertical: element.scrollHeight - element.clientHeight,
      horizontal: element.scrollWidth - element.clientWidth,
    }));
    expect(scrolls.vertical, "the matrix scrolls within its frame").toBeGreaterThan(0);
    await frame.evaluate((element) => {
      element.scrollTop = element.scrollHeight;
      element.scrollLeft = element.scrollWidth;
    });
    const edge = await box(frame);
    const head = await box(header);
    expect(Math.abs(head.y - edge.y), "the header at the top of its frame").toBeLessThanOrEqual(3);
    // The last function of the catalogue is in view, under the header; the column « Fonction » at
    // the start of the frame, whatever the sideways scroll.
    expect(
      head.x - edge.x,
      "the column « Fonction » at the start of its frame",
    ).toBeLessThanOrEqual(3);
    const groups = matrix.locator('th[scope="rowgroup"]');
    const visible = await groups.evaluateAll(
      (cells, bound) => {
        return cells.filter((cell) => {
          const rect = cell.getBoundingClientRect();
          return rect.bottom > bound.top + 30 && rect.top < bound.bottom;
        }).length;
      },
      { top: edge.y, bottom: edge.bottom },
    );
    expect(visible, "a function in view under the header").toBeGreaterThan(0);
    if (scrolls.horizontal > 0) {
      const group = groups.first();
      await frame.evaluate((element) => {
        element.scrollTop = 0;
      });
      const left = await box(group);
      expect(
        left.x - edge.x,
        "a function kept at the start while scrolled sideways",
      ).toBeLessThanOrEqual(3);
    }
  });
}

for (const address of ["/admin/users", "/admin/access-roles"] as const) {
  test(`${address}: the column of the screen is centred and bounded to 96rem, in a window wider than it`, async ({
    page,
  }) => {
    await open(page, address, { width: 2200, height: 900 });
    const main = await box(page.locator("main"));
    expect(main.width, "the column bounded").toBeLessThanOrEqual(COLUMN + 1);
    const area = await box(page.locator("main").locator("xpath=.."));
    const before = main.x - area.x;
    const after = area.right - main.right;
    expect(Math.abs(before - after), "the column centred").toBeLessThanOrEqual(2);
    expect(before, "room on both sides of the column").toBeGreaterThan(0);
  });
}

for (const size of WINDOWS) {
  test(`sets « Sauvegarder maintenant » filled at the right of the title of the card of the backups, and the deposit of another installation in a card, « Déposer » at the right of its field, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/backups", size);
    const backups = page.getByRole("region", { name: "Sauvegardes", exact: true });
    const start = backups.getByRole("button", { name: "Sauvegarder maintenant" });
    await expectAtTitle(backups, start, "« Sauvegarder maintenant »");
    expect(await backgroundOf(start), "filled, the principal command of its card").not.toBe(
      "rgba(0, 0, 0, 0)",
    );
    const deposit = page.getByRole("region", {
      name: "Restaurer une sauvegarde d’une autre installation",
      exact: true,
    });
    await expect(deposit.locator("xpath=self::*[@data-slot='section-card']")).toHaveCount(1);
    const field = await box(deposit.getByLabel("Archive de la sauvegarde"));
    const send = deposit.getByRole("button", { name: "Déposer" });
    const sending = await box(send);
    expect(sending.x, "« Déposer » at the right of its field").toBeGreaterThanOrEqual(field.right);
    expect(
      Math.abs(sending.middle - field.middle),
      "« Déposer » on the line of its field",
    ).toBeLessThanOrEqual(12);
    expect(await backgroundOf(send), "« Déposer » is outlined, not filled").not.toBe(
      await backgroundOf(start),
    );
    const cards = await Promise.all([box(backups), box(deposit)]);
    expect(cards[0].bottom, "the list above the deposit").toBeLessThanOrEqual(cards[1].y);
  });

  test(`sets the journal of audit tight in a card without a title of section, which fills the window, no count under its title, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/audit-log", size);
    // No count under the title; the totals row of the grid says it.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Journal d’audit");
    const grid = page.getByRole("grid", { name: "Journal d’audit" });
    await expect(grid.getByRole("row").last()).toHaveText("43 inscriptions");
    await expect(page.getByText("43 inscriptions")).toHaveCount(1);
    // The table is in a card, which has no title of section: no region named by a heading.
    const card = page.locator('main [data-slot="grid-card"]');
    await expect(card).toHaveCount(1);
    await expect(card.locator('[data-slot="card-title"]')).toHaveCount(0);
    await expect(card.getByRole("heading")).toHaveCount(0);
    await expect(card.getByRole("grid", { name: "Journal d’audit" })).toBeVisible();
    // It fills the window: its foot is in it, close to its bottom, the page not scrolling.
    const frame = await box(card);
    expect(frame.bottom, "the card ends in the window").toBeLessThanOrEqual(size.height + 1);
    expect(size.height - frame.bottom, "the card fills the window").toBeLessThanOrEqual(48);
    const grown = await page.evaluate(
      () => document.documentElement.scrollHeight - window.innerHeight,
    );
    expect(grown, "the page does not scroll").toBeLessThanOrEqual(1);
  });

  test(`shows the column « Projet » of the journal of audit whole, none of its cells cut, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/admin/audit-log", size);
    const cells = page
      .getByRole("grid", { name: "Journal d’audit" })
      .getByRole("gridcell", { name: /PRJ-001 · Modernisation du poste de commande/ });
    expect(await cells.count()).toBeGreaterThan(0);
    const cut = await cells.evaluateAll((all) =>
      all.filter((cell) => cell.scrollWidth > cell.clientWidth).map((cell) => cell.textContent),
    );
    expect(cut, "no cell of the project cut").toEqual([]);
  });
}
