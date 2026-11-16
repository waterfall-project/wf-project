// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { WORKING } from "./bounds";
import { axeViolations } from "./axe";
import { holdRoute, setExpanded, untilHydrated } from "./hydration";
import { path } from "./routes";

// The account of the fake back follows the workstation (`theme: default`): the mode the
// browser asks for alone decides the colours of the charter. The logo is on the side bar, midnight
// blue in both modes, and is there in its variant for a dark ground whatever the mode (US-2070).

/** The background the page is painted in, and the variant of the logo shown. */
async function shown(page: Page) {
  const background = await page
    .locator("body")
    .evaluate((body) => getComputedStyle(body).backgroundColor);
  const logo = await page
    .getByRole("img", { name: "Waterfall" })
    .evaluate((image: HTMLImageElement) => new URL(image.currentSrc).pathname);
  return { background, logo };
}

test.describe("a workstation in dark mode", () => {
  test.use({ colorScheme: "dark" });

  test("gets the dark tokens of the charter and the dark logo", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).not.toHaveAttribute("data-theme");
    expect(await shown(page)).toEqual({
      background: "rgb(11, 17, 27)",
      logo: "/waterfall_logo-dark.svg",
    });
  });

  test("is painted light when the account forces the light mode", async ({ page }) => {
    await page.goto("/");
    // The attribute the root layout sets for an account that chose `light`: the fake back
    // serves an account that follows the workstation, so it is set here as the layout would.
    await page.locator("html").evaluate((html) => {
      html.setAttribute("data-theme", "light");
    });
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(243, 245, 248)");
  });
});

test.describe("a workstation in light mode", () => {
  test.use({ colorScheme: "light" });

  test("gets the light tokens of the charter, and the logo for a dark ground on the dark bar", async ({
    page,
  }) => {
    await page.goto("/");
    expect(await shown(page)).toEqual({
      background: "rgb(243, 245, 248)",
      logo: "/waterfall_logo-dark.svg",
    });
  });

  test("is painted dark when the account forces the dark mode", async ({ page }) => {
    await page.goto("/");
    await page.locator("html").evaluate((html) => {
      html.setAttribute("data-theme", "dark");
    });
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(11, 17, 27)");
  });
});

/** The background a cell is painted on. */
function backgroundOf(cell: Locator): Promise<string> {
  return cell.evaluate((element) => getComputedStyle(element).backgroundColor);
}

// The access roles set a dense grid and a list one above the other: the grid of the roles, and the
// matrix of the permissions (#508) — the settings of costs, which set them side by side before, hold
// dense grids alone since EP-02/L42a.
for (const mode of ["light", "dark"] as const) {
  test.describe(`the tables of a workstation in ${mode} mode`, () => {
    test.use({ colorScheme: mode });

    test("sets the header row of a list and of a dense grid on the same muted background, its text legible [WF-IHM-0100-A]", async ({
      page,
    }) => {
      await page.goto("/admin/access-roles");
      const list = page.getByRole("table", { name: "Permissions par fonction" });
      const grid = page.getByRole("grid", { name: "Rôles d’habilitation" });
      const listHeader = list.getByRole("columnheader").first();
      const gridHeader = grid.getByRole("columnheader", { name: "Comptes porteurs" });
      await expect(gridHeader).toBeVisible();
      const header = await backgroundOf(listHeader);
      expect(await backgroundOf(gridHeader)).toBe(header);
      // A colour of its own, neither transparent nor that of the page the rows of the list show.
      expect(header).not.toBe("rgba(0, 0, 0, 0)");
      expect(header).not.toBe(await backgroundOf(page.locator("body")));
      // Un contrôle automatisé de contraste ne relève aucun écart au niveau AA: in the head of
      // every table of the screen.
      expect(await axeViolations(page, "thead")).toEqual([]);
    });
  });
}

// The side bar is midnight blue in both modes (EP-25, US-2070): the tokens its entries name take
// the values of the bar inside it, which the browser alone resolves.
for (const mode of ["light", "dark"] as const) {
  test.describe(`the side bar of a workstation in ${mode} mode`, () => {
    test.use({ colorScheme: mode });

    test("is midnight blue, its labels and its entries legible on it [WF-IHM-0100-A]", async ({
      page,
    }) => {
      await page.goto("/");
      const bar = page.locator('[data-sidebar="sidebar"]');
      await expect(bar).toHaveCSS("background-color", "rgb(15, 27, 45)");
      // A label of a group, written `text-muted-foreground` for the page: the muted light of the bar.
      await expect(bar.locator('[data-sidebar="group-label"]').first()).toHaveCSS(
        "color",
        "rgb(159, 176, 200)",
      );
      // Un contrôle automatisé de contraste ne relève aucun écart au niveau AA: on the dark bar.
      expect(await axeViolations(page, '[data-sidebar="sidebar"]')).toEqual([]);
    });

    test("is walked by the keyboard, the focus drawn on it in the bright blue of the logo, at 1366 points and at 911 [WF-IHM-0100-A]", async ({
      page,
    }) => {
      // Chaque écran se parcourt entièrement au clavier et le focus reste visible : on the dark bar
      // too, and at 911 points — what a zoom of 150 % leaves of 1366 — the bar still beside the page.
      for (const width of [1366, 911]) {
        await page.setViewportSize({ width, height: 768 });
        await page.goto("/");
        const bar = page.locator('[data-sidebar="sidebar"]');
        await expect(bar).toBeVisible();
        const logo = bar.getByRole("link", { name: "Waterfall" });
        // From the top of the document, Tab reaches the logo, the first stop of the bar.
        await page.keyboard.press("Tab");
        await expect(logo).toBeFocused();
        await expect(logo).toHaveCSS("box-shadow", /rgb\(17, 149, 225\)/);
        // The project switcher, then the entries: each drawn with the ring of the bar.
        for (let step = 0; step < 3; step += 1) {
          await page.keyboard.press("Tab");
          const focused = page.locator(":focus");
          await expect(focused).toBeInViewport();
          expect(
            await focused.evaluate(
              (element) => element.closest('[data-sidebar="sidebar"]') !== null,
            ),
          ).toBe(true);
          await expect(focused).toHaveCSS("box-shadow", /rgb\(17, 149, 225\)/);
        }
      }
    });

    test("is midnight blue as the sheet of a narrow window, legible on it [WF-IHM-0100-A]", async ({
      page,
    }) => {
      await page.setViewportSize({ width: 500, height: 800 });
      await page.goto("/");
      await page.getByRole("button", { name: /barre latérale/ }).click();
      const sheet = page.locator('[data-sidebar="sidebar"][data-mobile="true"]');
      await expect(sheet).toBeVisible();
      await expect(sheet).toHaveCSS("background-color", "rgb(15, 27, 45)");
      // Un contrôle automatisé de contraste ne relève aucun écart au niveau AA: on the sheet.
      expect(await axeViolations(page, '[data-sidebar="sidebar"][data-mobile="true"]')).toEqual([]);
    });
  });
}

