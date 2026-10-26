// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The online help as files (WF-IHM-0140, US-0580): every code of the FBS that has a screen has its
 * page in French, or waits for it in the list below, which names the lot that writes it; the page of
 * a screen keeps the fixed structure; a notion quotes the glossary of the specification without
 * rewriting it; every link leads to a page the help has, or will have; no page holds raw HTML.
 *
 * The list of the pages still to write never lies: a code that receives its file must leave it, and
 * a code it names must be one the table has. The English version is a gap of WF-IHM-0140, until its
 * translation is decided (#1075): nothing is asked of `help/en/` yet.
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

import {
  fileOf,
  HELP_CODES,
  type HelpTarget,
  helpCodeAt,
  isHelpTarget,
  linkTarget,
  SCREEN_HEADINGS,
  searched,
} from "./help";
import { helpDirectory, helpIndex, parseHelp, readHelpPage } from "./read";
import { NOTIONS_TO_COME, SCREENS_TO_COME } from "./to-come";

/** The headings of the page of a notion: what the glossary says, what Waterfall makes of it, and nearby. */
const NOTION_HEADINGS = ["Ce que dit le glossaire", "Dans Waterfall", "Voir aussi"];

const DIRECTORY = helpDirectory();

/** Whether the file of a page is written. */
function written(target: HelpTarget): boolean {
  return existsSync(path.join(DIRECTORY, fileOf(target)));
}

/** The names of the notions written. */
function notions(): string[] {
  return readdirSync(path.join(DIRECTORY, "notions"))
    .filter((file) => file.endsWith(".md"))
    .map((file) => file.slice(0, -".md".length));
}

/** Every page written, with its text. */
function pages(): { target: HelpTarget; text: string }[] {
  const targets: HelpTarget[] = [
    ...HELP_CODES.map((code) => ({ kind: "screen", code }) as const),
    ...notions().map((name) => ({ kind: "notion", name }) as const),
  ];
  return targets.filter(written).map((target) => ({
    target,
    text: readFileSync(path.join(DIRECTORY, fileOf(target)), "utf8"),
  }));
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

/** The links of a Markdown text, their targets as written. */
function links(text: string): string[] {
  return [...text.matchAll(/\]\(([^)]*)\)/g)].map((match) => match[1] ?? "");
}

