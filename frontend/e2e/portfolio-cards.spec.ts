// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The seven screens of the portfolio and the state of the system in cards (EP-25, US-2150,
 * WF-IHM-0100), against the fake back and measured rather than compared to an image, at the two
 * widths of the harness — 1366 points, then 911, what a zoom of 150 % leaves of it: each screen is
 * an airy column, centred and bounded to 96rem; each section, each table and each chart is a card,
 * the cards one under the other and none wider than the column; the filters of the perimeter lie in
 * a card of their own, above the view; the reading of the S-curve as cash-out is outlined at the
 * right of the title of its card, in reach. That the screens are walked entirely by the keyboard,
 * their contrast measured in both modes and nothing lost at 911 points is proven by
 * `accessibility.spec.ts`, which draws these screens from the table of the functions.
 */
import { expect, type Locator, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { untilHydrated } from "./hydration";

test.describe.configure({ mode: "parallel" });
test.slow();

const WINDOWS = [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
] as const;

/** The column bound of a screen of consultation, in pixels (`--container-column`, 96rem). */
const COLUMN = 1536;

const PERIMETER = "Périmètre du portefeuille";

/** What each screen holds, from the top: its cards by name, and the figures that stand in cards. */
const SCREENS = [
  {
    address: "/portfolio/projects",
    cards: [PERIMETER, "Valeur du portefeuille", "Projets du portefeuille"],
    figures: [],
  },
  {
    address: "/portfolio/workload",
    cards: [PERIMETER, "Charge par rôle et par mois"],
    figures: ["Charge empilée par rôle et par mois"],
  },
  {
    address: "/portfolio/performance",
    cards: [
      PERIMETER,
      "Indices agrégés",
      "Projections à terminaison",
      "Répartition des projets par zone",
    ],
    figures: ["Évolution trimestrielle des indices"],
  },
  {
    address: "/portfolio/cost-structure",
    cards: [
      PERIMETER,
      "Budget de référence par nature",
      "Reste à engager par nature",
      "Main-d’œuvre par nœud d’organisation",
    ],
    figures: [],
  },
  {
    address: "/portfolio/risks",
    cards: [
      PERIMETER,
      "Provisions des risques",
      "Couverture des risques",
      "Risques les plus lourds",
    ],
    figures: ["Matrice des risques"],
  },
  {
    address: "/portfolio/cost-curve",
    cards: [PERIMETER, "Courbe en S"],
    figures: ["Coûts cumulés du portefeuille"],
  },
  {
    address: "/portfolio/pilot-health",
    cards: [PERIMETER, "Signaux de santé du pilotage"],
    figures: [],
  },
  {
    address: "/system",
    cards: [
      "Alertes en cours",
      "Composants",
      "Espace de stockage",
      "Paramètres d’exploitation",
      "Dernières opérations",
    ],
    figures: [],
  },
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
  await page.goto(address);
  await untilHydrated(page);
}

for (const screen of SCREENS) {
  for (const size of WINDOWS) {
    test(`${screen.address}: sets each section, each table and each chart in a card, one under the other and inside the column, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
      page,
    }) => {
      await open(page, screen.address, size);
      const main = await box(page.locator("main"));
      let above = 0;
      for (const name of screen.cards) {
        const card = page.getByRole("region", { name, exact: true });
        await expect(card, `the card « ${name} »`).toHaveCount(1);
        await expect(
          card.locator("xpath=self::*[@data-slot='section-card']"),
          `« ${name} » is a card of section`,
        ).toHaveCount(1);
        const frame = await box(card);
        expect(frame.y, `« ${name} » not above the card before it`).toBeGreaterThanOrEqual(above);
        expect(frame.right, `« ${name} » inside the column`).toBeLessThanOrEqual(main.right + 1);
        expect(frame.x, `« ${name} » inside the column`).toBeGreaterThanOrEqual(main.x - 1);
        // Cards may stand side by side (two on a line from 1024 points): none starts above the one
        // before it.
        above = frame.y - 1;
      }
      for (const name of screen.figures) {
        const figure = page.getByRole("figure", { name });
        await expect(figure, `the chart « ${name} »`).toHaveCount(1);
        await expect(
          figure.locator("xpath=ancestor::*[@data-slot='card'][1]"),
          `« ${name} » in a card`,
        ).toHaveCount(1);
      }
      // Nothing goes out of the window sideways: a zoom of 150 % leaves no command out of reach.
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow, "the page does not scroll sideways").toBeLessThanOrEqual(1);
    });
  }

  test(`${screen.address}: the column of the screen is centred and bounded to 96rem [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, screen.address, { width: 2200, height: 900 });
    const main = await box(page.locator("main"));
    expect(main.width, "the column bounded").toBeLessThanOrEqual(COLUMN + 1);
    const area = await box(page.locator("main").locator("xpath=.."));
    expect(
      Math.abs(main.x - area.x - (area.right - main.right)),
      "the column centred",
    ).toBeLessThanOrEqual(2);
  });
}

for (const size of WINDOWS) {
  test(`sets the filters of the perimeter in a card above the view, in reach, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/portfolio/performance", size);
    const perimeter = page.getByRole("region", { name: PERIMETER, exact: true });
    const values = page.getByRole("region", { name: "Indices agrégés", exact: true });
    expect((await box(perimeter)).bottom, "the perimeter above the view").toBeLessThanOrEqual(
      (await box(values)).y + 1,
    );
    const states = perimeter.getByRole("button", { name: /États retenus/ });
    await states.scrollIntoViewIfNeeded();
    await expect(states).toBeInViewport({ ratio: 1 });
    const apply = perimeter.getByRole("button", { name: "Appliquer" });
    await apply.scrollIntoViewIfNeeded();
    await expect(apply).toBeInViewport({ ratio: 1 });
  });

  test(`sets the reading of the S-curve as cash-out, outlined, at the right of the title of its card, in reach, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/portfolio/cost-curve", size);
    const card = page.getByRole("region", { name: "Courbe en S", exact: true });
    const reading = card
      .locator("[data-slot='section-card-commands']")
      .getByRole("link", { name: "Lire en décaissements" });
    await reading.scrollIntoViewIfNeeded();
    await expect(reading).toBeInViewport({ ratio: 1 });
    const frame = await box(card);
    const heading = await box(card.getByRole("heading", { level: 2 }));
    const link = await box(reading);
    expect(link.x, "the reading after the title").toBeGreaterThan(heading.right);
    expect(frame.right - link.right, "the reading inside its card").toBeGreaterThan(0);
    expect(
      Math.abs(link.middle - heading.middle),
      "the reading on the line of the title",
    ).toBeLessThanOrEqual(8);
    // No principal command in the card: the reading outlined, nothing filled by the rule.
    await expect(card.locator("[data-slot='section-card-principal']")).toHaveCount(0);
    expect(
      await reading.evaluate((element) => getComputedStyle(element).backgroundColor),
      "the reading is outlined, not filled",
    ).not.toBe("rgb(0, 0, 0)");
  });

  test(`keeps the grid of the projects in its card, the totals row whole, at ${String(size.width)} points [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, "/portfolio/projects", size);
    const card = page.getByRole("region", { name: "Projets du portefeuille", exact: true });
    const grid = card.getByRole("grid");
    await expect(grid).toBeVisible();
    const frame = await box(card);
    // The frame of the grid, which clips and scrolls it: the grid itself is as wide as its columns.
    const inside = await box(grid.locator("xpath=.."));
    expect(inside.x, "the grid inside its card").toBeGreaterThan(frame.x);
    expect(inside.right, "the grid inside its card").toBeLessThanOrEqual(frame.right);
  });
}
