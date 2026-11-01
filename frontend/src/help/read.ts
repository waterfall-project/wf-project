// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the files of the help, on the server alone (US-0580): the page of a screen or of a
 * notion, cut into its sections by its headings of the second level, its title its heading of the
 * first; and the index of the titles of every page written, which the search of the panel reads. A
 * page whose file is not written yet is a page to come, which the panel says as such.
 *
 * Each reading is in a language of the interface, under the directory of that language (US-0670b):
 * a page missing in English is a failure, as one missing in French, never the French page in its
 * place, which would let a page forgotten pass for one written.
 *
 * The section of the columns of a screen that shows a grid is followed by the definitions of its
 * columns, from the configuration of the grid, by the same keys of the catalogues as the tooltips of
 * its headers (`columns.<grid>.<column>.help`): one source for both, never the Markdown.
 *
 * The directory is that of the front (`process.cwd()`), as `next dev`, `next start` and the
 * standalone server of the image all run there; the files are traced into the standalone output by
 * `outputFileTracingIncludes` (`next.config.ts`).
 */
import "server-only";

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import { accessRoleGrid, userGrid } from "@/components/admin/admin-grids";
import { backupGrid } from "@/components/admin/backup-columns";
import { auditGrid } from "@/components/audit/audit-columns";
import { COST_GRID, KEPT_HEADING } from "@/components/costs/cost-grid";
import type { GridColumn } from "@/components/grid/columns";
import { ESTIMATE_GRID } from "@/components/grid/estimate";
import { PLANNING_GRID } from "@/components/grid/planning";
import { REMAINING_GRID } from "@/components/grid/remaining";
import { PROJECT_GRID } from "@/components/portfolio/portfolio-grid";
import { PROJECT_LIST_GRID } from "@/components/projects/project-list-grid";
import {
  BREAKDOWN_GRID,
  CONTRIBUTOR_GRID,
  subprojectGrid,
} from "@/components/projects/settings-grids";
import { costCategoryGrid, costTypeGrid } from "@/components/reference/cost-grids";
import { RATE_HEADINGS } from "@/components/reference/rate-columns";
import { calendarGrid, orgNodeGrid, resourceRoleGrid } from "@/components/reference/resource-grids";
import { COMPARISON_GRID } from "@/components/revisions/comparison-columns";
import { RISK_GRID } from "@/components/risks/risk-grid";
import { isLocale, LOCALES, type Locale } from "@/i18n/locale";

import {
  fileOf,
  HELP_CODES,
  type HelpColumn,
  type HelpEntry,
  type HelpPage,
  type HelpSection,
  type HelpTarget,
} from "./help";
import { NOTIONS_TO_COME, SCREENS_TO_COME } from "./to-come";

/**
 * The directory of the pages of the help in a language of the interface. A value that names none
 * fails, before any path is built from it: the bound of `readText` starts from this directory, and
 * a language such as `../fr` would move it along (#1811).
 */
export function helpDirectory(language: Locale): string {
  if (!isLocale(language)) {
    throw new Error(`The help is written in no language ${String(language)}.`);
  }
  return path.join(process.cwd(), "help", language);
}

type AnyColumn = Pick<GridColumn<never, string, never>, "label" | "help" | "computed">;

/** The columns of a grid that bear a definition, in the order the grid shows them. */
function defined(columns: readonly AnyColumn[]): HelpColumn[] {
  return columns.flatMap((column) =>
    column.help === undefined
      ? []
      : [{ label: column.label, help: column.help, computed: column.computed !== undefined }],
  );
}

/**
 * The columns of several grids of one screen, each definition once: the columns of the state and of
 * the modification of the reference data are the same in each of its lists.
 */
function distinct(...grids: readonly (readonly AnyColumn[])[]): HelpColumn[] {
  const columns = defined(grids.flat());
  return columns.filter(
    (column, at) => columns.findIndex((other) => other.help === column.help) === at,
  );
}

/** The tables of the reference data, as a session that may modify them sees them. */
const COST_TYPES = costTypeGrid(true).columns;
const COST_CATEGORIES = costCategoryGrid(true).columns;
const HOURLY_RATES: readonly AnyColumn[] = Object.values(RATE_HEADINGS);
const ORG_NODES = orgNodeGrid(true).columns;
const RESOURCE_ROLES = resourceRoleGrid(true).columns;
const CALENDARS = calendarGrid(true).columns;

