// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The views of the indicators of a project and of the portfolio on a screen of 360 points
 * (WF-CMP-0010-A, US-0290): they read there, without scrolling sideways, and offer no input — no
 * field that writes, no editable cell, no command of writing. The filters of reading stay (decision
 * of the author of 2026-10-09). The project `mobile` plays these paths alone, in Chromium's engine
 * as a phone's (`playwright.config.ts`, tag `@mobile`): `make e2e-compat`.
 */
import { expect, type Locator, type Page } from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import { WORKING } from "./bounds";
import { openHydrated, untilHydrated } from "./hydration";
import { test } from "./mode";

const REVISION =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102";

interface View {
  title: string;
  address: string;
  /** What the screen holds once it is read, not its skeleton: a described image, a card, a grid. */
  witness: (page: Page) => Locator;
  /** A grid: keys typed in a cell of it open no field. */
  grid?: true;
}

const region = (name: string) => (page: Page) => page.getByRole("region", { name, exact: true });
const image = (name: RegExp) => (page: Page) => page.getByRole("img", { name }).first();

const VIEWS: View[] = [
  {
    title: "Indicateurs projets",
    address: `${REVISION}/indicators`,
    witness: image(/^Courbes de l’indice de coût du projet/),
  },
  {
    title: "Portefeuille de projets",
    address: "/portfolio/projects",
    witness: (page) => page.getByRole("grid", { name: catalogue.grid.names.portfolioProjects }),
    grid: true,
  },
  {
    title: "Performance du portefeuille",
    address: "/portfolio/performance",
    witness: image(/^Courbes de l’indice de coût et de l’indice de délai agrégés/),
  },
  {
    title: "Courbe en S du portefeuille",
    address: "/portfolio/cost-curve",
    witness: image(/^Courbes cumulées, mois par mois, du budget de référence/),
  },
  {
    title: "Structure des coûts du portefeuille",
    address: "/portfolio/cost-structure",
    witness: region(catalogue.portfolio.costStructure.remaining),
  },
  {
    title: "Santé du pilotage",
    address: "/portfolio/pilot-health",
    witness: region(catalogue.portfolio.pilotHealth.signals),
  },
  {
    title: "Risques du portefeuille",
    address: "/portfolio/risks",
    witness: image(/^Nuage de bulles des risques/),
  },
  {
    title: "Plan de charge agrégé",
    address: "/portfolio/workload",
    witness: image(/^Barres empilées de la charge/),
  },
];

/**
 * The commands of writing, by the verbs the French catalogue gives them: the texts at the keys that
 * name a command of writing (`save`, `create`, `add`, `delete`…), cut before their first
 * placeholder. A hand-written regular expression would drift from the catalogue; this one follows
 * it, and the test below fails if it comes up empty.
 */
const WRITING_KEYS = new Set([
  "save",
  "create",
  "add",
  "delete",
  "submit",
  "import",
  "modify",
  "restore",
  "abandon",
  "designate",
]);

function writingVerbs(node: unknown, key = "", found = new Set<string>()): Set<string> {
  if (typeof node === "string") {
    const verb = node.split("{")[0]?.trim() ?? "";
    if (WRITING_KEYS.has(key) && verb.length >= 4) {
      found.add(verb);
    }
  } else if (typeof node === "object" && node !== null) {
    for (const [name, child] of Object.entries(node)) {
      writingVerbs(child, name, found);
    }
  }
  return found;
}

const VERBS = [...writingVerbs(catalogue)];

test("knows the commands of writing from the catalogue @mobile [WF-CMP-0010-A]", () => {
  expect(VERBS).toEqual(expect.arrayContaining(["Enregistrer", "Supprimer", "Créer"]));
});

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

/** The names of the buttons, links and menu items of the page that bear a verb of writing. */
async function commandsOfWriting(page: Page): Promise<string[]> {
  const names: string[] = [];
  for (const role of ["button", "link", "menuitem"] as const) {
    const all = await page
      .getByRole(role)
      .evaluateAll((elements) =>
        elements.map((element) =>
          (element.getAttribute("aria-label") ?? element.textContent).trim(),
        ),
      );
    names.push(...all.map((name) => `${role} ${name}`));
  }
  return names.filter((entry) => {
    const name = entry.slice(entry.indexOf(" ") + 1);
    return VERBS.some((verb) => name.startsWith(verb));
  });
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
    // The shell writes the context of a project from an effect, which `openHydrated` awaits; the
    // portfolio has none, its screens are awaited hydrated where they stand.
    if (view.address.startsWith("/portfolio")) {
      await page.goto(view.address);
      await untilHydrated(page);
    } else {
      await openHydrated(page, view.address);
    }
    expect(page.viewportSize()?.width).toBe(360);
    await expect(page.getByRole("heading", { level: 1, name: view.title })).toBeVisible();
    // The screen is read, not its skeleton: its content shows before anything is measured.
    await expect(view.witness(page)).toBeVisible({ timeout: WORKING });
    // Read whole: the page is no wider than the screen.
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        ),
      )
      .toBeLessThanOrEqual(0);
    // No field that writes, no command of writing, no cell that can be edited.
    expect(await fieldsOfWriting(page)).toEqual([]);
    expect(await commandsOfWriting(page)).toEqual([]);
    if (view.grid) {
      // Keys typed in a cell of a grid — focused, for the pinned label covers the others at 360 points — open no field.
      const cells = page.getByRole("gridcell");
      await expect(cells.nth(1)).toBeVisible({ timeout: WORKING });
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
