// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { WORKING } from "./bounds";
import catalogue from "../messages/fr.json" with { type: "json" };
import { formatPlanningDate } from "../src/i18n/format";
import { pngSize } from "./download";
import { holdScripts, openHydrated } from "./hydration";
import {
  expectCards,
  expectCurvePoints,
  expectIndexPoints,
  expectMilestonePoints,
  type CurveSeries,
  type IndexHistory,
  LOCALE,
  type Indicators,
  type MilestoneTracking,
  ok,
  type Reader,
  readerOf,
} from "./indicator-answers";
import { inService, test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/indicators`;

// The first series of a chart in the token `--chart-1`, as the browser resolves it in each mode.
const SERIES_LIGHT = "rgb(61, 106, 158)";
const SERIES_DARK = "rgb(130, 169, 217)";

test.use({ colorScheme: "light" });

// A chart is drawn by ECharts from an effect, once the page is hydrated: each visit opens the
// screen hydrated (`openHydrated`), and its drawings are awaited from there.

test("draws the evolution of an index in SVG, an image described in a sentence, its values in a table @browsers @shared [WF-IHM-0100-A] [WF-CMP-0010-A]", async ({
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

test("paints its series with the tokens of the charter, drawn again when the account forces the dark mode @shared", async ({
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

test("names each curve at its end, two names ending close together drawn apart, their letters never overlapping @browsers @shared [WF-CMP-0010-A]", async ({
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

test("exports a curve, at the keyboard, as a PNG image drawn on a canvas, named after the project @shared [WF-IHM-0100-A] [WF-IHM-0130-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const figure = page.getByRole("figure", {
    name: catalogue.projectIndicators.milestones.chartTitle,
  });
  const command = figure.getByRole("button", { name: catalogue.chart.exportPng });
  await command.focus();
  await expect(command).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.keyboard.press("Enter"),
  ]);
  expect(download.suggestedFilename()).toBe("suivi-des-jalons-PRJ-001.png");
  // The signature of a PNG checked, then the width and the height of its header: an image of its
  // own size, twice as dense as the screen, whatever the size of the window.
  expect(await pngSize(download)).toEqual([2560, 1440]);
  // The instance out of the screen is gone with its canvas.
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("draws the cumulative costs, and shifts them by the payment delays at the server's @browsers @shared [WF-CMP-0010-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  // The drawing itself, named by its sentence: the figure holds the icon of its export too.
  await expect(
    page
      .getByRole("figure", { name: catalogue.projectIndicators.costCurve.chartTitle })
      .getByRole("img", { name: /^Courbes cumulées du budget de référence/ })
      .locator("svg"),
  ).toBeVisible();
  await page.getByRole("link", { name: catalogue.projectIndicators.costCurve.delay }).click();
  await expect(page).toHaveURL(/payment_delays=true/);
});

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

test("opens the screen hydrated, though the shell has written its cookie before the screen hydrated @shared", async ({
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
  const scripts = await holdScripts(page, async ({ url, body }) => {
    if (body.includes("data-probe")) {
      await page.context().addCookies([
        {
          name: "wf_last_project",
          value: encodeURIComponent(SCREEN),
          url: new URL(url).origin,
        },
      ]);
      held += 1;
      await released;
    }
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
  // A rejection of `opened` must not be reported unhandled, whatever ends the test. This catch
  // swallows nothing: `opened` is awaited just below, first in the `try`, on every path — nothing
  // before it can throw —, and that await gets its rejection and fails the test with it; the
  // catch is only a second listener (#1808).
  void opened.catch(() => undefined);
  try {
    expect(await opened).toEqual({ shown: 3, hydrated: 3 });
  } finally {
    release();
    // The scripts the screen loads once hydrated — those of the charts — are still being fetched,
    // some of them asked as the test ends: the route is taken away once they are served (#1635).
    await scripts.remove();
  }
});

// The paths below hold the screen to the answers of the service for PRJ-001 (US-1730,
// WF-ARC-0070-A): each reads the operations the screen reads, by the API under the token of the
// account of the run, for the revision, the date and the scope of the address, and compares what the
// screen shows to the answer. The fake back serves one example whatever it is asked: nothing to
// compare there.
const ONLY_IN_SERVICE = "the fake back serves one example whatever the address asks";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const MARKED = "01926f3a-7c00-7000-8000-000000000101";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const BASE = `/projects/${PROJECT}`;
const INDICATORS = `${BASE}/indicators`;
const HISTORY = `${INDICATORS}/index-history`;
const COSTS = `${INDICATORS}/cost-curve`;
const VALUE = `${INDICATORS}/earned-value-curves`;
const TRACKING = `${INDICATORS}/milestone-tracking`;
const NAMES = catalogue.projectIndicators;

/** The screen of the indicators of a revision, under an address, and the query it reads by. */
function screenOf(revision: string, query: string): string {
  return `${BASE}/revisions/${revision}/indicators${query === "" ? "" : `?${query}`}`;
}

/** The scopes the screen is held to: the whole project, a sub-project, what belongs to none. */
const SCOPES = [
  { title: "the whole project", address: "", scope: {} },
  {
    title: "a sub-project",
    address: `subproject_id=${SUBPROJECT}`,
    scope: { scope: SUBPROJECT },
  },
  {
    title: "what belongs to no sub-project",
    address: "subproject_id=unassigned",
    scope: { scope: "unassigned" },
  },
] as const;

/** The two curve figures of the screen — the cost curve, the earned value — held to their answers. */
async function expectCurves(
  main: Locator,
  reader: Reader,
  query: Record<string, string>,
  { delayed = false }: { readonly delayed?: boolean } = {},
) {
  const costs = await ok<CurveSeries>(
    reader,
    COSTS,
    delayed ? { ...query, payment_delays: "true" } : query,
  );
  const value = await ok<CurveSeries>(reader, VALUE, query);
  await expectCurvePoints(
    main.getByRole("figure", {
      name: delayed ? NAMES.costCurve.chartTitleDelayed : NAMES.costCurve.chartTitle,
    }),
    costs,
    reader,
    { cashOut: delayed },
  );
  await expectCurvePoints(
    main.getByRole("figure", { name: NAMES.earnedValue.chartTitle }),
    value,
    reader,
  );
}

for (const { title, address, scope } of SCOPES) {
  test(`shows the cards of the revision in progress, the evolution of its indices and its two curves, as the service answers for ${title} @shared [WF-ARC-0070-A]`, async ({
    page,
    browser,
    request,
    manager,
  }) => {
    test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
    test.slow();
    const reader = await readerOf(browser, request, manager);
    const query = { revision_id: REVISION, ...scope };
    const indicators = await ok<Indicators>(reader, INDICATORS, query);
    const history = await ok<IndexHistory>(reader, HISTORY, scope);
    expect(indicators.context.is_stored).toBe(false);
    await openHydrated(page, screenOf(REVISION, address));
    const main = page.getByRole("main");
    await expectCards(main, indicators, reader);
    await expectIndexPoints(
      main.getByRole("figure", { name: NAMES.history.costTitle }),
      history,
      "cost_index",
    );
    await expectIndexPoints(
      main.getByRole("figure", { name: NAMES.history.scheduleTitle }),
      history,
      "schedule_index",
    );
    await expectCurves(main, reader, query);
  });
}

test("shows the time/time diagram as the service answers, the diagram of the whole project under a sub-project @shared [WF-ARC-0070-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
  test.slow();
  const reader = await readerOf(browser, request, manager);
  // The tracking of the milestones takes no scope: the project whole, whatever the address filters.
  const tracking = await ok<MilestoneTracking>(reader, TRACKING);
  await openHydrated(page, screenOf(REVISION, `subproject_id=${SUBPROJECT}`));
  const main = page.getByRole("main");
  await expectMilestonePoints(
    main.getByRole("figure", { name: NAMES.milestones.chartTitle }),
    tracking,
  );
  await expect(main.getByText(NAMES.wholeProject.milestones)).toBeVisible();
});

test("shifts the cumulative costs by the payment delays as the service answers, the cash-out by month with them @shared [WF-ARC-0070-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
  test.slow();
  const reader = await readerOf(browser, request, manager);
  const delays = { revision_id: REVISION, payment_delays: "true" };
  const delayed = await ok<CurveSeries>(reader, COSTS, delays);
  expect(delayed.payment_delays).toBe(true);
  await openHydrated(page, screenOf(REVISION, "payment_delays=true"));
  await expectCurves(page.getByRole("main"), reader, { revision_id: REVISION }, { delayed: true });
});

test("reads the revision 101, marked, as its marking kept it, and says the evolution of the indices is computed on another revision @shared [WF-ARC-0070-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
  test.slow();
  const reader = await readerOf(browser, request, manager);
  const indicators = await ok<Indicators>(reader, INDICATORS, { revision_id: MARKED });
  expect(indicators.context.is_stored).toBe(true);
  expect(indicators.context.revision_id).toBe(MARKED);
  await openHydrated(page, screenOf(MARKED, ""));
  const main = page.getByRole("main");
  await expectCards(main, indicators, reader);
  await expectCurves(main, reader, { revision_id: MARKED });
  await expect(main.getByText(NAMES.elsewhere.title)).toBeVisible();
});

test("says an offer refused by the service, no card and no curve of its own, the tracking of the milestones kept @shared [WF-ARC-0070-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
  const reader = await readerOf(browser, request, manager);
  const refused = await reader.get(INDICATORS, { revision_id: OFFER });
  expect(refused.status).toBe(409);
  await openHydrated(page, screenOf(OFFER, ""));
  const main = page.getByRole("main");
  await expect(main.getByText(NAMES.notInProgress.title)).toBeVisible();
  await expect(main.getByRole("region", { name: NAMES.financial.title })).toHaveCount(0);
  await expect(main.getByRole("figure", { name: NAMES.costCurve.chartTitle })).toHaveCount(0);
  await expect(main.getByRole("figure", { name: NAMES.milestones.chartTitle })).toBeVisible();
});

test("reads the indicators at a date as the service answers, the revision of the calculation named, and says a date before any marking refused @shared [WF-ARC-0070-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService || manager === undefined, ONLY_IN_SERVICE);
  test.slow();
  const reader = await readerOf(browser, request, manager);
  const asOf = "2026-05-31";
  const indicators = await ok<Indicators>(reader, INDICATORS, { as_of: asOf });
  expect(indicators.context.is_stored).toBe(true);
  await openHydrated(page, screenOf(REVISION, `as_of=${asOf}`));
  const main = page.getByRole("main");
  await expectCards(main, indicators, reader);
  // The curves are those of the date, the evolution of the indices that of the project, whatever the date.
  await expectCurves(main, reader, { as_of: asOf });
  const history = await ok<IndexHistory>(reader, HISTORY);
  await expectIndexPoints(
    main.getByRole("figure", { name: NAMES.history.costTitle }),
    history,
    "cost_index",
  );
  await expectIndexPoints(
    main.getByRole("figure", { name: NAMES.history.scheduleTitle }),
    history,
    "schedule_index",
  );
  await expect(page.getByRole("region", { name: catalogue.contextBanner.label })).toContainText(
    catalogue.contextBanner.asOf.replace("{date}", formatPlanningDate(asOf, LOCALE)),
  );
  // Before the first marking, no revision is designated: refused as an offer is.
  const before = "2026-01-15";
  expect((await reader.get(INDICATORS, { as_of: before })).status).toBe(409);
  await openHydrated(page, screenOf(REVISION, `as_of=${before}`));
  await expect(page.getByRole("main").getByText(NAMES.notInProgress.title)).toBeVisible();
});

test("exports each curve of the screen as a PNG image named after its figure and the project @shared [WF-IHM-0130-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  for (const [name, file] of [
    [NAMES.milestones.chartTitle, NAMES.milestones.file],
    [NAMES.costCurve.chartTitle, NAMES.costCurve.file],
    [NAMES.earnedValue.chartTitle, NAMES.earnedValue.file],
  ] as const) {
    const command = page
      .getByRole("figure", { name })
      .getByRole("button", { name: catalogue.chart.exportPng });
    const [download] = await Promise.all([page.waitForEvent("download"), command.click()]);
    expect(download.suggestedFilename()).toBe(`${file}-PRJ-001.png`);
    expect(await pngSize(download)).toEqual([2560, 1440]);
  }
});
