// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/indicators`;

// The first series of a chart in the token `--chart-1`, as the browser resolves it in each mode.
const SERIES_LIGHT = "rgb(2, 112, 179)";
const SERIES_DARK = "rgb(17, 149, 225)";

test.use({ colorScheme: "light" });

// A chart is drawn by ECharts from an effect, once the page is hydrated: each visit opens the
// screen hydrated (`openHydrated`), and its drawings are awaited from there.

test("draws the evolution of an index in SVG, an image described in a sentence, its values in a table [WF-IHM-0100-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  await expect(page.getByRole("heading", { level: 1, name: "Indicateurs projets" })).toBeVisible();
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator("svg")).toBeVisible();
  // The thresholds of the reference, drawn by a series of their own.
  await expect(cost.locator("svg text", { hasText: "Seuil de vigilance" })).toBeAttached();
  await expect(cost.locator("svg text", { hasText: "Seuil d’alerte" })).toBeAttached();
  const figure = page.getByRole("figure", { name: "Évolution de l’indice de coût" });
  await figure.getByText("Valeurs du graphique").click();
  const row = figure.getByRole("row", { name: /^Projet entier Révision en cours/ });
  await row.scrollIntoViewIfNeeded();
  await expect(row).toBeInViewport();
  // The date of the evolution, under the caption of its figure.
  await expect(figure.getByText(/^Calculé le/)).toBeVisible();
});

test("paints its series with the tokens of the charter, drawn again when the account forces the dark mode", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`).first()).toBeAttached();
  // The attribute the root layout sets for an account that chose `dark`.
  await page.locator("html").evaluate((html) => {
    html.setAttribute("data-theme", "dark");
  });
  await expect(cost.locator(`path[stroke="${SERIES_DARK}"]`).first()).toBeAttached();
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`)).toHaveCount(0);
});

test("names each curve at its end, two names ending close together drawn apart, their letters never overlapping", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const schedule = page.getByRole("img", { name: /^Courbes de l’indice de délai du projet/ });
  // The whole project and what belongs to no sub-project end close on the current day, at
  // 0.9879 and 1.
  const project = schedule.locator("svg text", { hasText: /^Projet entier$/ });
  const unassigned = schedule.locator("svg text", { hasText: /^Hors sous-projet$/ });
  await expect(project).toBeAttached();
  await expect(unassigned).toBeAttached();
  // The baselines of the two names are at least the size of their font apart: their letters
  // do not overlap. ECharts writes where it places a name in its transform.
  const placed = async (name: typeof project) => {
    const [transform, size] = await name.evaluate((text) => [
      text.getAttribute("transform") ?? "",
      getComputedStyle(text).fontSize,
    ]);
    const baseline = /translate\([\d.]+ ([\d.]+)\)/.exec(transform)?.[1];
    return { baseline: Number(baseline), size: Number.parseFloat(size) };
  };
  const [a, b] = await Promise.all([placed(project), placed(unassigned)]);
  expect(Math.abs(a.baseline - b.baseline)).toBeGreaterThanOrEqual(Math.max(a.size, b.size));
});

test("exports a curve, at the keyboard, as a PNG image drawn on a canvas, named after the project", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const figure = page.getByRole("figure", { name: "Diagramme temps/temps" });
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  await command.focus();
  await expect(command).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.keyboard.press("Enter"),
  ]);
  expect(download.suggestedFilename()).toBe("suivi-des-jalons-PRJ-001.png");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(chunk as Buffer);
  }
  const image = Buffer.concat(chunks);
  // The signature of a PNG, then the width and the height of its header: an image of its own
  // size, twice as dense as the screen, whatever the size of the window.
  expect(image.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  expect([image.readUInt32BE(16), image.readUInt32BE(20)]).toEqual([2560, 1440]);
  // The instance out of the screen is gone with its canvas.
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("draws the cumulative costs, and shifts them by the payment delays at the server's", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  // The drawing itself, named by its sentence: the figure holds the icon of its export too.
  await expect(
    page
      .getByRole("figure", { name: "Courbe en S" })
      .getByRole("img", { name: /^Courbes cumulées du budget de référence/ })
      .locator("svg"),
  ).toBeVisible();
  await page.getByRole("link", { name: "Décaler des délais de paiement" }).click();
  await expect(page).toHaveURL(/payment_delays=true/);
});

