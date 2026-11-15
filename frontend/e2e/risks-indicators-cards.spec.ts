// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risks and the indicators of a project in cards (EP-25, US-2150, WF-IHM-0100), measured
 * rather than compared to an image, at the two widths of the harness — 1366 points, then 911, what
 * a zoom of 150 % leaves of it: each section of the indicators — the milestones, the cumulative
 * costs, the earned value — is a region named by its title, the shift of the costs at the right of
 * the title of its card; the matrix and the coverage of the risks are cards, the matrix as wide as
 * the register, named once; no command goes out of reach.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated } from "./hydration";

test.describe.configure({ mode: "parallel" });
test.slow();

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const INDICATORS = `/projects/${PROJECT}/revisions/${REVISION}/indicators`;
const RISKS = `/projects/${PROJECT}/revisions/${REVISION}/risks`;

/** The column bound of a screen of consultation, in pixels (`--container-column`, 96rem). */
const COLUMN = 1536;

const WINDOWS = [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
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
    bottom: measured.y + measured.height,
    middle: measured.y + measured.height / 2,
  };
}

/** Open a screen in a window, hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await compile(page.request, address);
  await page.setViewportSize(size);
  await openHydrated(page, address);
}

/** How far the column of the screen is from the centre of the area that holds it, in pixels. */
async function offCentre(page: Page): Promise<number> {
  const main = await box(page.locator("main"));
  const area = await box(page.locator("main").locator("xpath=.."));
  return Math.abs(main.x - area.x - (area.right - main.right));
}

for (const size of WINDOWS) {
  test(`sets each section of the indicators in a card named by its title, the shift of the costs at the right of its title, in reach, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, INDICATORS, size);
    let above = 0;
    for (const name of ["Suivi des jalons", "Coûts cumulés", "Courbes de valeur acquise"]) {
      const card = page.getByRole("region", { name, exact: true });
      await expect(card, `the card « ${name} »`).toHaveCount(1);
      const frame = await box(card);
      expect(frame.y, `« ${name} » under the card before it`).toBeGreaterThanOrEqual(above);
      above = frame.bottom - 1;
    }
    const costs = page.getByRole("region", { name: "Coûts cumulés", exact: true });
    const shift = costs
      .locator("[data-slot='section-card-commands']")
      .getByRole("link", { name: "Décaler des délais de paiement" });
    // At 150 %, the command stays in reach: scrolled to, it lies whole in the window.
    await shift.scrollIntoViewIfNeeded();
    await expect(shift).toBeInViewport({ ratio: 1 });
    const frame = await box(costs);
    const heading = await box(costs.getByRole("heading", { level: 2 }));
    const link = await box(shift);
    expect(link.x, "the shift after the title").toBeGreaterThan(heading.right);
    expect(frame.right - link.right, "the shift inside its card").toBeGreaterThan(0);
    expect(
      Math.abs(link.middle - heading.middle),
      "the shift on the line of the title",
    ).toBeLessThanOrEqual(8);
    // A shift is no principal command: nothing in the card is filled by the rule.
    await expect(costs.locator("[data-slot='section-card-principal']")).toHaveCount(0);
  });
}

test("keeps the column of the indicators centred and bounded to 96rem [WF-IHM-0100-A]", async ({
  page,
}) => {
  await open(page, INDICATORS, { width: 2200, height: 900 });
  const main = await box(page.locator("main"));
  expect(main.width, "the column bounded").toBeLessThanOrEqual(COLUMN + 1);
  expect(await offCentre(page), "the column centred").toBeLessThanOrEqual(2);
  await page.setViewportSize({ width: 1366, height: 768 });
  expect(await offCentre(page), "the column centred at 1366").toBeLessThanOrEqual(2);
});

for (const size of WINDOWS) {
  test(`sets the coverage and the matrix of the risks in cards, the matrix as wide as the register and named once, its commands in reach, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, RISKS, size);
    const grid = page.getByRole("grid", { name: "Registre des risques" });
    const coverage = page.getByRole("region", { name: "Couverture des risques" });
    await expect(coverage).toBeVisible();
    const figure = page.getByRole("figure", { name: "Matrice des risques" });
    const card = figure.locator("xpath=ancestor::*[@data-slot='card'][1]");
    await expect(card, "the matrix in a card").toHaveCount(1);
    // One title: the caption of the figure; neither a heading nor a region repeats it.
    await expect(page.getByText("Matrice des risques", { exact: true })).toHaveCount(1);
    await expect(page.getByRole("region", { name: "Matrice des risques" })).toHaveCount(0);
    // The card of the matrix lies between the coverage and the register, as wide as the register.
    const matrixBox = await box(card);
    const coverageBox = await box(coverage);
    const registerBox = await box(grid.locator("xpath=.."));
    expect(matrixBox.y, "the matrix under the coverage").toBeGreaterThan(coverageBox.bottom - 1);
    expect(matrixBox.bottom, "the matrix above the register").toBeLessThan(registerBox.y + 1);
    expect(matrixBox.width, "the card as wide as the register").toBeGreaterThan(
      registerBox.width - 1,
    );
    // Its commands stay in reach, wherever the window cuts the page.
    const toggle = figure.getByRole("button", { name: "Graphique", exact: true });
    await toggle.scrollIntoViewIfNeeded();
    await expect(toggle).toBeInViewport({ ratio: 1 });
    const exported = figure.getByRole("button", { name: /^Exporter/ });
    await exported.scrollIntoViewIfNeeded();
    await expect(exported).toBeInViewport({ ratio: 1 });
  });
}