describe("the pages of the help", () => {
  it("has a page in French for every code of the FBS that has a screen, or the lot that writes it [WF-IHM-0140-A]", () => {
    const missing = HELP_CODES.filter(
      (code) => !written({ kind: "screen", code }) && SCREENS_TO_COME[code] === undefined,
    );
    expect(missing).toEqual([]);
    // The list of the pages to come never lies: none of them written, each a code of the table.
    const writtenToCome = Object.keys(SCREENS_TO_COME).filter((code) =>
      written({ kind: "screen", code }),
    );
    expect(writtenToCome).toEqual([]);
    expect(Object.keys(SCREENS_TO_COME).filter((code) => !HELP_CODES.includes(code))).toEqual([]);
    // Every code of the table is written or to come, never both and never neither.
    expect(HELP_CODES.length).toBe(
      HELP_CODES.filter((code) => written({ kind: "screen", code })).length +
        Object.keys(SCREENS_TO_COME).length,
    );
  });

  it("writes the notions of the earned value, and lists those to come without writing them [WF-IHM-0140-A]", () => {
    expect(notions().sort()).toEqual([
      "budget-de-reference",
      "indices",
      "revisions",
      "valeur-acquise",
      "valeur-planifiee",
    ]);
    expect(notions().filter((name) => NOTIONS_TO_COME[name] !== undefined)).toEqual([]);
  });

  it("gives the page of every screen the fixed structure of the help, each section filled [WF-IHM-0140-A]", () => {
    for (const { target, text } of pages().filter((page) => page.target.kind === "screen")) {
      const parsed = parseHelp(text);
      expect(parsed?.title, fileOf(target)).toBeTruthy();
      expect(parsed?.intro, fileOf(target)).toBe("");
      expect(
        parsed?.sections.map((section) => section.heading),
        fileOf(target),
      ).toEqual([...SCREEN_HEADINGS]);
      expect(
        parsed?.sections.filter((section) => section.body === "").map((section) => section.heading),
        fileOf(target),
      ).toEqual([]);
    }
  });

  it("quotes the glossary of the specification in every notion, word for word but the identifiers of requirement [WF-IHM-0140-A]", () => {
    const terms = glossary();
    expect(terms.size).toBeGreaterThan(50);
    for (const { target, text } of pages().filter((page) => page.target.kind === "notion")) {
      const parsed = parseHelp(text);
      expect(
        parsed?.sections.map((section) => section.heading),
        fileOf(target),
      ).toEqual(NOTION_HEADINGS);
      const quotes = (parsed?.sections[0]?.body ?? "")
        .split("\n")
        .filter((line) => line.startsWith(">"))
        .map((line) => /^> \*\*(.+?)\*\* — (.+)$/.exec(line));
      expect(quotes.length, fileOf(target)).toBeGreaterThan(0);
      for (const quote of quotes) {
        expect(quote, fileOf(target)).not.toBeNull();
        const term = plain(quote?.[1] ?? "");
        expect(quote?.[2], `${fileOf(target)}: ${term}`).not.toMatch(/WF-[A-Z]{3}-\d{4}/);
        expect(plain(quote?.[2] ?? ""), `${fileOf(target)}: ${term}`).toBe(terms.get(term));
      }
    }
  });

  it("links every page to pages the help has, or to pages to come [WF-IHM-0140-A]", () => {
    const broken: string[] = [];
    for (const { target, text } of pages()) {
      for (const href of links(text)) {
        const to = linkTarget(target, href);
        const known =
          to !== undefined &&
          (written(to) ||
            (to.kind === "screen"
              ? SCREENS_TO_COME[to.code] !== undefined
              : NOTIONS_TO_COME[to.name] !== undefined));
        if (!known) {
          broken.push(`${fileOf(target)} → ${href}`);
        }
      }
    }
    expect(broken).toEqual([]);
  });

  it("holds neither raw HTML nor images in any page [WF-IHM-0140-A]", () => {
    const offending = pages().filter(({ text }) => /<[a-z/!]|!\[/i.test(text));
    expect(offending.map(({ target }) => fileOf(target))).toEqual([]);
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
    const page = await readHelpPage({ kind: "screen", code: "FBS-4.4" });
    expect(page.kind).toBe("written");
    if (page.kind === "written") {
      expect(page.title).toBe("Chiffrage et devis");
      expect(page.sections.map((section) => section.heading)).toEqual([...SCREEN_HEADINGS]);
      expect(page.columns.map((column) => column.help)).toContain("estimate.referenceAmount");
      expect(page.columns.find((column) => column.help === "estimate.category")?.computed).toBe(
        false,
      );
      expect(
        page.columns.find((column) => column.help === "estimate.referenceAmount")?.computed,
      ).toBe(true);
    }
    const column = await readHelpPage({ kind: "screen", code: "FBS-4.4.3" });
    expect(column.kind === "written" ? column.columns.map((each) => each.label) : []).toEqual([
      "referenceAmount",
    ]);
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
  ])(
    "names the columns of %s, each with a label and a definition key [WF-IHM-0140-A]",
    async (code) => {
      const page = await readHelpPage({ kind: "screen", code });
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
      const page = await readHelpPage({ kind: "screen", code });
      const helps = page.kind === "written" ? page.columns.map((column) => column.help) : [];
      expect(helps).toHaveLength(7);
      expect(helps.every((help) => help.startsWith("risks."))).toBe(true);
      expect(helps).toEqual([
        "risks.label",
        "risks.probability",
        "risks.severity",
        "risks.provisionAmount",
        "risks.state",
        "risks.lastReview",
        "risks.matrixCell",
      ]);
    },
  );

  it("says a page not written yet is to come [WF-IHM-0140-A]", async () => {
    expect(await readHelpPage({ kind: "screen", code: "FBS-1.1" })).toEqual({
      kind: "pending",
      target: { kind: "screen", code: "FBS-1.1" },
    });
    expect((await readHelpPage({ kind: "notion", name: "lotissement" })).kind).toBe("pending");
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
      const page = await readHelpPage({ kind: "screen", code });
      expect(page.kind).toBe("written");
      if (page.kind === "written") {
        expect(page.title).toBe(title);
      }
    },
  );

  it("fails on a page that should be written and whose file is missing, and says a page to come [WF-IHM-0140-A]", async () => {
    const root = mkdtempSync(path.join(tmpdir(), "waterfall-help-"));
    folders.push(root);
    mkdirSync(path.join(root, "help", "fr"), { recursive: true });
    vi.spyOn(process, "cwd").mockReturnValue(root);
    // FBS-4.3 has a page, which this directory does not carry, as a standalone build that forgot it.
    await expect(readHelpPage({ kind: "screen", code: "FBS-4.3" })).rejects.toThrow("FBS-4.3.md");
    await expect(readHelpPage({ kind: "notion", name: "indices" })).rejects.toThrow("indices.md");
    expect((await readHelpPage({ kind: "screen", code: "FBS-1.1" })).kind).toBe("pending");
  });

  it("fails the index on a page that should be written and is missing or untitled, and does not keep it [WF-IHM-0140-A]", async () => {
    const root = mkdtempSync(path.join(tmpdir(), "waterfall-help-"));
    folders.push(root);
    mkdirSync(path.join(root, "help", "fr"), { recursive: true });
    vi.spyOn(process, "cwd").mockReturnValue(root);
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    const fresh = await import("./read");
    await expect(fresh.helpIndex()).rejects.toThrow("is missing");
    // The pages are carried, one of them without a title: the failure is the same, and the call
    // reads again instead of keeping an index with a hole.
    cpSync(DIRECTORY, path.join(root, "help", "fr"), { recursive: true });
    writeFileSync(path.join(root, "help", "fr", "FBS-4.1.md"), "no heading\n");
    await expect(fresh.helpIndex()).rejects.toThrow("FBS-4.1.md has no title");
    writeFileSync(path.join(root, "help", "fr", "FBS-4.1.md"), "# Révisions\n");
    expect((await fresh.helpIndex())[0]?.title).toBe("Révisions");
    vi.unstubAllEnvs();
  });

  it("indexes the title of every page written, the screens then the notions [WF-IHM-0140-A]", async () => {
    const index = await helpIndex();
    expect(index.length).toBe(
      HELP_CODES.filter((code) => written({ kind: "screen", code })).length + notions().length,
    );
    expect(index[0]).toEqual({
      target: { kind: "screen", code: "FBS-4.1" },
      title: "Gestion des révisions",
    });
    expect(index.map((entry) => entry.title)).toContain("La valeur acquise");
  });

  it("refuses, as a server action, a target that names no page the help may have [WF-IHM-0140-A]", async () => {
    expect(await readHelp({ kind: "screen", code: "../../package.json" })).toBeUndefined();
    expect(await readHelp({ kind: "notion", name: "../FBS-4.3" })).toBeUndefined();
    expect(await readHelp(null as unknown as HelpTarget)).toBeUndefined();
    expect((await readHelp({ kind: "notion", name: "indices" }))?.page.kind).toBe("written");
  });

  it("refuses, where the path is written, a file outside the directory of the help [WF-IHM-0140-A]", async () => {
    // The action refuses such a target first; the reading holds the same bound for any caller
    // (#1462). The file named here exists: the README of the repository, three levels up.
    await expect(readHelpPage({ kind: "screen", code: "../../../README" })).rejects.toThrow(
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
