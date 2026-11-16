// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the risks and of the indicators and the correspondence of the actual costs in the
 * layout of EP-25 (US-2110/L2), measured at the two widths of the
 * harness — 1366 points, then 911, what a zoom of 150 % leaves of it: « Modifier … » outlined at the
 * right of the title of the screen, on its line; the two cards of the correspondence, its fields
 * bounded to a reading width, its save filled below them. That
 * these screens are walked entirely by the keyboard, their contrast measured in both modes and
 * nothing lost at 911 points is proven by `accessibility.spec.ts`.
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
  return { ...measured, right: measured.x + measured.width, bottom: measured.y + measured.height };
}

/** Open a screen in a window, until its title shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await compile(page.request, address);
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: WORKING });
  await untilHydrated(page);
}

for (const size of WINDOWS) {
  const at = `at ${String(size.width)} points`;

  for (const [address, command] of [
    ["/reference/risks", "Modifier la matrice de risques"],
    ["/reference/indicators", "Modifier les seuils et le délai"],
  ] as const) {
    test(`sets « ${command} » outlined at the right of the title of the screen ${at}`, async ({
      page,
    }) => {
      await open(page, address, size);
      const button = page.getByRole("main").getByRole("button", { name: command });
      const title = await box(page.getByRole("heading", { level: 1 }));
      const measured = await box(button);
      // At 911 points the command may wrap under the title; it never stands before it.
      expect(measured.x, "after the start of the title").toBeGreaterThanOrEqual(title.x);
      if (size.width >= 1366) {
        expect(measured.x, "after the end of the title").toBeGreaterThanOrEqual(
          title.x + title.width,
        );
        const gap = Math.abs(measured.y + measured.height / 2 - (title.y + title.height / 2));
        expect(gap, "on the line of the title").toBeLessThanOrEqual(title.height);
      }
      expect(measured.right, "inside the window").toBeLessThanOrEqual(size.width);
      const style = await button.evaluate((element) => getComputedStyle(element).borderTopWidth);
      expect(style, "outlined: a border").not.toBe("0px");
    });
  }

  test(`sets the correspondence in two cards, its fields bounded, its save below ${at}`, async ({
    page,
  }) => {
    await open(page, "/reference/costs/actual-cost-mapping", size);
    const read = page.getByRole("region", { name: "Colonnes lues", exact: true });
    const kept = page.getByRole("region", { name: "Colonnes conservées", exact: true });
    const save = page.getByRole("button", { name: "Enregistrer la correspondance" });
    const keptBox = await box(kept);
    expect((await box(read)).bottom, "the cards stacked").toBeLessThanOrEqual(keptBox.y + 1);
    expect((await box(save)).x, "the save at the foot").toBeGreaterThanOrEqual(keptBox.x);
    expect((await box(save)).y, "the save below the cards").toBeGreaterThanOrEqual(keptBox.bottom);
    const field = read.getByRole("textbox").first();
    expect((await box(field)).width, "a field no wider than a reading line").toBeLessThanOrEqual(
      576,
    );
  });
}
