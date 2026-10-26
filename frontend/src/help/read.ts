// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the files of the help, on the server alone (US-0580): the page of a screen or of a
 * notion, cut into its sections by its headings of the second level, its title its heading of the
 * first; and the index of the titles of every page written, which the search of the panel reads. A
 * page whose file is not written yet is a page to come, which the panel says as such.
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

import type { GridColumn } from "@/components/grid/columns";
import { ESTIMATE_GRID } from "@/components/grid/estimate";
import { PLANNING_GRID } from "@/components/grid/planning";
import { REMAINING_GRID } from "@/components/grid/remaining";
import { RISK_GRID } from "@/components/risks/risk-grid";

import {
  fileOf,
  HELP_CODES,
  HELP_LANGUAGE,
  type HelpColumn,
  type HelpEntry,
  type HelpPage,
  type HelpSection,
  type HelpTarget,
} from "./help";
import { NOTIONS_TO_COME, SCREENS_TO_COME } from "./to-come";

/** The directory of the pages of the help in its language. */
export function helpDirectory(): string {
  return path.join(process.cwd(), "help", HELP_LANGUAGE);
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
 * The columns each screen defines: the grid of its function and the section of the grid itself;
 * the column a section of a single column is.
 */
const COLUMNS: Readonly<Record<string, readonly HelpColumn[]>> = {
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
async function readText(file: string): Promise<string | undefined> {
  const directory = helpDirectory();
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
 * Read a page of the help: written, cut into its sections, or to come. A page that should be
 * written and whose file is missing or has no title is a failure, not a page to come: a file the
 * build did not carry must not pass for help still to write.
 */
export async function readHelpPage(target: HelpTarget): Promise<HelpPage> {
  const file = fileOf(target);
  const text = await readText(file);
  if (text === undefined) {
    if (isToCome(target)) {
      return { kind: "pending", target };
    }
    throw new Error(`The page of the help ${file} is missing from ${helpDirectory()}.`);
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

/** The names of the notions written, by their files. */
async function notionNames(): Promise<string[]> {
  try {
    const files = await readdir(path.join(helpDirectory(), "notions"));
    return files
      .filter((file) => file.endsWith(".md"))
      .map((file) => file.slice(0, -".md".length))
      .sort((one, other) => one.localeCompare(other));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return [];
    }
    throw error;
  }
}

/** The index of the pages written, read once by the process: the files do not change under it. */
let indexed: Promise<HelpEntry[]> | undefined;

async function readIndex(): Promise<HelpEntry[]> {
  const targets: HelpTarget[] = [
    ...HELP_CODES.map((code) => ({ kind: "screen", code }) as const),
    ...(await notionNames()).map((name) => ({ kind: "notion", name }) as const),
  ];
  // A page that should be written and is missing or untitled fails the index, as it fails its own
  // reading, so that the process does not keep an index with a hole in it.
  const entries = await Promise.all(
    targets.map(async (target) => {
      const page = await readHelpPage(target);
      return page.kind === "written" ? [{ target, title: page.title }] : [];
    }),
  );
  return entries.flat();
}

/**
 * The index of the pages written: the screens in the order of the table, then the notions in the
 * order of their names, each by its title, which the search reads. The panel asks for it at every
 * page it opens, so the process keeps it, except under `next dev`, where the author changes the
 * pages and reads them again.
 */
export function helpIndex(): Promise<HelpEntry[]> {
  if (process.env.NODE_ENV === "development") {
    return readIndex();
  }
  indexed ??= readIndex().catch((error: unknown) => {
    indexed = undefined;
    throw error;
  });
  return indexed;
}
