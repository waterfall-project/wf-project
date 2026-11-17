// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources in cards (EP-25, US-2110/L1), measured rather than compared to an
 * image: at the two widths of the harness — 1366 points, then 911, what a zoom of 150 % leaves of
 * it — « Nouveau nœud », « Nouveau rôle » and « Nouveau calendrier » are filled at the right of the
 * title of their card, on its line; « Modifier les unités de durée » is outlined at the right of the
 * title of its card; the bar of the tree orders « Filtres », « Colonnes », « Arbre ». That the
 * screen is walked entirely by the keyboard, its contrast measured in both modes and nothing lost at
 * 911 points is proven by `accessibility.spec.ts`; the width of the tables, by `grid-frame.spec.ts`.
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

/** The box of an element in the page, measured. */
async function box(element: Locator) {
  const measured = await element.boundingBox();
  if (measured === null) {
    throw new Error("the element is not laid out");
  }
  return {
    ...measured,
    right: measured.x + measured.width,
    middle: measured.y + measured.height / 2,
  };
}

/** The background a button is painted on. */
function backgroundOf(button: Locator): Promise<string> {
  return button.evaluate((element) => getComputedStyle(element).backgroundColor);
}

/** Expect a command at the right of the title of a card, on the line of the title. */
async function expectAtTitle(card: Locator, command: Locator, what: string) {
  const frame = await box(card);
  const heading = await box(card.getByRole("heading", { level: 2 }));
  const button = await box(command);
  expect(button.x, `${what} after the title`).toBeGreaterThan(heading.right);
  expect(frame.right - button.right, `${what} inside its card`).toBeGreaterThan(0);
  expect(frame.right - button.right, `${what} inside the padding of its card`).toBeLessThanOrEqual(
    32,
  );
  expect(
    Math.abs(button.middle - heading.middle),
    `${what} on the line of the title`,
  ).toBeLessThanOrEqual(8);
}

/** Open the screen in a window, until its first table shows and the page is hydrated. */
async function open(page: Page, size: { width: number; height: number }) {
  const address = "/reference/resources";
  await compile(page.request, address);
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='treegrid']").first()).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
}

for (const size of WINDOWS) {
  test(`sets the creation of a node, of a role and of a calendar filled at the right of the title of its card, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, size);
    for (const [title, creation] of [
      ["Arbre d’organisation", "Nouveau nœud"],
      ["Rôles de ressources", "Nouveau rôle"],
      ["Calendriers", "Nouveau calendrier"],
    ] as const) {
      const card = page.getByRole("region", { name: title, exact: true });
      const button = card.getByRole("button", { name: creation });
      await expectAtTitle(card, button, `« ${creation} »`);
      expect(await backgroundOf(button), `« ${creation} » filled`).not.toBe("rgba(0, 0, 0, 0)");
    }
  });

  test(`sets « Modifier les unités de durée » outlined at the right of the title of its card, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, size);
    const card = page.getByRole("region", { name: "Unités de durée", exact: true });
    const button = card.getByRole("button", { name: "Modifier les unités de durée" });
    await expectAtTitle(card, button, "« Modifier les unités de durée »");
    const style = await button.evaluate((element) => {
      const computed = getComputedStyle(element);
      return { border: computed.borderTopColor, width: computed.borderTopWidth };
    });
    expect(style.width, "outlined: a border").not.toBe("0px");
    expect(style.border, "outlined: a visible border").not.toBe("rgba(0, 0, 0, 0)");
    expect(await backgroundOf(button), "outlined: on the background of the page, not filled").toBe(
      await page.evaluate(() => getComputedStyle(document.body).backgroundColor),
    );
  });

  test(`orders the bar of the tree: its filters, its columns, then « Arbre », at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, size);
    const card = page.getByRole("region", { name: "Arbre d’organisation", exact: true });
    const filters = await box(card.getByRole("button", { name: /^Filtres/ }));
    const columns = await box(card.getByRole("button", { name: /^Colonnes/ }));
    const tree = await box(card.getByRole("button", { name: /^Arbre/ }));
    expect(columns.x, "« Colonnes » after « Filtres »").toBeGreaterThan(filters.right - 1);
    expect(tree.x, "« Arbre » after « Colonnes »").toBeGreaterThan(columns.right - 1);
    expect(Math.abs(tree.middle - columns.middle), "one line").toBeLessThanOrEqual(8);
  });
}