/** The tables of the settings of a project, as a session that may modify them sees them. */
const WORK_BREAKDOWN = BREAKDOWN_GRID.columns;
const SUBPROJECTS = subprojectGrid(true).columns;
const CONTRIBUTORS = CONTRIBUTOR_GRID.columns;

/**
 * The columns each screen defines: the grid of its function and the section of the grid itself;
 * the column a section of a single column is; the grids of a screen of the reference data or of
 * the settings of a project, each definition once, and the grids of its sections; the lines of the
 * actual costs, every column kept from the file being defined alike; the comparison of two
 * revisions, the one grid of their management. A table is defined with
 * every column a session may see there — those of its commands included, which only a session that
 * may exercise them sees.
 */
const COLUMNS: Readonly<Record<string, readonly HelpColumn[]>> = {
  "FBS-1.1": defined(userGrid({ roles: () => [], rename: undefined }).columns),
  "FBS-1.2": defined(accessRoleGrid(true).columns),
  "FBS-1.4": defined(backupGrid({ marks: true, downloads: true, restores: true }).columns),
  "FBS-1.5": defined(auditGrid({ functions: [], revision: false }).columns),
  "FBS-2.1": defined(PROJECT_GRID.columns),
  "FBS-3.1": distinct(COST_TYPES, COST_CATEGORIES, HOURLY_RATES),
  "FBS-3.1.1": distinct(COST_TYPES, COST_CATEGORIES),
  "FBS-3.1.2": defined(HOURLY_RATES),
  "FBS-3.2": distinct(ORG_NODES, RESOURCE_ROLES, CALENDARS),
  "FBS-3.2.1": defined(ORG_NODES),
  "FBS-3.2.2": defined(RESOURCE_ROLES),
  "FBS-3.2.3": defined(CALENDARS),
  "FBS-4": defined(PROJECT_LIST_GRID.columns),
  "FBS-4.1": defined(COMPARISON_GRID.columns),
  "FBS-4.2": distinct(WORK_BREAKDOWN, SUBPROJECTS, CONTRIBUTORS),
  "FBS-4.2.1": defined(WORK_BREAKDOWN),
  "FBS-4.2.3": defined(SUBPROJECTS),
  "FBS-4.2.4": defined(CONTRIBUTORS),
  "FBS-4.3": defined(PLANNING_GRID.columns),
  "FBS-4.3.2": defined(PLANNING_GRID.columns),
  "FBS-4.3.3": defined(PLANNING_GRID.columns).filter((column) => column.label === "gantt"),
  "FBS-4.4": defined(ESTIMATE_GRID.columns),
  "FBS-4.4.2": defined(ESTIMATE_GRID.columns),
  "FBS-4.4.3": defined(ESTIMATE_GRID.columns).filter(
    (column) => column.label === "referenceAmount",
  ),
  "FBS-4.5": defined(REMAINING_GRID.columns),
  "FBS-4.5.2": defined(REMAINING_GRID.columns),
  "FBS-4.6": defined(RISK_GRID.columns),
  "FBS-4.6.1": defined(RISK_GRID.columns),
  "FBS-4.7": defined([...COST_GRID.columns, KEPT_HEADING]),
};

/** A page cut at its headings: its title, what precedes its first section, and its sections. */
export interface ParsedHelp {
  readonly title: string;
  readonly intro: string;
  readonly sections: readonly HelpSection[];
}

/**
 * Cut the Markdown of a page: its first line is its title, `# …`; each heading `## …` opens a
 * section. `undefined` for a file without a title.
 */
export function parseHelp(markdown: string): ParsedHelp | undefined {
  const [first, ...lines] = markdown.replace(/\r\n/g, "\n").split("\n");
  const title = /^# (.+)$/.exec(first ?? "")?.[1]?.trim();
  if (title === undefined) {
    return undefined;
  }
  const intro: string[] = [];
  const sections: { heading: string; lines: string[] }[] = [];
  for (const line of lines) {
    const heading = /^## (.+)$/.exec(line)?.[1];
    if (heading !== undefined) {
      sections.push({ heading: heading.trim(), lines: [] });
    } else {
      (sections.at(-1)?.lines ?? intro).push(line);
    }
  }
  return {
    title,
    intro: intro.join("\n").trim(),
    sections: sections.map((section) => ({
      heading: section.heading,
      body: section.lines.join("\n").trim(),
    })),
  };
}

