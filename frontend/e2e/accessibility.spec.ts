// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The minimal accessibility of every screen of the application (US-0200, WF-IHM-0100): those of
 * the table of the functions, drawn from `functions.json` as the links of `screens.spec.ts` are,
 * and those no table names (`routes.ts`), which `src/app/screens.test.ts` holds to the pages of
 * the application, and the grids of the planning and of the estimate on a differential, whose marks
 * tint their rows (US-0500). Each screen is opened by its address in a window of 1366 points, then narrowed
 * to 911 — what a zoom of 150 % leaves of 1366 points, the page reflowed as the browser reflows it
 * when its user zooms; a device scale factor would change the pixels, not the layout. At each
 * width:
 *
 * - axe's rules for WCAG A and AA hold — the contrast of every text among them, a text axe leaves
 *   « incomplete » with a measure that fails counted —, in the mode of a workstation set light and
 *   in that of one set dark, the charter painting both; in light mode, the rules that say a field
 *   has its label and an image its description are said apart; what axe left without a measure is
 *   noted, reason by reason;
 * - Tab, from where the focus is, reaches every element it may reach, each seen in the window and
 *   wearing its indicator of the focus, comes back to the first without being caught on the way
 *   (`walkByTab`), and reaches at 911 points every element it reached at 1366 (`lost`).
 *
 * The matrix of the risks, unfolded behind its command, is audited too, in both modes, and the
 * estimate with the tooltip of a command of the bar of its grid open (US-0580).
 *
 * What these tests leave unproven is written in the note of US-0200 (EP-14): what a gesture opens
 * — a dialog, a menu, the editor of a cell — is not walked, nor what a closed `details` holds.
 *
 * Each test is a screen and a check: they are spread one by one over the workers and over the
 * parts of the chain, not as a file. The session of the fake back grants the whole catalogue of
 * permissions: every command a screen can offer is offered. A browser in French.
 */
import { expect, type Page, test } from "@playwright/test";

import { type AxeBreach, axeAudit } from "./axe";
import { untilHydrated, WORKING } from "./hydration";
import { type AppScreen, DIFFERENTIAL_SCREENS, OTHER_SCREENS, tableScreens } from "./routes";
import { lost, type Walk, walkByTab } from "./tab-walk";

test.describe.configure({ mode: "parallel" });
// Each test opens a screen cold — compiling it, on the first visit to the development server —,
// then checks it twice, at each width: the walk by the keyboard presses Tab twice over every
// element of a page, three exchanges with the browser each, and the health of the steering lists
// two hundred projects.
test.slow();

/** The window of the harness, then the same window at a zoom of 150 %. */
const WINDOWS = [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
] as const;

/**
 * The rules of axe that say a field has its label and an image its description: `label` and
 * `image-alt`, with their kin for what is a field or an image without being an `input` or an
 * `img` — a list, a field or a switch of ARIA, a button drawn as an image, an image of ARIA or of
 * SVG, an area of a map, an object. All are rules of WCAG A, which the audit runs.
 */
const LABELS = [
  "label",
  "select-name",
  "aria-input-field-name",
  "aria-toggle-field-name",
  "image-alt",
  "input-image-alt",
  "role-img-alt",
  "svg-img-alt",
  "area-alt",
  "object-alt",
];

/** The background of the page in each mode, as the charter paints it (`theme.spec.ts`). */
const BACKGROUNDS = { light: "rgb(255, 255, 255)", dark: "rgb(10, 10, 10)" } as const;

/** Open a screen by its address, in the first window, named and hydrated. */
async function open(page: Page, screen: AppScreen): Promise<void> {
  await page.setViewportSize(WINDOWS[0]);
  await page.goto(screen.address);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(screen.name, {
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/**
 * Give the page a window, and the time to lay itself out in it: what measures its room — a grid
 * that renders the rows in view, the side bar — answers within two frames.
 */
async function resize(page: Page, size: (typeof WINDOWS)[number]): Promise<void> {
  await page.setViewportSize(size);
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(resolve));
      }),
  );
}

/** The breaches of the rules of the labels and the descriptions, or of every other rule. */
function labels(breaches: readonly AxeBreach[], wanted: boolean): AxeBreach[] {
  return breaches.filter((breach) => LABELS.includes(breach.rule) === wanted);
}

/** What a walk saw that it should not have, the elements it reached left aside. */
function faults(walk: Walk) {
  const { unseen, covered, unmarked, unjudged, trapped, missed, stopless, clipped } = walk;
  return {
    unseen,
    covered,
    unmarked,
    unjudged,
    trapped,
    missed,
    stopless,
    clipped,
    untabbable: walk.untabbable,
  };
}

