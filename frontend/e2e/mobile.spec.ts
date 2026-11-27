// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The views of the indicators of a project and of the portfolio on a screen of 360 points
 * (WF-CMP-0010-A, US-0290): they read there, without scrolling sideways, and offer no input — no
 * field that writes, no editable cell, no command of writing. The filters of reading stay (decision
 * of the author of 2026-10-09). The project `mobile` plays these paths alone, in Chromium's engine
 * as a phone's (`playwright.config.ts`, tag `@mobile`): `make e2e-compat`.
 */
import { expect, type Page } from "@playwright/test";

import { openHydrated, untilHydrated } from "./hydration";
import { test } from "./mode";

const REVISION =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102";

const VIEWS = [
  { title: "Indicateurs projets", address: `${REVISION}/indicators` },
  { title: "Portefeuille de projets", address: "/portfolio/projects" },
  { title: "Performance du portefeuille", address: "/portfolio/performance" },
  { title: "Courbe en S du portefeuille", address: "/portfolio/cost-curve" },
  { title: "Structure des coûts du portefeuille", address: "/portfolio/cost-structure" },
  { title: "Santé du pilotage", address: "/portfolio/pilot-health" },
  { title: "Risques du portefeuille", address: "/portfolio/risks" },
  { title: "Plan de charge agrégé", address: "/portfolio/workload" },
];

// A command of writing, by the name its button bears.
const WRITING =
  /^(Enregistrer|Ajouter|Créer|Nouveau|Nouvelle|Supprimer|Importer|Modifier|Marquer|Abandonner|Restaurer|Valider|Copier|Dupliquer)/i;

/** The fields of the page that are no filter of reading: a search, a date, a choice, a bound « du » or « au ». */
async function fieldsOfWriting(page: Page): Promise<string[]> {
  return page
    .locator("input, textarea, select, [contenteditable]:not([contenteditable=false])")
    .evaluateAll((fields) =>
      fields
        .filter((field) => {
          const type = field.getAttribute("type") ?? "text";
          const name = field.getAttribute("aria-label") ?? "";
          const reading =
            field.tagName === "SELECT" ||
            type === "search" ||
            type === "date" ||
            type === "hidden" ||
            / (du|au)$/.test(name.replace(/,/g, ""));
          return !reading;
        })
        .map((field) => `${field.tagName} ${field.getAttribute("aria-label") ?? ""}`),
    );
}

for (const view of VIEWS) {
  test(`reads ${view.title} on 360 points without scrolling sideways, and offers no input @mobile [WF-CMP-0010-A]`, async ({
    page,
  }) => {
    const sent: string[] = [];
    page.on("request", (request) => {
      if (request.method() !== "GET") {
        sent.push(`${request.method()} ${request.url()}`);
      }
    });
    if (view.address.startsWith("/portfolio")) {
      await page.goto(view.address);
      await untilHydrated(page);
    } else {
      await openHydrated(page, view.address);
    }
    expect(page.viewportSize()?.width).toBe(360);
    await expect(page.getByRole("heading", { level: 1, name: view.title })).toBeVisible();
    // Read whole: the page is no wider than the screen.
    const widths = await page.evaluate(() => ({
      page: document.documentElement.scrollWidth,
      screen: document.documentElement.clientWidth,
    }));
    expect(widths.page).toBeLessThanOrEqual(widths.screen);
    // No field that writes, no command of writing, no cell that can be edited.
    expect(await fieldsOfWriting(page)).toEqual([]);
    const buttons = await page
      .getByRole("button")
      .evaluateAll((all) =>
        all.map((button) => (button.getAttribute("aria-label") ?? button.textContent).trim()),
      );
    expect(buttons.filter((name) => WRITING.test(name))).toEqual([]);
    // Keys typed in a cell of a grid — focused, for the pinned label covers the others at 360 points — open no field.
    const cells = page.getByRole("gridcell");
    if ((await cells.count()) > 1) {
      await cells.nth(1).focus();
      for (const key of ["Enter", "F2", "5"]) {
        await page.keyboard.press(key);
      }
      await expect(page.getByRole("grid").getByRole("textbox")).toHaveCount(0);
      expect(await fieldsOfWriting(page)).toEqual([]);
    }
    expect(sent).toEqual([]);
  });
}