/**
 * The text of a file of the help, or `undefined` when it is not written. The file is read inside
 * the directory of the help, or the reading fails: the action refuses a target that names no page
 * before any file is named from it (`actions/help.ts`), and the bound holds here too, where the
 * path is written, for any caller (#1462).
 */
async function readText(file: string, language: Locale): Promise<string | undefined> {
  const directory = helpDirectory(language);
  const resolved = path.resolve(directory, file);
  if (!resolved.startsWith(directory + path.sep)) {
    throw new Error(`The file ${file} is outside the directory of the help.`);
  }
  try {
    return await readFile(resolved, "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return undefined;
    }
    throw error;
  }
}

/** Whether the page is one the lots of the help have yet to write (`to-come.ts`). */
function isToCome(target: HelpTarget): boolean {
  return target.kind === "screen"
    ? SCREENS_TO_COME[target.code] !== undefined
    : NOTIONS_TO_COME[target.name] !== undefined;
}

/**
 * Read a page of the help in a language: written, cut into its sections, or to come. A page that
 * should be written and whose file is missing or has no title is a failure, not a page to come: a
 * file the build did not carry, or a translation forgotten, must not pass for help still to write.
 */
export async function readHelpPage(target: HelpTarget, language: Locale): Promise<HelpPage> {
  const file = fileOf(target);
  const text = await readText(file, language);
  if (text === undefined) {
    if (isToCome(target)) {
      return { kind: "pending", target };
    }
    throw new Error(`The page of the help ${file} is missing from ${helpDirectory(language)}.`);
  }
  const parsed = parseHelp(text);
  if (parsed === undefined) {
    throw new Error(`The page of the help ${file} has no title.`);
  }
  return {
    kind: "written",
    target,
    ...parsed,
    columns: target.kind === "screen" ? (COLUMNS[target.code] ?? []) : [],
  };
}

/** The names of the notions written in a language, by their files. */
async function notionsWrittenIn(language: Locale): Promise<string[]> {
  try {
    const files = await readdir(path.join(helpDirectory(language), "notions"));
    return files.filter((file) => file.endsWith(".md")).map((file) => file.slice(0, -".md".length));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return [];
    }
    throw error;
  }
}

/**
 * The names of the notions the help has, in the order of their names: those written in any language
 * of the interface. A notion written in one and missing from another is a page that should be
 * written there, which fails the index of that language instead of leaving a hole in it (#1823).
 */
async function notionNames(): Promise<string[]> {
  const written = await Promise.all(LOCALES.map((language) => notionsWrittenIn(language)));
  return [...new Set(written.flat())].sort((one, other) => one.localeCompare(other));
}

/**
 * The index of the pages written in each language, read once by the process: the files do not
 * change under it.
 */
const indexed = new Map<Locale, Promise<HelpEntry[]>>();

async function readIndex(language: Locale): Promise<HelpEntry[]> {
  const targets: HelpTarget[] = [
    ...HELP_CODES.map((code) => ({ kind: "screen", code }) as const),
    ...(await notionNames()).map((name) => ({ kind: "notion", name }) as const),
  ];
  // A page that should be written and is missing or untitled fails the index, as it fails its own
  // reading, so that the process does not keep an index with a hole in it.
  const entries = await Promise.all(
    targets.map(async (target) => {
      const page = await readHelpPage(target, language);
      return page.kind === "written" ? [{ target, title: page.title }] : [];
    }),
  );
  return entries.flat();
}

/**
 * The index of the pages written in a language: the screens in the order of the table, then the
 * notions in the order of their names, each by its title, which the search reads. The panel asks for
 * it at every page it opens, so the process keeps one by language, except under `next dev`, where
 * the author changes the pages and reads them again.
 */
export function helpIndex(language: Locale): Promise<HelpEntry[]> {
  if (process.env.NODE_ENV === "development") {
    return readIndex(language);
  }
  const kept = indexed.get(language);
  if (kept !== undefined) {
    return kept;
  }
  const reading = readIndex(language).catch((error: unknown) => {
    indexed.delete(language);
    throw error;
  });
  indexed.set(language, reading);
  return reading;
}
