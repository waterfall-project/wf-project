// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the files of the help, on the server alone (US-0580): the page of a screen or of a
 * notion, cut into its sections by its headings of the second level, its title its heading of the
 * first; and the index of the titles of every page written, which the panel reads to lead a
 * function's screen to the pages of its sections. A page whose file is not written yet is a page to
 * come, which the panel says as such.
 *
 * The directory is that of the front (`process.cwd()`), as `next dev`, `next start` and the
 * standalone server of the image all run there; the files are traced into the standalone output by
 * `outputFileTracingIncludes` (`next.config.ts`).
 */
import "server-only";

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import {
  fileOf,
  HELP_CODES,
  HELP_LANGUAGE,
  type HelpEntry,
  type HelpPage,
  type HelpSection,
  type HelpTarget,
} from "./help";

/** The directory of the pages of the help in its language. */
export function helpDirectory(): string {
  return path.join(process.cwd(), "help", HELP_LANGUAGE);
}

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

/** The text of a file of the help, or `undefined` when it is not written. */
async function readText(file: string): Promise<string | undefined> {
  try {
    return await readFile(path.join(helpDirectory(), file), "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return undefined;
    }
    throw error;
  }
}

/** Read a page of the help: written, cut into its sections, or to come. */
export async function readHelpPage(target: HelpTarget): Promise<HelpPage> {
  const text = await readText(fileOf(target));
  const parsed = text === undefined ? undefined : parseHelp(text);
  if (parsed === undefined) {
    return { kind: "pending", target };
  }
  return { kind: "written", target, ...parsed };
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

/**
 * The index of the pages written: the screens in the order of the table,
 * then the notions in the order of their names, each by its title.
 */
export async function helpIndex(): Promise<HelpEntry[]> {
  const targets: HelpTarget[] = [
    ...HELP_CODES.map((code) => ({ kind: "screen", code }) as const),
    ...(await notionNames()).map((name) => ({ kind: "notion", name }) as const),
  ];
  const entries = await Promise.all(
    targets.map(async (target) => {
      const text = await readText(fileOf(target));
      const title = text === undefined ? undefined : parseHelp(text)?.title;
      return title === undefined ? [] : [{ target, title }];
    }),
  );
  return entries.flat();
}
