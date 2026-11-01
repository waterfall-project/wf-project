// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The online help as files (WF-IHM-0140, US-0580), in each language of the interface (US-0670b):
 * every code of the FBS that has a screen has its page in French and in English, by the same name —
 * since US-0670/L5 (#1452), none waits for it any more in the list of the pages to come, which names
 * the lot that writes each and stays for a code the table would gain —; the page of a screen keeps
 * the fixed structure, said in its language; a French notion quotes the glossary of the specification
 * without rewriting it, an English one translates the same quotations, as many; the English pages
 * link to the pages the French ones link to, and cite in bold the labels of the English catalogue
 * where the French ones cite those of the French; every link leads to a page the help has, or will
 * have; no page holds raw HTML.
 *
 * The list of the pages still to write never lies: a code that receives its file must leave it, and
 * a code it names must be one the table has. A page missing in one language is a failure there,
 * never the page of another language in its place.
 */
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import { readHelp } from "@/api/actions/help";
import { CATALOGUES } from "@/i18n/catalogues";
import { LOCALES, type Locale } from "@/i18n/locale";
import { FUNCTION_GROUPS } from "@/navigation/functions";

import {
  fileOf,
  HELP_CODES,
  type HelpTarget,
  helpCodeAt,
  isHelpTarget,
  linkTarget,
  NOTION_HEADINGS,
  SCREEN_HEADINGS,
  searched,
  sectionsOf,
} from "./help";
import { helpDirectory, helpIndex, parseHelp, readHelpPage } from "./read";
import { NOTIONS_TO_COME, SCREENS_TO_COME } from "./to-come";

/** The directories of the help in each language, those of the front. */
const DIRECTORIES: Readonly<Record<Locale, string>> = {
  fr: helpDirectory("fr"),
  en: helpDirectory("en"),
};

/** Whether the file of a page is written in a language. */
function written(target: HelpTarget, language: Locale = "fr"): boolean {
  return existsSync(path.join(DIRECTORIES[language], fileOf(target)));
}

/** The names of the notions written in a language. */
function notions(language: Locale = "fr"): string[] {
  return readdirSync(path.join(DIRECTORIES[language], "notions"))
    .filter((file) => file.endsWith(".md"))
    .map((file) => file.slice(0, -".md".length));
}

/** Every file of the help in a language, by its path under the directory of that language. */
function files(language: Locale): string[] {
  const directory = DIRECTORIES[language];
  return readdirSync(directory, { recursive: true, encoding: "utf8" })
    .filter((file) => file.endsWith(".md"))
    .map((file) => file.split(path.sep).join("/"))
    .sort();
}

/** Every page written in a language, with its text. */
function pages(language: Locale = "fr"): { target: HelpTarget; text: string }[] {
  const targets: HelpTarget[] = [
    ...HELP_CODES.map((code) => ({ kind: "screen", code }) as const),
    ...notions(language).map((name) => ({ kind: "notion", name }) as const),
  ];
  return targets
    .filter((target) => written(target, language))
    .map((target) => ({
      target,
      text: readFileSync(path.join(DIRECTORIES[language], fileOf(target)), "utf8"),
    }));
}

/** The text of a page in a language. */
function pageText(target: HelpTarget, language: Locale): string {
  return readFileSync(path.join(DIRECTORIES[language], fileOf(target)), "utf8");
}

/** A text as the glossary and a page are compared: the apostrophes and the spaces made plain. */
function plain(text: string): string {
  // `\s` takes the no-break spaces of French typography too.
  return text.replace(/[’']/g, "'").replace(/\s+/g, " ").trim();
}

/**
 * A definition of the glossary as a notion quotes it: without the identifiers of requirement in
 * brackets (« (WF-RIS-0050) »), which mean nothing to the reader of the help (#1440).
 */
function withoutIdentifiers(text: string): string {
  return text.replace(/\s\(WF-[A-Z]{3}-\d{4}\)/g, "");
}

/** The glossary of the specification, its annex A, by term. */
function glossary(): ReadonlyMap<string, string> {
  const spec = readFileSync(
    path.join(process.cwd(), "..", "docs", "spec", "waterfall-spec.md"),
    "utf8",
  );
  const start = spec.indexOf("# ANNEXE A: Glossaire");
  const end = spec.indexOf("# ANNEXE B", start);
  const terms = new Map<string, string>();
  for (const row of spec.slice(start, end).split("\n")) {
    const cells = /^\|([^|]+)\|([^|]+)\|$/.exec(row.trim());
    if (cells?.[1] !== undefined && cells[2] !== undefined && !cells[1].includes("---")) {
      terms.set(plain(cells[1]), plain(withoutIdentifiers(cells[2])));
    }
  }
  return terms;
}

/** The quotations of the glossary of a notion, under its first section: `> **Term** — …`. */
function quotations(text: string): (RegExpExecArray | null)[] {
  return (parseHelp(text)?.sections[0]?.body ?? "")
    .split("\n")
    .filter((line) => line.startsWith(">"))
    .map((line) => /^> \*\*(.+?)\*\* — (.+)$/.exec(line));
}

/** The links of a Markdown text, their targets as written. */
function links(text: string): string[] {
  return [...text.matchAll(/\]\(([^)]*)\)/g)].map((match) => match[1] ?? "");
}

/** The pages a page links to, by their files, in order. */
function linked(target: HelpTarget, text: string): string[] {
  return links(text).map((href) => {
    const to = linkTarget(target, href);
    return to === undefined ? href : fileOf(to);
  });
}

/** The texts a page writes in bold. */
function bold(text: string): string[] {
  return [...text.matchAll(/\*\*(.+?)\*\*/g)].map((match) => match[1] ?? "");
}

/** Every text of a catalogue, by its key. */
function texts(catalogue: object, prefix = ""): Map<string, string> {
  const found = new Map<string, string>();
  for (const [key, value] of Object.entries(catalogue)) {
    if (typeof value === "string") {
      found.set(prefix + key, value);
    } else if (typeof value === "object" && value !== null) {
      for (const [inner, text] of texts(value as object, `${prefix}${key}.`)) {
        found.set(inner, text);
      }
    }
  }
  return found;
}

const FRENCH = texts(CATALOGUES.fr);
const ENGLISH = texts(CATALOGUES.en);

/** The English texts of the keys whose French text is the one given. */
function inEnglish(french: string): string[] {
  return [...FRENCH].flatMap(([key, text]) => (text === french ? [ENGLISH.get(key) ?? ""] : []));
}

/**
 * The key, in the catalogues, of the name a code has on its screen: that of a function, of a leaf,
 * of the block of the projects, or of a section of a function's screen.
 */
function nameKey(code: string): string | undefined {
  for (const group of FUNCTION_GROUPS) {
    if (group.code === code && group.route !== undefined) {
      return group.label;
    }
    for (const fn of group.functions) {
      const named = [fn, ...(fn.leaves ?? [])].find((each) => each.code === code);
      if (named !== undefined) {
        return named.label;
      }
      const section = (fn.sections ?? []).find((each) => each.code === code);
      if (section !== undefined) {
        return section.name;
      }
    }
  }
  return undefined;
}

describe("the pages of the help", () => {
  it.each(LOCALES)(
    "has a page in %s for every code of the FBS that has a screen, none left to come [WF-IHM-0140-A]",
    (language) => {
      // US-0670/L5 (#1452) wrote the last French pages, US-0670b their English translation: the
      // list of the pages to come is empty, and every code of the table has its file in each language.
      expect(SCREENS_TO_COME).toEqual({});
      expect(HELP_CODES.filter((code) => !written({ kind: "screen", code }, language))).toEqual([]);
      // The list of the pages to come never lies: none of them written, each a code of the table.
      const writtenToCome = Object.keys(SCREENS_TO_COME).filter((code) =>
        written({ kind: "screen", code }, language),
      );
      expect(writtenToCome).toEqual([]);
      expect(Object.keys(SCREENS_TO_COME).filter((code) => !HELP_CODES.includes(code))).toEqual([]);
      // Every code of the table is written or to come, never both and never neither.
      expect(HELP_CODES.length).toBe(
        HELP_CODES.filter((code) => written({ kind: "screen", code }, language)).length +
          Object.keys(SCREENS_TO_COME).length,
      );
    },
  );

  it.each(LOCALES)(
    "writes in %s every notion of the method, and lists none to come but those not written [WF-IHM-0140-A]",
    (language) => {
      // The name of a notion is a key, not a word shown: the same in each language.
      expect(notions(language).sort()).toEqual([
        "avenant-et-differentiel",
        "budget-de-reference",
        "chemin-critique",
        "indices",
        "lotissement",
        "provision-et-reserve",
        "reste-a-engager",
        "revisions",
        "valeur-acquise",
        "valeur-planifiee",
      ]);
      expect(NOTIONS_TO_COME).toEqual({});
    },
  );

  it("names the files of the English help as those of the French, none added nor left out [WF-IHM-0140-A]", () => {
    expect(files("en")).toEqual(files("fr"));
    expect(files("fr")).toHaveLength(HELP_CODES.length + notions("fr").length);
  });

  it.each(LOCALES)(
    "gives the page of every screen, in %s, the fixed structure of the help in its language, each section filled [WF-IHM-0140-A]",
    (language) => {
      for (const { target, text } of pages(language).filter(
        (page) => page.target.kind === "screen",
      )) {
        const parsed = parseHelp(text);
        expect(parsed?.title, fileOf(target)).toBeTruthy();
        expect(parsed?.intro, fileOf(target)).toBe("");
        expect(
          parsed?.sections.map((section) => section.heading),
          fileOf(target),
        ).toEqual([...SCREEN_HEADINGS[language]]);
        expect(
          parsed?.sections
            .filter((section) => section.body === "")
            .map((section) => section.heading),
          fileOf(target),
        ).toEqual([]);
      }
    },
  );

  it("quotes the glossary of the specification in every French notion, word for word but the identifiers of requirement [WF-IHM-0140-A]", () => {
    const terms = glossary();
    expect(terms.size).toBeGreaterThan(50);
    for (const { target, text } of pages("fr").filter((page) => page.target.kind === "notion")) {
      expect(
        parseHelp(text)?.sections.map((section) => section.heading),
        fileOf(target),
      ).toEqual([...NOTION_HEADINGS.fr]);
      const quotes = quotations(text);
      expect(quotes.length, fileOf(target)).toBeGreaterThan(0);
      for (const quote of quotes) {
        expect(quote, fileOf(target)).not.toBeNull();
        const term = plain(quote?.[1] ?? "");
        expect(quote?.[2], `${fileOf(target)}: ${term}`).not.toMatch(/WF-[A-Z]{3}-\d{4}/);
        expect(plain(quote?.[2] ?? ""), `${fileOf(target)}: ${term}`).toBe(terms.get(term));
      }
    }
  });

  it("translates in every English notion the quotations of the French, in their form, as many [WF-IHM-0140-A]", () => {
    // The specification is French alone: the comparison word for word stays on the French, and the
    // English keeps the form and the number of its quotations (US-0670b).
    for (const { target, text } of pages("en").filter((page) => page.target.kind === "notion")) {
      expect(
        parseHelp(text)?.sections.map((section) => section.heading),
        fileOf(target),
      ).toEqual([...NOTION_HEADINGS.en]);
      const quotes = quotations(text);
      expect(quotes.length, fileOf(target)).toBe(quotations(pageText(target, "fr")).length);
      for (const quote of quotes) {
        expect(quote, fileOf(target)).not.toBeNull();
        expect(quote?.[2], fileOf(target)).not.toMatch(/WF-[A-Z]{3}-\d{4}/);
      }
    }
  });

  it.each(LOCALES)(
    "links every page, in %s, to pages the help has, or to pages to come [WF-IHM-0140-A]",
    (language) => {
      const broken: string[] = [];
      for (const { target, text } of pages(language)) {
        for (const href of links(text)) {
          const to = linkTarget(target, href);
          const known =
            to !== undefined &&
            (written(to, language) ||
              (to.kind === "screen"
                ? SCREENS_TO_COME[to.code] !== undefined
                : NOTIONS_TO_COME[to.name] !== undefined));
          if (!known) {
            broken.push(`${fileOf(target)} → ${href}`);
          }
        }
      }
      expect(broken).toEqual([]);
    },
  );

  it("links every English page to the pages its French one links to, as many times [WF-IHM-0140-A]", () => {
    const differing = pages("fr").flatMap(({ target, text }) => {
      const french = linked(target, text).sort();
      const english = linked(target, pageText(target, "en")).sort();
      return JSON.stringify(english) === JSON.stringify(french)
        ? []
        : [{ page: fileOf(target), french, english }];
    });
    expect(differing).toEqual([]);
  });

  it("cites in bold, on every English page, the labels of the English catalogue its French one cites from the French [WF-IHM-0140-A]", () => {
    const missing = pages("fr").flatMap(({ target, text }) => {
      const english = new Set(bold(pageText(target, "en")));
      return bold(text).flatMap((label) => {
        const labels = inEnglish(label);
        return labels.length === 0 || labels.some((each) => english.has(each))
          ? []
          : [`${fileOf(target)}: ${label} → ${labels.join(" | ")}`];
      });
    });
    expect(missing).toEqual([]);
  });

  it("titles every English page of a screen by its name in the English catalogue, where the French one is titled by its name in the French [WF-IHM-0140-A]", () => {
    const differing = HELP_CODES.flatMap((code) => {
      const key = nameKey(code);
      const target = { kind: "screen", code } as const;
      const french = parseHelp(pageText(target, "fr"))?.title;
      const english = parseHelp(pageText(target, "en"))?.title;
      return key === undefined || french !== FRENCH.get(key) || english === ENGLISH.get(key)
        ? []
        : [`${code}: ${String(english)} → ${String(ENGLISH.get(key))}`];
    });
    expect(differing).toEqual([]);
  });

  it.each(LOCALES)(
    "holds neither raw HTML nor images in any page, in %s [WF-IHM-0140-A]",
    (language) => {
      const offending = pages(language).filter(({ text }) => /<[a-z/!]|!\[/i.test(text));
      expect(offending.map(({ target }) => fileOf(target))).toEqual([]);
    },
  );

  it("writes the English entries of a duration and of the predecessors as the English interface takes them [WF-IHM-0140-A]", () => {
    // #1441: the suffixes of the units and the codes of the links are the English catalogue's.
    const grid = pageText({ kind: "screen", code: "FBS-4.3.2" }, "en");
    const units = CATALOGUES.en.enums.DurationUnit;
    const typed = [`2 ${units.d}`, `1 ${units.w}`, `1 ${units.mo}`, `3FS+2 ${units.d}; 5SS`];
    for (const entry of typed) {
      expect(grid).toContain(`“${entry}”`);
    }
    for (const french of [/« \d+ (j|sem) »/, /\bFD\b/, /\bDD\b/, /\bDF\b/]) {
      expect(grid).not.toMatch(french);
    }
  });
});

/** The directories made for a test, removed after it. */
const folders: string[] = [];

afterEach(() => {
  vi.restoreAllMocks();
  for (const folder of folders.splice(0)) {
    rmSync(folder, { recursive: true, force: true });
  }
});

describe("the reading of the help", () => {
  it("reads the page of a screen in its sections, with the columns of its grid from the catalogues [WF-IHM-0140-A]", async () => {
    const page = await readHelpPage({ kind: "screen", code: "FBS-4.4" }, "fr");
    expect(page.kind).toBe("written");
    if (page.kind === "written") {
      expect(page.title).toBe("Chiffrage et devis");
      expect(page.sections.map((section) => section.heading)).toEqual([...SCREEN_HEADINGS.fr]);
      expect(page.columns.map((column) => column.help)).toContain("estimate.referenceAmount");
      expect(page.columns.find((column) => column.help === "estimate.paymentDelay")?.computed).toBe(
        false,
      );
      expect(
        page.columns.find((column) => column.help === "estimate.referenceAmount")?.computed,
      ).toBe(true);
    }
    const column = await readHelpPage({ kind: "screen", code: "FBS-4.4.3" }, "fr");
    expect(column.kind === "written" ? column.columns.map((each) => each.label) : []).toEqual([
      "referenceAmount",
    ]);
  });

  it("reads the page of a screen in English, its sections said in English, the columns of its grid the same [WF-IHM-0140-A]", async () => {
    const french = await readHelpPage({ kind: "screen", code: "FBS-4.4" }, "fr");
    const page = await readHelpPage({ kind: "screen", code: "FBS-4.4" }, "en");
    expect(page.kind).toBe("written");
    if (page.kind === "written" && french.kind === "written") {
      expect(page.title).toBe(CATALOGUES.en.functions.estimate);
      expect(page.sections.map((section) => section.heading)).toEqual([...SCREEN_HEADINGS.en]);
      expect(page.columns).toEqual(french.columns);
    }
    const notion = await readHelpPage({ kind: "notion", name: "valeur-acquise" }, "en");
    expect(notion.kind === "written" ? notion.title : undefined).toBe("Earned value");
  });

  it.each([
    ["FBS-4.3"],
    ["FBS-4.3.2"],
    ["FBS-4.3.3"],
    ["FBS-4.4"],
    ["FBS-4.4.2"],
    ["FBS-4.4.3"],
    ["FBS-4.5"],
    ["FBS-4.5.2"],
    ["FBS-4.6"],
    ["FBS-4.6.1"],
    ["FBS-1.1"],
    ["FBS-1.2"],
    ["FBS-1.4"],
    ["FBS-1.5"],
    ["FBS-2.1"],
    ["FBS-3.1"],
    ["FBS-3.1.1"],
    ["FBS-3.1.2"],
    ["FBS-3.2"],
    ["FBS-3.2.1"],
    ["FBS-3.2.2"],
    ["FBS-3.2.3"],
    ["FBS-4"],
    ["FBS-4.2"],
    ["FBS-4.2.1"],
    ["FBS-4.2.3"],
    ["FBS-4.2.4"],
    ["FBS-4.7"],
    ["FBS-4.1"],
  ])(
    "names the columns of %s, each with a label and a definition key [WF-IHM-0140-A]",
    async (code) => {
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      expect(page.kind).toBe("written");
      const columns = page.kind === "written" ? page.columns : [];
      expect(columns.length).toBeGreaterThan(0);
      for (const column of columns) {
        expect(column.label.trim()).not.toBe("");
        expect(column.help.trim()).not.toBe("");
      }
      if (code === "FBS-4.3.3" || code === "FBS-4.4.3") {
        expect(columns).toHaveLength(1);
      }
    },
  );

  it.each([["FBS-4.6"], ["FBS-4.6.1"]])(
    "defines the columns of %s as the risk grid orders them [WF-IHM-0140-A]",
    async (code) => {
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      const helps = page.kind === "written" ? page.columns.map((column) => column.help) : [];
      expect(helps).toHaveLength(8);
      expect(helps.every((help) => help.startsWith("risks."))).toBe(true);
      expect(helps).toEqual([
        "risks.label",
        "risks.probability",
        "risks.severity",
        "risks.provisionAmount",
        "risks.occurrenceCost",
        "risks.state",
        "risks.lastReview",
        "risks.matrixCell",
      ]);
    },
  );

  it("says a page not written yet is to come, when a code the table gains waits for its lot [WF-IHM-0140-A]", async () => {
    // Every page is written since US-0670/L5: a code the table would gain is listed to come, with
    // the lot that writes it, and its page, not carried, is said to come rather than failing.
    const root = mkdtempSync(path.join(tmpdir(), "waterfall-help-"));
    folders.push(root);
    mkdirSync(path.join(root, "help", "fr"), { recursive: true });
    vi.spyOn(process, "cwd").mockReturnValue(root);
    vi.resetModules();
    vi.doMock("./to-come", () => ({
      SCREENS_TO_COME: { "FBS-4.8": "a lot to come" },
      NOTIONS_TO_COME: { indices: "a lot to come" },
    }));
    try {
      const fresh = await import("./read");
      expect(await fresh.readHelpPage({ kind: "screen", code: "FBS-4.8" }, "fr")).toEqual({
        kind: "pending",
        target: { kind: "screen", code: "FBS-4.8" },
      });
      expect((await fresh.readHelpPage({ kind: "notion", name: "indices" }, "fr")).kind).toBe(
        "pending",
      );
      // A page not listed to come, and not carried, fails.
      await expect(fresh.readHelpPage({ kind: "screen", code: "FBS-4.3" }, "fr")).rejects.toThrow(
        "FBS-4.3.md",
      );
    } finally {
      // The lists mocked never reach the tests after it, whatever this one does.
      vi.doUnmock("./to-come");
      vi.resetModules();
    }
  });

  it.each([
    ["/projects/p/revisions", "FBS-4.1", "Gestion des révisions"],
    ["/projects/p/revisions/r/planning", "FBS-4.3", "Planification"],
    ["/projects/p/revisions/r/estimate", "FBS-4.4", "Chiffrage et devis"],
    ["/projects/p/revisions/r/remaining", "FBS-4.5", "Estimation du reste à engager"],
    ["/projects/p/revisions/r/risks", "FBS-4.6", "Gestion des risques"],
  ])(
    "opens, at %s, the help of the screen it shows: %s, %s [WF-IHM-0140-A]",
    async (pathname, code, title) => {
      expect(helpCodeAt(pathname)).toBe(code);
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      expect(page.kind).toBe("written");
      if (page.kind === "written") {
        expect(page.title).toBe(title);
      }
    },
  );

  it.each([
    ["/admin/users", "FBS-1.1", "Gestion des utilisateurs"],
    ["/admin/access-roles", "FBS-1.2", "Gestion des rôles d’habilitation"],
    ["/system", "FBS-1.3", "Surveillance de l’état du système"],
    ["/admin/backups", "FBS-1.4", "Sauvegarde et restauration"],
    ["/admin/audit-log", "FBS-1.5", "Journal d’audit"],
    ["/portfolio/projects", "FBS-2.1", "Portefeuille de projets"],
    ["/portfolio/workload", "FBS-2.2", "Plan de charge agrégé"],
    ["/portfolio/performance", "FBS-2.3", "Performance du portefeuille"],
    ["/portfolio/cost-structure", "FBS-2.4", "Structure des coûts du portefeuille"],
    ["/portfolio/risks", "FBS-2.5", "Risques du portefeuille"],
    ["/portfolio/cost-curve", "FBS-2.6", "Courbe en S du portefeuille"],
    ["/portfolio/pilot-health", "FBS-2.7", "Santé du pilotage"],
    ["/reference/costs", "FBS-3.1", "Paramètres de coûts"],
    [
      "/reference/costs/actual-cost-mapping",
      "FBS-3.1.3",
      "Correspondance de l’extraction des coûts réels",
    ],
    ["/reference/resources", "FBS-3.2", "Paramètres de ressources"],
    ["/reference/risks", "FBS-3.3", "Paramètres de risques"],
    ["/reference/indicators", "FBS-3.4", "Paramètres d’indicateurs"],
  ])(
    "opens, at %s, the help of the screen of the administration, the portfolio or the reference data: %s, %s [WF-IHM-0140-A]",
    async (pathname, code, title) => {
      expect(helpCodeAt(pathname)).toBe(code);
      expect(SCREENS_TO_COME[code]).toBeUndefined();
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      expect(page.kind).toBe("written");
      if (page.kind === "written") {
        expect(page.title).toBe(title);
      }
    },
  );

  it.each([
    ["/", "FBS-4", "Projets"],
    ["/projects/p", "FBS-4", "Projets"],
    ["/projects/p/settings", "FBS-4.2", "Paramètres de projets"],
    ["/projects/p/revisions/r/timelines", "FBS-4.3.1", "Chronologies"],
    ["/projects/p/revisions/r/exchanges", "FBS-4.3.4", "Imports et exports"],
    ["/projects/p/revisions/r/task-tree", "FBS-4.3.5", "Arborescence de tâches"],
    ["/projects/p/revisions/r/workload", "FBS-4.4.4", "Plan de charge du projet"],
    ["/projects/p/revisions/r/kanban", "FBS-4.5.3", "Kanban — démarrage des tâches"],
    ["/projects/p/revisions/r/actual-costs", "FBS-4.7", "Coûts réels"],
    ["/projects/p/revisions/r/indicators", "FBS-4.8", "Indicateurs projets"],
    ["/projects/p/lifecycle", "FBS-4.9", "Cycle de vie du projet"],
  ])(
    "opens, at %s, the help of the screen of the project: %s, %s [WF-IHM-0140-A]",
    async (pathname, code, title) => {
      expect(helpCodeAt(pathname)).toBe(code);
      expect(SCREENS_TO_COME[code]).toBeUndefined();
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      expect(page.kind).toBe("written");
      if (page.kind === "written") {
        expect(page.title).toBe(title);
      }
    },
  );

  it.each([
    ["FBS-4.8.1", "Avancement financier"],
    ["FBS-4.8.2", "Projection à terminaison"],
    ["FBS-4.8.3", "Avancement physique"],
    ["FBS-4.8.4", "Indicateur de coûts (CPI)"],
    ["FBS-4.8.5", "Indicateur de délais (SPI)"],
    ["FBS-4.8.6", "Suivi des jalons"],
    ["FBS-4.8.7", "Coûts cumulés"],
    ["FBS-4.8.8", "Courbes de valeur acquise"],
  ])(
    "writes the help of %s, a section of the indicators of a project: %s [WF-IHM-0140-A]",
    async (code, title) => {
      expect(sectionsOf("FBS-4.8")).toContain(code);
      expect(SCREENS_TO_COME[code]).toBeUndefined();
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      expect(page.kind).toBe("written");
      if (page.kind === "written") {
        expect(page.title).toBe(title);
        // Cards and charts: no grid, no definition of a column.
        expect(page.columns).toEqual([]);
      }
    },
  );

  // The exclusion written under US-0670 in the file of EP-16 (#1439): the screens outside the table
  // of the functions open no help — the account, the avatar, the pages of error and of the session.
  it.each([
    ["/account"],
    ["/account/avatar"],
    ["/login/unavailable"],
    ["/nowhere"],
    ["/projects"],
    ["/projects/p/nowhere"],
    ["/projects/p/revisions/r"],
  ])("opens no help at %s, outside the table of the functions [WF-IHM-0140-A]", (pathname) => {
    expect(helpCodeAt(pathname)).toBeUndefined();
  });

  it("names the columns of the settings of a project once, and every column kept from the file of the actual costs alike [WF-IHM-0140-A]", async () => {
    const helps = async (code: string) => {
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      return page.kind === "written" ? page.columns.map((column) => column.help) : [];
    };
    expect(await helps("FBS-4.2")).toEqual([
      ...(await helps("FBS-4.2.1")),
      ...(await helps("FBS-4.2.3")),
      ...(await helps("FBS-4.2.4")),
    ]);
    expect(await helps("FBS-4.2.1")).toEqual(["workBreakdown.label", "workBreakdown.kind"]);
    // The sub-projects with the columns of their commands, which a session that may modify them sees.
    expect(await helps("FBS-4.2.3")).toEqual([
      "subprojects.code",
      "subprojects.label",
      "subprojects.actualCosts",
      "subprojects.modify",
      "subprojects.delete",
    ]);
    expect(await helps("FBS-4")).toEqual([
      "projects.label",
      "projects.code",
      "projects.state",
      "projects.updatedAt",
    ]);
    expect((await helps("FBS-4.7")).at(-1)).toBe("actualCosts.passthrough");
    // The comparison of two revisions, the one grid of their management (US-0670/L5, #1434).
    expect(await helps("FBS-4.1")).toEqual(["nodes.label", "comparison.changes"]);
    // A leaf of a fact, or a screen without a table, defines no column.
    for (const code of ["FBS-4.2.2", "FBS-4.2.5", "FBS-4.3.5", "FBS-4.8", "FBS-4.9"]) {
      expect(await helps(code), code).toEqual([]);
    }
  });

  it("names each column of the screens of the reference data once, their state and modification shared by their lists [WF-IHM-0140-A]", async () => {
    const helps = async (code: string) => {
      const page = await readHelpPage({ kind: "screen", code }, "fr");
      return page.kind === "written" ? page.columns.map((column) => column.help) : [];
    };
    for (const code of ["FBS-3.1", "FBS-3.1.1", "FBS-3.2"]) {
      const named = await helps(code);
      expect(new Set(named).size, code).toBe(named.length);
      expect(
        named.filter((help) => help.startsWith("referenceCommands.")),
        code,
      ).toEqual(["referenceCommands.state", "referenceCommands.modify"]);
    }
    expect(await helps("FBS-3.1.2")).toEqual([
      "hourlyRates.code",
      "hourlyRates.label",
      "hourlyRates.state",
      "hourlyRates.year",
    ]);
    expect(await helps("FBS-3.1")).toEqual(
      expect.arrayContaining([...(await helps("FBS-3.1.1")), ...(await helps("FBS-3.1.2"))]),
    );
    expect(await helps("FBS-3.2")).toEqual(
      expect.arrayContaining([
        ...(await helps("FBS-3.2.1")),
        ...(await helps("FBS-3.2.2")),
        ...(await helps("FBS-3.2.3")),
      ]),
    );
    expect(await helps("FBS-3.1.3")).toEqual([]);
  });

  it.each([
    ["fr", "en"],
    ["en", "fr"],
  ] as const)(
    "fails on a page that should be written in %s and whose file is missing, the other language carried [WF-IHM-0140-A]",
    async (missing, carried) => {
      const root = mkdtempSync(path.join(tmpdir(), "waterfall-help-"));
      folders.push(root);
      mkdirSync(path.join(root, "help", missing), { recursive: true });
      cpSync(DIRECTORIES[carried], path.join(root, "help", carried), { recursive: true });
      vi.spyOn(process, "cwd").mockReturnValue(root);
      // FBS-4.3 has a page, which this directory does not carry in one language, as a standalone
      // build that forgot it or a translation forgotten: no page of the other language in its place.
      for (const target of [
        { kind: "screen", code: "FBS-4.3" },
        { kind: "notion", name: "indices" },
        { kind: "screen", code: "FBS-4.8" },
      ] as const) {
        await expect(readHelpPage(target, missing)).rejects.toThrow(
          `${fileOf(target)} is missing from ${path.join(root, "help", missing)}`,
        );
        expect((await readHelpPage(target, carried)).kind).toBe("written");
      }
    },
  );

  it.each(LOCALES)(
    "fails the index in %s on a page that should be written and is missing or untitled, and does not keep it [WF-IHM-0140-A]",
    async (language) => {
      const root = mkdtempSync(path.join(tmpdir(), "waterfall-help-"));
      folders.push(root);
      const directory = path.join(root, "help", language);
      mkdirSync(directory, { recursive: true });
      vi.spyOn(process, "cwd").mockReturnValue(root);
      vi.stubEnv("NODE_ENV", "production");
      vi.resetModules();
      const fresh = await import("./read");
      await expect(fresh.helpIndex(language)).rejects.toThrow("is missing");
      // The pages are carried, one of them without a title: the failure is the same, and the call
      // reads again instead of keeping an index with a hole.
      cpSync(DIRECTORIES[language], directory, { recursive: true });
      writeFileSync(path.join(directory, "FBS-4.1.md"), "no heading\n");
      await expect(fresh.helpIndex(language)).rejects.toThrow("FBS-4.1.md has no title");
      writeFileSync(path.join(directory, "FBS-4.1.md"), "# Revisions\n");
      const index = await fresh.helpIndex(language);
      const revisions = index.find((entry) => fileOf(entry.target) === "FBS-4.1.md");
      expect(revisions?.title).toBe("Revisions");
      vi.unstubAllEnvs();
    },
  );

  it.each([
    ["fr", "Gestion des utilisateurs", "La valeur acquise"],
    ["en", "User management", "Earned value"],
  ] as const)(
    "indexes, in %s, the title of every page written, the screens then the notions [WF-IHM-0140-A]",
    async (language, user, notion) => {
      const index = await helpIndex(language);
      expect(index.length).toBe(
        HELP_CODES.filter((code) => written({ kind: "screen", code }, language)).length +
          notions(language).length,
      );
      expect(index[0]).toEqual({ target: { kind: "screen", code: "FBS-1.1" }, title: user });
      expect(index.map((entry) => entry.title)).toContain(notion);
    },
  );

  it("keeps an index by language, each of the pages of its own [WF-IHM-0140-A]", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    try {
      const fresh = await import("./read");
      const french = await fresh.helpIndex("fr");
      const english = await fresh.helpIndex("en");
      expect(english.map((entry) => entry.target)).toEqual(french.map((entry) => entry.target));
      expect(english.map((entry) => entry.title)).not.toContain("Gestion des utilisateurs");
      expect(french.map((entry) => entry.title)).not.toContain("User management");
      // Kept: the same promise, each language its own.
      expect(fresh.helpIndex("en")).toBe(fresh.helpIndex("en"));
      expect(await fresh.helpIndex("fr")).toBe(french);
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("refuses, as a server action, a target that names no page the help may have [WF-IHM-0140-A]", async () => {
    expect(await readHelp({ kind: "screen", code: "../../package.json" }, "fr")).toBeUndefined();
    expect(await readHelp({ kind: "notion", name: "../FBS-4.3" }, "fr")).toBeUndefined();
    expect(await readHelp(null as unknown as HelpTarget, "fr")).toBeUndefined();
    expect((await readHelp({ kind: "notion", name: "indices" }, "fr"))?.page.kind).toBe("written");
  });

  it.each([["de"], ["../fr"], ["fr/../../src"], [""], [null], [undefined]])(
    "refuses, as a server action, a language the interface is not offered in: %o [WF-IHM-0140-A]",
    async (language) => {
      expect(
        await readHelp({ kind: "notion", name: "indices" }, language as unknown as Locale),
      ).toBeUndefined();
    },
  );

  it.each([
    ["fr", "Les indices de coût et de délai"],
    ["en", "Cost and schedule indices"],
  ] as const)(
    "reads, as a server action, the page and the index in the language asked, %s, and says it [WF-IHM-0140-A]",
    async (language, title) => {
      const reading = await readHelp({ kind: "notion", name: "indices" }, language);
      expect(reading?.language).toBe(language);
      expect(reading?.page.kind === "written" ? reading.page.title : undefined).toBe(title);
      expect(reading?.index).toEqual(await helpIndex(language));
    },
  );

  it("refuses, where the path is written, a file outside the directory of the help [WF-IHM-0140-A]", async () => {
    // The action refuses such a target first; the reading holds the same bound for any caller
    // (#1462). The file named here exists: the README of the repository, three levels up.
    await expect(readHelpPage({ kind: "screen", code: "../../../README" }, "fr")).rejects.toThrow(
      "outside the directory of the help",
    );
  });
});

describe("the links, the search and the screens of the help", () => {
  it.each([
    [{ kind: "screen", code: "FBS-4.3" }, "FBS-4.4.md", { kind: "screen", code: "FBS-4.4" }],
    [
      { kind: "screen", code: "FBS-4.3" },
      "notions/valeur-acquise.md",
      { kind: "notion", name: "valeur-acquise" },
    ],
    [{ kind: "notion", name: "indices" }, "../FBS-4.5.md", { kind: "screen", code: "FBS-4.5" }],
    [
      { kind: "notion", name: "indices" },
      "valeur-acquise.md",
      { kind: "notion", name: "valeur-acquise" },
    ],
    [{ kind: "screen", code: "FBS-4.3" }, "https://example.org/FBS-4.4.md", undefined],
    [{ kind: "screen", code: "FBS-4.3" }, "FBS-9.9.md", undefined],
    [{ kind: "screen", code: "FBS-4.3" }, "FBS-4.4.md#colonnes", undefined],
    [{ kind: "notion", name: "indices" }, "../../package.json", undefined],
  ] as const)("resolves a link of %o to %s", (from, href, to) => {
    expect(linkTarget(from, href)).toEqual(to);
  });

  it("finds the pages whose title holds every word, accents and capitals aside", () => {
    const index = [
      { target: { kind: "notion", name: "valeur-acquise" }, title: "La valeur acquise" },
      { target: { kind: "notion", name: "budget-de-reference" }, title: "Le budget de référence" },
    ] as const;
    expect(searched(index, "REFERENCE").map((entry) => entry.title)).toEqual([
      "Le budget de référence",
    ]);
    expect(searched(index, "acquise valeur")).toHaveLength(1);
    expect(searched(index, "  ")).toEqual([]);
    // The ligature NFD does not decompose is spelt out, on the title and on the query.
    const ligatures = [
      { target: { kind: "notion", name: "oeuvre" }, title: "Cœur de l’œuvre" },
    ] as const;
    expect(searched(ligatures, "coeur oeuvre")).toHaveLength(1);
    expect(searched(ligatures, "CŒUR")).toHaveLength(1);
  });

  it.each([
    ["/projects/p/revisions/r/planning", "FBS-4.3"],
    ["/projects/p/revisions/r/kanban", "FBS-4.5.3"],
    ["/projects/p/revisions", "FBS-4.1"],
    ["/", "FBS-4"],
    ["/admin/users", "FBS-1.1"],
    ["/account", undefined],
  ])("knows the code of the screen at %s [WF-IHM-0140-A]", (pathname, code) => {
    expect(helpCodeAt(pathname)).toBe(code);
  });

  it("takes only a code of the table or a notion well named as a target [WF-IHM-0140-A]", () => {
    expect(isHelpTarget({ kind: "screen", code: "FBS-4.3.2" })).toBe(true);
    expect(isHelpTarget({ kind: "screen", code: "FBS-9" })).toBe(false);
    expect(isHelpTarget({ kind: "notion", name: "Valeur acquise" })).toBe(false);
  });
});