/**
 * A script fetched for the page on a connection of its own: one kept open across a held script
 * was closed by the front as idle while the journey reused it (ECONNRESET, under load).
 */
const ONE_USE = { connection: "close" };

/** The methods of a page that open it and read its cookies: `openHydrated` reads the shell so. */
const OPENS = new Set<PropertyKey>(["context", "url"]);

/**
 * A page whose screen is let hydrate, by `release`, at the first moment it is read: what opens
 * the page or reads its cookies does not read the screen. The page is opened from its first
 * response on — its load waits for the scripts the screen is held by — and `held` is awaited
 * before `goto` returns, so that what opens the page starts its own bound only then, whole for the
 * hydration alone, whatever the load took to hold the scripts.
 */
function releasedAtRead(page: Page, held: () => Promise<void>, release: () => void): Page {
  return new Proxy(page, {
    get(target, property): unknown {
      const value: unknown = Reflect.get(target, property, target);
      if (typeof value !== "function") {
        return value;
      }
      const method = value as (...args: unknown[]) => unknown;
      if (property === "goto") {
        return async (address: string) => {
          const response = await target.goto(address, { waitUntil: "commit" });
          await held();
          return response;
        };
      }
      if (OPENS.has(property)) {
        return method.bind(target);
      }
      return (...args: unknown[]): unknown => {
        release();
        return method.apply(target, args);
      };
    },
  });
}

/** How many commands of the charts — the screen's own — the page shows, and React has hydrated. */
function chartCommands(): { shown: number; hydrated: number } {
  const commands = [...document.querySelectorAll("figure button")];
  return {
    shown: commands.length,
    hydrated: commands.filter((command) =>
      Object.keys(command).some((key) => key.startsWith("__reactProps$")),
    ).length,
  };
}

test("opens the screen hydrated, though the shell has written its cookie before the screen hydrated", async ({
  page,
}) => {
  // The shell writes its cookie from an effect, once it has hydrated; the screen hydrates in the
  // boundary of its `loading.tsx`, after it. Under load, the cookie came seconds before the screen,
  // and a chart awaited from it for five seconds was never drawn (#1537). The page hydrates only
  // once all its scripts are loaded, the shell's with the screen's: the scripts of the charts are
  // held here, nothing hydrates, and the cookie is written as the shell writes it — the page as the
  // load left it, given whatever the load. The screen is let hydrate at the first moment the
  // opening reads the page, once the test has seen it so.
  let release = (): void => undefined;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  await page.route("**/_next/static/chunks/**", async (route) => {
    const response = await page.request.get(route.request().url(), { headers: ONE_USE });
    const body = await response.body();
    if (body.includes("data-probe")) {
      await page.context().addCookies([
        {
          name: "wf_last_project",
          value: encodeURIComponent(SCREEN),
          url: new URL(route.request().url()).origin,
        },
      ]);
      held += 1;
      await released;
    }
    await route.fulfill({ status: response.status(), headers: response.headers(), body });
  });
  // The page as the load left it: scripts held, cookie written, no button hydrated.
  const heldScreen = async (): Promise<void> => {
    await expect.poll(() => held, { timeout: WORKING }).toBeGreaterThan(0);
    const cookies = await page.context().cookies();
    expect(cookies.map(({ name }) => name)).toContain("wf_last_project");
    await expect
      .poll(() => page.evaluate(chartCommands), { timeout: WORKING })
      .toEqual({ shown: 3, hydrated: 0 });
  };
  const opening = releasedAtRead(page, heldScreen, release);
  const opened = openHydrated(opening, SCREEN).then(() => page.evaluate(chartCommands));
  // A late rejection, if the test fails before `opened` is awaited, must not hide that failure.
  void opened.catch(() => undefined);
  try {
    expect(await opened).toEqual({ shown: 3, hydrated: 3 });
  } finally {
    release();
    // The scripts the screen loads once hydrated — those of the charts — are still being fetched,
    // some of them asked as the test ends: a route removed under a request it has just caught
    // continues that request, and the handler's `fulfill` then fails ("Route is already handled").
    // The page is left to load them all, held by the route, before the route is removed.
    await page.waitForLoadState("networkidle");
    await page.unrouteAll({ behavior: "wait" });
  }
});
