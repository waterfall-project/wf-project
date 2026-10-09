// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The review of a project, from the list of projects to its indicators and back, played whole in
 * French and in English (US-0090, US-0190, US-0270): the same path, the same gestures, each
 * language finding the controls by the names its catalogue gives them, written here.
 *
 * The fake back serves the first example of each operation: the project in progress, its current
 * revision — a draft —, its two sub-projects, and the indicators of the witness, whatever the
 * sub-project asked. The figures the path checks are those of that example, written here as each
 * language shows them — the marks `test_the_marks_the_review_journey_reads` holds in the
 * generator (tools/tests/test_mocktoday.py): a change of the example that moves them fails there.
 */
import { type Browser, expect, type Locator, type Page, test } from "@playwright/test";

import catalogue from "../messages/fr.json" with { type: "json" };
import type { Locale } from "../src/i18n/locale";
import { columnsOf } from "./columns";
import { compile } from "./compile";
import { WORKING } from "./hydration";
import { rowAt } from "./scroll";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;
// A sub-project of the project (`subprojects.json`), which the filter of the actual costs offers.
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";

// What the users entered, never translated: the same text in every language (WF-INTF-0170).
const PROJECT_LABEL = "Modernisation du poste de commande";
const SUBPROJECT_NAME = "SP-CMD — Poste de commande";

/** What a path reads in one language: the names its catalogue gives the controls it uses. */
interface Language {
  readonly locale: string;
  readonly language: Locale;
  readonly timezoneId: string;
  readonly names: {
    readonly functions: string;
    readonly projects: string;
    readonly currentRevision: string;
    readonly revisionTerm: string;
    readonly draft: string;
    readonly planningGrid: string;
    readonly actualCosts: string;
    readonly subprojectFilter: string;
    readonly remaining: string;
    readonly remainingGrid: string;
    readonly risks: string;
    readonly riskRegister: string;
    readonly indicators: string;
    readonly banner: string;
    readonly activeFilters: string;
    /**
     * The chip of the sub-project of the indicators, which restricts every figure but the tracking
     * of the milestones (WF-IND-0020).
     */
    readonly indicatorsChip: string;
    /** The chip of the sub-project of the remaining to commit, which restricts its grid alone. */
    readonly gridOnlyChip: string;
    readonly estimateGrid: string;
    readonly labelColumn: string;
    readonly portfolio: string;
    readonly portfolioProjects: string;
    readonly backToProject: string;
  };
  /**
   * The figures of the indicators of the witness, each under its term, as the language shows
   * them; the date of their calculation, in the time zone of the workstation.
   */
  readonly figures: readonly (readonly [term: string, shown: string])[];
  readonly computedOn: string;
}

const FRENCH: Language = {
  locale: "fr-FR",
  language: "fr",
  timezoneId: "Europe/Paris",
  names: {
    functions: "Fonctions",
    projects: "Projets",
    currentRevision: "Révision en cours",
    revisionTerm: "Révision",
    draft: "En cours d’élaboration",
    planningGrid: "Grille de planning",
    actualCosts: "Coûts réels",
    subprojectFilter: "Sous-projet",
    remaining: "Estimation du reste à engager",
    remainingGrid: "Grille de reste à engager",
    risks: "Gestion des risques",
    riskRegister: "Registre des risques",
    indicators: "Indicateurs projets",
    banner: "Contexte de lecture",
    activeFilters: "Filtres actifs",
    indicatorsChip: `Sous-projet : ${SUBPROJECT_NAME}, hors suivi des jalons`,
    gridOnlyChip: `Sous-projet : ${SUBPROJECT_NAME}, sur la grille seulement`,
    estimateGrid: "Grille de devis",
    labelColumn: "Libellé",
    portfolio: "Portefeuille",
    portfolioProjects: "Portefeuille de projets",
    backToProject: "Retour au projet",
  },
  // French separates thousands with a narrow no-break space (U+202F).
  figures: [
    ["Reste à engager", "21\u202f234,56"],
    ["Budget de référence", "120\u202f534,56"],
    ["Valeur planifiée", "101\u202f223,69"],
    ["Écart de délai", "-1\u202f223,69"],
    ["Indice de délai", "0,9879"],
    ["Indice de coût", "0,9488"],
  ],
  computedOn: "Calculé le 3 juin 2026, 16:05",
};