// The two families of screens (US-2070; EP-25, « Deux familles d'écrans, dites par Screen »),
// measured in a window wider than the column: a screen of settings is a column bounded to 96rem
// (`max-w-column`, from `--container-column`), centred in what the side bar leaves; a screen of
// work fills it. A test of the classes would pass on a utility Tailwind never generated.
test.describe("the two families of screens, in a window of 2560 points", () => {
  test.use({ viewport: { width: 2560, height: 1440 } });

  /** Where `main` lies in the part of the window the side bar leaves to the page. */
  async function placed(page: Page) {
    // The screen, not the skeleton of its loading (dense, and without a heading) that precedes it.
    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1 })).toBeVisible();
    const inset = await page.locator('[data-slot="sidebar-inset"]').boundingBox();
    const box = await main.boundingBox();
    if (inset === null || box === null) {
      throw new Error("the page or its main content is not laid out");
    }
    return {
      main,
      width: box.width,
      page: inset.width,
      left: box.x - inset.x,
      right: inset.x + inset.width - (box.x + box.width),
    };
  }

  test("sets a screen of settings in a column of 1536 points at most, centred in the page", async ({
    page,
  }) => {
    await page.goto("/reference/costs");
    const shown = await placed(page);
    await expect(shown.main).toHaveCSS("max-width", "1536px");
    // The page is wider than the column: the column takes its bound, no more.
    expect(shown.page).toBeGreaterThan(1536);
    expect(shown.width).toBeCloseTo(1536, 0);
    expect(Math.abs(shown.left - shown.right)).toBeLessThanOrEqual(1);
  });

  // A screen of settings reached by a click shows the skeleton of its segment first, held here by
  // its payload: the skeleton takes the template of the screen — the airy column, not the dense
  // width of the home it leaves —, and the screen replaces it without a jump (#3269).
  test("lays the skeleton of a screen of settings where the screen comes", async ({ page }) => {
    await page.goto("/");
    await untilHydrated(page);
    const nav = page.getByRole("navigation", { name: "Fonctions" });
    // The skeleton shows at the click only once the router has prefetched it, with the link. The
    // router asks first for the tree of the routes (`next-router-segment-prefetch: /_tree`), which
    // answers well before the segment that holds the skeleton: that one is the prefetch awaited.
    const prefetched = page.waitForResponse((response) => {
      const headers = response.request().headers();
      return (
        new URL(response.url()).pathname === "/reference/costs" &&
        headers["next-router-prefetch"] === "1" &&
        headers["next-router-segment-prefetch"] === undefined
      );
    });
    await setExpanded(
      nav.getByRole("button", { name: "Paramètres applicatifs", exact: true }),
      true,
    );
    await prefetched;
    await page.waitForLoadState("networkidle");
    const held = await holdRoute(page, "**/reference/costs?**", async (route, released) => {
      const headers = route.request().headers();
      if (headers.rsc === "1" && headers["next-router-prefetch"] !== "1") {
        await released;
      }
    });
    let skeleton: { x: number; width: number } | null;
    try {
      await nav.getByRole("link", { name: "Paramètres de coûts" }).click();
      const loading = page.getByRole("main", { name: "Chargement de l’écran" });
      await expect(loading).toBeVisible({ timeout: WORKING });
      skeleton = await loading.boundingBox();
    } finally {
      await held.release();
    }
    const shown = await placed(page);
    expect(skeleton).not.toBeNull();
    // The column of 1536 points, centred: the skeleton, then the screen in its very place.
    expect(skeleton?.width).toBeCloseTo(1536, 0);
    expect(skeleton?.width).toBeCloseTo(shown.width, 0);
    const box = await shown.main.boundingBox();
    expect(skeleton?.x).toBeCloseTo(box?.x ?? Number.NaN, 0);
  });

  test("lets a screen of work fill the width the side bar leaves", async ({ page }) => {
    await page.goto(path("/projects/[projectId]/revisions/[revisionId]/planning"));
    const shown = await placed(page);
    await expect(shown.main).toHaveCSS("max-width", "none");
    expect(shown.page).toBeGreaterThan(1536);
    expect(shown.width).toBeCloseTo(shown.page, 0);
    expect(shown.left).toBeCloseTo(0, 0);
  });
});
