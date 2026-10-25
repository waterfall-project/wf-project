// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server action of the online help (US-0580): the panel asks the server of Next for a page of
 * the help — that of the screen shown, when it opens; another, when a link leads to it — and for
 * the index of the titles of the pages written. The files are read where they live, on the
 * server (`src/help/read.ts`); the API has no part in it.
 *
 * A server action is reachable by any request: the target is checked against the codes of the table
 * and the form of the name of a notion before any file is named from it, so that no path is ever
 * built from what a request says.
 */
"use server";

import { type HelpReading, type HelpTarget, isHelpTarget } from "@/help/help";
import { helpIndex, readHelpPage } from "@/help/read";

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
 * Read a page of the help and the index of the pages written; `undefined` for a target that names
 * no page the help may have.
 */
export async function readHelp(target: HelpTarget): Promise<HelpReading | undefined> {
  if (!wellFormed(target) || !isHelpTarget(target)) {
    return undefined;
  }
  const kept: HelpTarget =
    target.kind === "screen"
      ? { kind: "screen", code: target.code }
      : { kind: "notion", name: target.name };
  const [page, index] = await Promise.all([readHelpPage(kept), helpIndex()]);
  return { page, index };
}