const ENGLISH: Language = {
  locale: "en-US",
  language: "en",
  timezoneId: "America/New_York",
  names: {
    functions: "Functions",
    projects: "Projects",
    currentRevision: "Current revision",
    revisionTerm: "Revision",
    draft: "Draft",
    planningGrid: "Planning grid",
    actualCosts: "Actual costs",
    subprojectFilter: "Subproject",
    remaining: "Estimate to complete",
    remainingGrid: "Remaining to commit grid",
    risks: "Risk management",
    riskRegister: "Risk register",
    indicators: "Project indicators",
    banner: "Reading context",
    activeFilters: "Active filters",
    indicatorsChip: `Subproject: ${SUBPROJECT_NAME}, except the milestone tracking`,
    gridOnlyChip: `Subproject: ${SUBPROJECT_NAME}, on the grid only`,
    estimateGrid: "Estimate grid",
    labelColumn: "Label",
    portfolio: "Portfolio",
    portfolioProjects: "Project portfolio",
    backToProject: "Back to the project",
  },
  figures: [
    ["Remaining to commit", "21,234.56"],
    ["Reference budget", "120,534.56"],
    ["Planned value", "101,223.69"],
    ["Schedule variance", "-1,223.69"],
    ["Schedule index", "0.9879"],
    ["Cost index", "0.9488"],
  ],
  computedOn: "Computed on 3 Jun 2026, 10:05",
};

// A text the catalogue of the language lacks shows as its key, « functions.risks »: next-intl's
// mark of a missing translation. Both catalogues have the same keys (`make catalogs`).
const MISSING = new RegExp(`\\b(?:${Object.keys(catalogue).join("|")})\\.[A-Za-z]`);

/** Check the page shows no text whose translation went missing. */
async function expectTranslated(page: Page) {
  // Its text as laid out: two blocks side by side never run together into a key.
  await expect(page.locator("body")).not.toContainText(MISSING, { useInnerText: true });
}

/**
 * Follow a link of the sidebar, opening first the block of the FBS it is in, if any; the screen
 * reached names its function — in the time given, a grid of a structure waiting for the six
 * thousand nodes of `listNodes` before its title shows —, and shows no text whose translation went
 * missing.
 */
