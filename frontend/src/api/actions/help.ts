// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server action of the online help (US-0580): the panel asks the server of Next for a page of
 * the help — that of the screen shown, when it opens; another, when a link or a search leads to it —
 * and for the index of the titles the search reads. The files are read where they live, on the
 * server (`src/help/read.ts`); the API has no part in it.
 *
 * The page is read in the language of the interface, which the panel sends (US-0670b): the help of
 * an interface in English is the English help, never the French one in its place.
 *
 * A server action is reachable by any request: the target is checked against the codes of the table
 * and the form of the name of a notion, and the language against the languages of the interface,
 * before any file is named from them, so that no path is ever built from what a request says.
 */
"use server";

import { type HelpReading, type HelpTarget, isHelpTarget } from "@/help/help";
import { helpIndex, readHelpPage } from "@/help/read";
import { isLocale, type Locale } from "@/i18n/locale";

/** Whether a value a request sent is a target of the help, in its form. */
function wellFormed(target: unknown): target is HelpTarget {
  if (typeof target !== "object" || target === null) {
    return false;
  }
  const { kind, code, name } = target as { kind?: unknown; code?: unknown; name?: unknown };
  return (
    (kind === "screen" && typeof code === "string") ||
    (kind === "notion" && typeof name === "string")
  );
}

/**
 * Read a page of the help and the index of the pages written, in a language of the interface;
 * `undefined` for a target that names no page the help may have, or a language it is not written in.
 */
export async function readHelp(
  target: HelpTarget,
  language: Locale,
): Promise<HelpReading | undefined> {
  if (!wellFormed(target) || !isHelpTarget(target) || !isLocale(language)) {
    return undefined;
  }
  const kept: HelpTarget =
    target.kind === "screen"
      ? { kind: "screen", code: target.code }
      : { kind: "notion", name: target.name };
  const [page, index] = await Promise.all([readHelpPage(kept, language), helpIndex(language)]);
  return { language, page, index };
}
