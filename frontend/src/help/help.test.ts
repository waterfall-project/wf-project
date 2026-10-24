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
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { readHelp } from "@/api/actions/help";

import {
  fileOf,
  HELP_CODES,
  type HelpTarget,
  helpCodeAt,
  isHelpTarget,
  linkTarget,
  SCREEN_HEADINGS,
} from "./help";
import { helpDirectory, helpIndex, parseHelp, readHelpPage } from "./read";

/** The codes whose page is still to write, by the lot that writes it. */
const SCREENS_TO_COME: Readonly<Record<string, string>> = Object.fromEntries([
  ...[
    "FBS-1.1",
    "FBS-1.2",
    "FBS-1.3",
    "FBS-1.4",
    "FBS-1.5",
    "FBS-2.1",
    "FBS-2.2",
    "FBS-2.3",
    "FBS-2.4",
    "FBS-2.5",
    "FBS-2.6",
    "FBS-2.7",
    "FBS-3.1",
    "FBS-3.1.1",
    "FBS-3.1.2",
    "FBS-3.2",
    "FBS-3.2.1",
    "FBS-3.2.2",
    "FBS-3.2.3",
    "FBS-3.3",
    "FBS-3.4",
  ].map((code) => [code, "US-0580/L4, #1139"] as const),
  ...[
    "FBS-4",
    "FBS-4.2",
    "FBS-4.2.1",
    "FBS-4.2.2",
    "FBS-4.2.3",
    "FBS-4.2.4",
    "FBS-4.2.5",
    "FBS-4.3.1",
    "FBS-4.3.4",
    "FBS-4.3.5",
    "FBS-4.4.4",
    "FBS-4.5.3",
    "FBS-4.7",
    "FBS-4.8",
    "FBS-4.8.1",
    "FBS-4.8.2",
    "FBS-4.8.3",
    "FBS-4.8.4",
    "FBS-4.8.5",
    "FBS-4.8.6",
    "FBS-4.8.7",
    "FBS-4.8.8",
    "FBS-4.9",
  ].map((code) => [code, "US-0580/L5, #1140"] as const),
]);

/** The notions still to write, by the lot that writes them, which the pages may link to already. */
const NOTIONS_TO_COME: Readonly<Record<string, string>> = {
  "reste-a-engager": "US-0580/L4, #1139",
  "provision-et-reserve": "US-0580/L4, #1139",
  "avenant-et-differentiel": "US-0580/L4, #1139",
  lotissement: "US-0580/L4, #1139",
  "chemin-critique": "US-0580/L4, #1139",
};

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
      terms.set(plain(cells[1]), plain(cells[2]));
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
    expect(HELP_CODES.filter((code) => written({ kind: "screen", code }))).toEqual([
      "FBS-4.1",
      "FBS-4.3",
      "FBS-4.3.2",
      "FBS-4.3.3",
      "FBS-4.4",
      "FBS-4.4.1",
      "FBS-4.4.2",
      "FBS-4.4.3",
      "FBS-4.5",
      "FBS-4.5.1",
      "FBS-4.5.2",
      "FBS-4.6",
      "FBS-4.6.1",
      "FBS-4.6.2",
    ]);
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

  it("quotes the glossary of the specification in every notion, word for word [WF-IHM-0140-A]", () => {
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

describe("the reading of the help", () => {
  it("reads the page of a screen in its sections, [WF-IHM-0140-A]", async () => {
    const page = await readHelpPage({ kind: "screen", code: "FBS-4.4" });
    expect(page.kind).toBe("written");
    if (page.kind === "written") {
      expect(page.title).toBe("Chiffrage et devis");
      expect(page.sections.map((section) => section.heading)).toEqual([...SCREEN_HEADINGS]);
    }
  });

  it("says a page not written yet is to come", async () => {
    expect(await readHelpPage({ kind: "screen", code: "FBS-1.1" })).toEqual({
      kind: "pending",
      target: { kind: "screen", code: "FBS-1.1" },
    });
    expect((await readHelpPage({ kind: "notion", name: "lotissement" })).kind).toBe("pending");
  });

  it("indexes the title of every page written, the screens then the notions", async () => {
    const index = await helpIndex();
    expect(index.length).toBe(14 + 5);
    expect(index[0]).toEqual({
      target: { kind: "screen", code: "FBS-4.1" },
      title: "Gestion des révisions",
    });
    expect(index.map((entry) => entry.title)).toContain("La valeur acquise");
  });

  it("refuses, as a server action, a target that names no page the help may have", async () => {
    expect(await readHelp({ kind: "screen", code: "../../package.json" })).toBeUndefined();
    expect(await readHelp({ kind: "notion", name: "../FBS-4.3" })).toBeUndefined();
    expect(await readHelp(null as unknown as HelpTarget)).toBeUndefined();
    expect((await readHelp({ kind: "notion", name: "indices" }))?.page.kind).toBe("written");
  });
});

describe("the links and the screens of the help", () => {
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

  it.each([
    ["/projects/p/revisions/r/planning", "FBS-4.3"],
    ["/projects/p/revisions/r/kanban", "FBS-4.5.3"],
    ["/projects/p/revisions", "FBS-4.1"],
    ["/", "FBS-4"],
    ["/admin/users", "FBS-1.1"],
    ["/account", undefined],
  ])("knows the code of the screen at %s", (pathname, code) => {
    expect(helpCodeAt(pathname)).toBe(code);
  });

  it("takes only a code of the table or a notion well named as a target", () => {
    expect(isHelpTarget({ kind: "screen", code: "FBS-4.3.2" })).toBe(true);
    expect(isHelpTarget({ kind: "screen", code: "FBS-9" })).toBe(false);
    expect(isHelpTarget({ kind: "notion", name: "Valeur acquise" })).toBe(false);
  });
});
