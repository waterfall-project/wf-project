// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The online help (WF-IHM-0140, US-0580): a page of Markdown for each code of the FBS that has a
 * screen — a function, a leaf with a screen of its own, a section its function's screen shows, the
 * list of the projects —, and a page for each notion of the method, under `frontend/help/<language>/`
 * (`<code>.md`, `notions/<notion>.md`). The table of the functions is its key: the code of the screen
 * shown is that of the route the address follows.
 *
 * Neither server nor client: what the panel of the help and the reading of its files share — what a
 * page is, which codes have one, where a link between pages leads. The files
 * are read on the server alone (`read.ts`).
 */
import { FUNCTION_GROUPS, findScreen } from "@/navigation/functions";

/**
 * The language the help is written in: French alone, the English version being decided once the
 * author has read the French (#1075) — an interface in English shows the French help until then,
 * a gap written under WF-IHM-0140 in the file of EP-15.
 */
export const HELP_LANGUAGE = "fr";

/** A page of the help: that of a screen, by its code of the FBS, or that of a notion of the method. */
export type HelpTarget =
  | { readonly kind: "screen"; readonly code: string }
  | { readonly kind: "notion"; readonly name: string };

/**
 * The headings of the page of a screen, always the same, in this order (#1075): what the screen
 * shows and its part in the method; its commands, their keys and their conditions; its columns and
 * its computed values; the gestures of the keyboard; the notions and the screens nearby.
 */
export const SCREEN_HEADINGS = [
  "Ce que montre l’écran",
  "Ses commandes",
  "Ses colonnes et ses valeurs calculées",
  "Les gestes au clavier",
  "Voir aussi",
] as const;

/** A section of a page: its heading of the second level, and the Markdown under it. */
export interface HelpSection {
  readonly heading: string;
  readonly body: string;
}

/** A page of the help, written, or still to write. */
export type HelpPage =
  | {
      readonly kind: "written";
      readonly target: HelpTarget;
      readonly title: string;
      /** What comes before the first section: nothing, on the page of a screen. */
      readonly intro: string;
      readonly sections: readonly HelpSection[];
    }
  | { readonly kind: "pending"; readonly target: HelpTarget };

/** A page of the index of the pages written: what it is, and its title. */
export interface HelpEntry {
  readonly target: HelpTarget;
  readonly title: string;
}

/** What the panel receives: the page asked, and the index of the pages written. */
export interface HelpReading {
  readonly page: HelpPage;
  readonly index: readonly HelpEntry[];
}

/**
 * The codes of the FBS that have a screen, in the order of the table: the list of the projects
 * (the block of the projects), each function, its sections, its leaves.
 */
export const HELP_CODES: readonly string[] = FUNCTION_GROUPS.flatMap((group) => [
  ...(group.route === undefined ? [] : [group.code]),
  ...group.functions.flatMap((fn) => [
    fn.code,
    ...(fn.sections ?? []).map((section) => section.code),
    ...(fn.leaves ?? []).map((leaf) => leaf.code),
  ]),
]);

/** The codes of the sections of a function's screen, whose pages its own leads to. */
export function sectionsOf(code: string): readonly string[] {
  const fn = FUNCTION_GROUPS.flatMap((group) => group.functions).find((each) => each.code === code);
  return (fn?.sections ?? []).map((section) => section.code);
}

/**
 * The code of the screen an address shows: that of the function or of the leaf whose route it
 * follows, that of the list of the projects at its route; `undefined` elsewhere — the account, a
 * page of the system.
 */
export function helpCodeAt(pathname: string): string | undefined {
  const group = FUNCTION_GROUPS.find((each) => each.route === pathname);
  if (group !== undefined) {
    return group.code;
  }
  return findScreen(pathname.split("/").slice(1))?.fn.code;
}

/** The name of a notion, as its file is named: words of small letters and digits, by hyphens. */
const NOTION_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Whether a target names a page the help may have: a code with a screen, a notion well named. */
export function isHelpTarget(target: HelpTarget): boolean {
  return target.kind === "screen"
    ? HELP_CODES.includes(target.code)
    : NOTION_NAME.test(target.name);
}

/** The file of a page, under the directory of its language. */
export function fileOf(target: HelpTarget): string {
  return target.kind === "screen" ? `${target.code}.md` : `notions/${target.name}.md`;
}

/** Whether two targets name the same page. */
export function sameTarget(one: HelpTarget, other: HelpTarget): boolean {
  return fileOf(one) === fileOf(other);
}

/** A base of the URL the links of a page are resolved against, with no host nor scheme of its own. */
const BASE = "help:/";

/**
 * The page a link of a page leads to: a link relative to its file — `FBS-4.4.md` from a screen,
 * `notions/valeur-acquise.md`, `../FBS-4.3.md` from a notion —, which a reader of the files follows
 * as the panel does; `undefined` for any other, which the panel shows as text.
 */
export function linkTarget(from: HelpTarget, href: string): HelpTarget | undefined {
  let path: string;
  try {
    const url = new URL(href, BASE + fileOf(from));
    if (url.protocol !== "help:" || url.search !== "" || url.hash !== "") {
      return undefined;
    }
    path = url.pathname;
  } catch {
    return undefined;
  }
  const screen = /^\/(FBS-[\d.]+)\.md$/.exec(path);
  if (screen?.[1] !== undefined) {
    const target = { kind: "screen", code: screen[1] } as const;
    return isHelpTarget(target) ? target : undefined;
  }
  const notion = /^\/notions\/([^/]+)\.md$/.exec(path);
  if (notion?.[1] !== undefined) {
    const target = { kind: "notion", name: notion[1] } as const;
    return isHelpTarget(target) ? target : undefined;
  }
  return undefined;
}