async function follow(
  page: Page,
  { names }: Language,
  name: string,
  // Five seconds unless told otherwise, the time of an assertion of Playwright.
  { block, timeout = 5_000 }: { readonly block?: string; readonly timeout?: number } = {},
) {
  const nav = page.getByRole("navigation", { name: names.functions });
  if (block !== undefined) {
    const button = nav.getByRole("button", { name: block, exact: true });
    if ((await button.getAttribute("aria-expanded")) === "false") {
      await button.click();
    }
  }
  await nav.getByRole("link", { name, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name, { timeout });
  await expectTranslated(page);
}

/** The definitions a term names, in the list it belongs to. */
function definitionOf(scope: Page | Locator, term: string) {
  return scope
    .getByRole("term")
    .filter({ hasText: new RegExp(`^${term}$`) })
    .first()
    .locator("..");
}

/** The address of a screen of the revision, the sub-project filtered and nothing else. */
function filtered(segment: string): string {
  return `${IN_REVISION}/${segment}?subproject_id=${SUBPROJECT}`;
}

for (const language of [FRENCH, ENGLISH]) {
  const { names } = language;

  test.describe(`a browser asking for ${language.language}`, () => {
    test.use({ locale: language.locale, timezoneId: language.timezoneId });

    test("reviews a project from the list to its indicators, the revision and the sub-project kept from screen to screen, every figure the API's, and comes back to it from the portfolio [WF-QUA-0070-A] [WF-IHM-0010-A] [WF-ARC-0020-A]", async ({
      page,
    }) => {
      test.slow();
      // Every screen after the first is reached by a click: compiled first (`e2e/compile.ts`).
      await compile(
        page.request,
        `/projects/${PROJECT}`,
        IN_REVISION,
        `${IN_REVISION}/planning`,
        `${IN_REVISION}/actual-costs`,
        filtered("remaining"),
        filtered("risks"),
        filtered("indicators"),
        "/portfolio/projects",
      );

      // The list of the projects, in the language of the browser; the project opened from it.
      await page.goto("/");
      await expect(page.locator("html")).toHaveAttribute("lang", language.language);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(names.projects);
      // The list may not be hydrated yet: the link then loads the project as a whole document,
      // given the time of a screen under load.
      await page.getByRole("main").getByRole("link", { name: PROJECT_LABEL }).click();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(PROJECT_LABEL, {
        timeout: WORKING,
      });
      // The shell hydrated, which writes the context it shows in its cookie from an effect alone:
      // from here on, every click is a navigation in the browser, React answering the gestures.
      await expect
        .poll(
          async () => {
            const cookies = await page.context().cookies();
            const last = cookies.find((cookie) => cookie.name === "wf_last_project");
            return decodeURIComponent(last?.value ?? "");
          },
          { timeout: WORKING },
        )
        .toBe(`/projects/${PROJECT}`);

      // Its current revision, which opens on its planning: six thousand rows rendered by the
      // server, given the time the witness path gives them (#315).
      await page.getByRole("main").getByRole("link", { name: names.currentRevision }).click();
      await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
      await expect(page.getByRole("treegrid", { name: names.planningGrid })).toBeVisible({
        timeout: WORKING,
      });

      // The actual costs, where the user filters a sub-project: the address carries it.
      await follow(page, language, names.actualCosts);
      // The choice is the filter's once React answers it: chosen again until the address says it.
      const subprojects = page.getByRole("combobox", { name: names.subprojectFilter, exact: true });
      await expect(async () => {
        await subprojects.selectOption(SUBPROJECT);
        await expect(page).toHaveURL(new RegExp(`subproject_id=${SUBPROJECT}`), { timeout: 1_000 });
      }).toPass({ timeout: WORKING });

      // The remaining to commit, then the risks, then the indicators: the same revision, in the
      // path, and the same sub-project, in the parameters, each time (WF-IHM-0010).
      const banner = page.getByRole("region", { name: names.banner });
      const chips = banner.getByRole("list", { name: names.activeFilters }).getByRole("listitem");
      await follow(page, language, names.remaining, { timeout: WORKING });
      await expect(page).toHaveURL(filtered("remaining"));
      await expect(chips).toHaveText([names.gridOnlyChip]);
      await expect(page.getByRole("treegrid", { name: names.remainingGrid })).toBeVisible();

      await follow(page, language, names.risks);
      await expect(page).toHaveURL(filtered("risks"));
      await expect(page.getByRole("grid", { name: names.riskRegister })).toBeVisible();

      // The indicators read several answers on the server before they show.
      await follow(page, language, names.indicators, { timeout: WORKING });
      await expect(page).toHaveURL(filtered("indicators"));
      await expect(chips).toHaveText([names.indicatorsChip]);

      // The amounts, the indices and the date of calculation are the API's, formatted in the
      // language, the date in the time zone of the workstation (WF-ARC-0020).
      for (const [term, shown] of language.figures) {
        await expect(definitionOf(page, term).getByRole("definition").first()).toHaveText(shown);
      }
      await expect(page.getByRole("main")).toContainText(language.computedOn);

      // Out of the project, to its portfolio; back to the project, in the same context.
      await follow(page, language, names.portfolioProjects, { block: names.portfolio });
      await expect(page).toHaveURL("/portfolio/projects");
      // The indicators read several answers on the server before they show: given the time of a
      // screen under load.
      await page.getByRole("link", { name: names.backToProject }).click();
      await expect(page).toHaveURL(filtered("indicators"), { timeout: WORKING });
      await expect(chips).toHaveText([names.indicatorsChip]);
    });
  });
}

/** A page of a browser of its own, asking for a language. */
async function pageIn(browser: Browser, language: Language): Promise<Page> {
  const context = await browser.newContext({
    locale: language.locale,
    timezoneId: language.timezoneId,
  });
  return context.newPage();
}

/**
 * A grid of the revision that shows labels: its screen, its name, a row holding a label, and
 * whether a label is entered there — in the estimate; the planning is entered from EP-06.
 */
interface EntryGrid {
  readonly segment: "planning" | "estimate";
  readonly name: (language: Language) => string;
  readonly row: number;
  readonly label: string;
  readonly entered: boolean;
}

const ENTRY_GRIDS: readonly EntryGrid[] = [
  {
    segment: "planning",
    name: ({ names }) => names.planningGrid,
    row: 2,
    label: "Études de détail",
    entered: false,
  },
  {
    segment: "estimate",
    name: ({ names }) => names.estimateGrid,
    row: 3,
    label: "Ingénierie de détail",
    entered: true,
  },
];

/** What a user reads of a grid: its headings, the labels of its first rows, the revision state. */
async function readGrid(page: Page, language: Language, entry: EntryGrid) {
  const { names } = language;
  await page.goto(`${IN_REVISION}/${entry.segment}`);
  const grid = page.getByRole("treegrid", { name: entry.name(language) });
  await expect(grid).toBeVisible({ timeout: WORKING });
  const { label } = await columnsOf(grid, { label: names.labelColumn });
  const labels = await Promise.all(
    [1, 2, 3, 4, 5].map((row) => rowAt(grid, row).getByRole("gridcell").nth(label).innerText()),
  );
  const revision = definitionOf(
    page.getByRole("region", { name: names.banner }),
    names.revisionTerm,
  );
  return {
    grid,
    label,
    headings: await grid.getByRole("columnheader").allInnerTexts(),
    labels,
    // The state of the revision, its second definition after its name.
    state: await revision.getByRole("definition").nth(1).innerText(),
  };
}

/**
 * Check a grid has one column that bears the name of the label, and that a label is entered in one
 * field, if anywhere: a double click opens it once React answers it, given again until it does.
 */
async function expectOneLabelField(
  page: Page,
  language: Language,
  entry: EntryGrid,
  { grid, label }: { readonly grid: Locator; readonly label: number },
) {
  const { names } = language;
  await expect(grid.getByRole("columnheader", { name: new RegExp(names.labelColumn) })).toHaveCount(
    1,
  );
  if (!entry.entered) {
    await expect(grid.getByRole("textbox")).toHaveCount(0);
    return;
  }
  const field = page.getByRole("textbox", { name: names.labelColumn });
  await expect(async () => {
    await rowAt(grid, entry.row).getByRole("gridcell").nth(label).dblclick();
    await expect(field).toHaveValue(entry.label, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(grid.getByRole("textbox")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await expect(grid.getByRole("textbox")).toHaveCount(0);
}

test("two users of different languages opening the same project read the same labels of tasks and lines, under headings and states each in their own language, are offered no label to enter in a second language, and read what the other entered with no mark of a missing translation [WF-INTF-0170-A]", async ({
  browser,
}) => {
  test.slow();
  const [french, english] = await Promise.all([pageIn(browser, FRENCH), pageIn(browser, ENGLISH)]);
  try {
    for (const entry of ENTRY_GRIDS) {
      const read = {
        fr: await readGrid(french, FRENCH, entry),
        en: await readGrid(english, ENGLISH, entry),
      };

      // The labels of the tasks and of the lines are those entered, the same in both languages;
      // the headings of the columns and the state of the revision differ.
      expect(read.fr.labels).toContain(entry.label);
      expect(read.en.labels).toEqual(read.fr.labels);
      expect(read.en.headings).toHaveLength(read.fr.headings.length);
      expect(read.en.headings).not.toEqual(read.fr.headings);
      expect(read.fr.state).toBe(FRENCH.names.draft);
      expect(read.en.state).toBe(ENGLISH.names.draft);

      // A label is entered in its cell alone, in one field, whatever the language of the user.
      await expectOneLabelField(french, FRENCH, entry, read.fr);
      await expectOneLabelField(english, ENGLISH, entry, read.en);
      await expectTranslated(english);
    }

    // The project entered in French reads in English as it was entered — its labels, above, and
    // its own page —, with no mark of a missing translation, on its texts or anywhere else.
    await english.goto(`/projects/${PROJECT}`);
    await expect(english.getByRole("heading", { level: 1 })).toHaveText(PROJECT_LABEL);
    await expect(english.getByRole("main")).toContainText("PRJ-001");
    await expectTranslated(english);
  } finally {
    await Promise.all([french.context().close(), english.context().close()]);
  }
});