for (const screen of [...tableScreens(), ...OTHER_SCREENS, ...DIFFERENTIAL_SCREENS]) {
  for (const mode of ["light", "dark"] as const) {
    test.describe(`a workstation in ${mode} mode`, () => {
      test.use({ colorScheme: mode });

      const named =
        mode === "light" ? "; every field labelled and every image described, at both widths" : "";
      test(`${screen.code} ${screen.route}, in ${mode} mode: no contrast below AA, nor any other breach of axe's rules for WCAG A and AA, at 1366 and at 911 points [WF-IHM-0100-A]${named}`, async ({
        page,
      }) => {
        await open(page, screen);
        // The mode asked is the one painted: the account follows the workstation, none forced.
        await expect(page.locator("html")).not.toHaveAttribute("data-theme");
        await expect(page.locator("body")).toHaveCSS("background-color", BACKGROUNDS[mode]);
        for (const size of WINDOWS) {
          await resize(page, size);
          const width = `${String(size.width)} points`;
          const { breaches, unmeasured } = await axeAudit(page);
          const reasons = Object.entries(unmeasured).map(
            ([reason, count]) => `${reason}: ${String(count)}`,
          );
          test.info().annotations.push({
            type: "contrast left unmeasured by axe",
            description: `${width}: ${reasons.length === 0 ? "none" : reasons.join(", ")}`,
          });
          if (mode === "light") {
            expect.soft(labels(breaches, true), `${width}: labels and descriptions`).toEqual([]);
            expect
              .soft(labels(breaches, false), `${width}: axe's rules for WCAG A and AA`)
              .toEqual([]);
          } else {
            expect.soft(breaches, `${width}: axe's rules for WCAG A and AA`).toEqual([]);
          }
        }
      });
    });
  }

  if (screen.route === "/projects/[projectId]/revisions/[revisionId]/estimate") {
    for (const mode of ["light", "dark"] as const) {
      test.describe(`a workstation in ${mode} mode, a tooltip open`, () => {
        test.use({ colorScheme: mode });

        test(`${screen.code} ${screen.route}, in ${mode} mode, the tooltip of a command of the bar of the grid open on its focus: no contrast below AA, nor any other breach of axe's rules for WCAG A and AA [WF-IHM-0100-A]`, async ({
          page,
        }) => {
          await open(page, screen);
          await expect(page.locator("body")).toHaveCSS("background-color", BACKGROUNDS[mode]);
          // The tooltip of the command opens on its focus, and describes it by its help (US-0580).
          const columns = page.getByRole("button", { name: "Colonnes", exact: true });
          await columns.focus();
          await expect(page.getByRole("tooltip")).toHaveText(
            "Choisit les colonnes que la grille montre.",
          );
          await expect(columns).toHaveAccessibleDescription(
            "Choisit les colonnes que la grille montre.",
          );
          const { breaches } = await axeAudit(page);
          expect.soft(breaches, "axe's rules for WCAG A and AA").toEqual([]);
          // Escape closes it, the focus left on the command.
          await page.keyboard.press("Escape");
          await expect(page.getByRole("tooltip")).toHaveCount(0);
          await expect(columns).toBeFocused();
        });
      });
    }
  }

  if (screen.route === "/projects/[projectId]/revisions/[revisionId]/risks") {
    for (const mode of ["light", "dark"] as const) {
      test.describe(`a workstation in ${mode} mode, the matrix unfolded`, () => {
        test.use({ colorScheme: mode });

        test(`${screen.code} ${screen.route}, in ${mode} mode, the matrix of the risks unfolded: no contrast below AA, nor any other breach of axe's rules for WCAG A and AA, at 1366 and at 911 points [WF-IHM-0100-A]`, async ({
          page,
        }) => {
          await open(page, screen);
          await expect(page.locator("html")).not.toHaveAttribute("data-theme");
          await expect(page.locator("body")).toHaveCSS("background-color", BACKGROUNDS[mode]);
          // The matrix starts folded behind its command, which says so.
          const toggle = page.getByRole("button", { name: "Graphique", exact: true });
          await expect(toggle).toHaveAttribute("aria-expanded", "false");
          await toggle.click();
          await expect(toggle).toHaveAttribute("aria-expanded", "true");
          await expect(
            page.getByRole("img", { name: /^Nuage de bulles des risques/ }).locator("svg"),
          ).toBeVisible();
          for (const size of WINDOWS) {
            await resize(page, size);
            const { breaches, unmeasured } = await axeAudit(page);
            const reasons = Object.entries(unmeasured).map(
              ([reason, count]) => `${reason}: ${String(count)}`,
            );
            test.info().annotations.push({
              type: "contrast left unmeasured by axe",
              description: `${String(size.width)} points: ${reasons.length === 0 ? "none" : reasons.join(", ")}`,
            });
            expect
              .soft(breaches, `${String(size.width)} points: axe's rules for WCAG A and AA`)
              .toEqual([]);
          }
        });
      });
    }
  }

  test(`${screen.code} ${screen.route}: Tab reaches every control, each seen in the window with its focus shown, and comes back to the first without a trap, at 1366 points and at 911, where it reaches all it reached at 1366 [WF-IHM-0100-A]`, async ({
    page,
  }) => {
    await open(page, screen);
    const walks: Walk[] = [];
    for (const size of WINDOWS) {
      await resize(page, size);
      const walk = await walkByTab(page);
      const width = `${String(size.width)} points`;
      expect.soft(walk.reached.length, `${width}: elements reached`).toBeGreaterThan(0);
      expect.soft(faults(walk), width).toEqual({
        unseen: [],
        covered: [],
        unmarked: [],
        unjudged: [],
        trapped: undefined,
        missed: [],
        stopless: [],
        clipped: [],
        untabbable: [],
      });
      walks.push(walk);
    }
    const [wide, narrow] = walks;
    expect
      .soft(lost(wide?.reached ?? [], narrow?.reached ?? []), "reached at 1366, lost at 911")
      .toEqual([]);
  });
}
