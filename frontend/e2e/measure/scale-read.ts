// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The comparison of the reading of a revision on a platform of one project and on one of six
 * hundred (`make measure-scale`, US-2970/L2), read in the JSON it wrote, to go in the report of the
 * version: the two measures take the workstation alone and cannot nest. The report is taken without
 * it when the file is absent — the comparison is a measure of its own, and says so — and refuses a
 * file that is not what `scale.measure.ts` wrote.
 */
import { existsSync, readFileSync } from "node:fs";

import type { ScaleComparison } from "./scale";

/** What `scale.measure.ts` writes: the comparison, with when and how many passes. */
export interface ScaleWritten extends ScaleComparison {
  readonly taken_at: string;
  readonly passes: number;
}

/** The comparison in the file, none when there is no file; a file that is no comparison is refused. */
export function scaleRead(file: string): ScaleWritten | undefined {
  if (file === "" || !existsSync(file)) {
    return undefined;
  }
  let json: Partial<ScaleWritten>;
  try {
    json = JSON.parse(readFileSync(file, "utf8")) as Partial<ScaleWritten>;
  } catch (error) {
    throw new Error(
      `${file}: not a JSON (${error instanceof Error ? error.message : "unreadable"})`,
      { cause: error },
    );
  }
  if (
    typeof json.finding !== "boolean" ||
    typeof json.gap !== "number" ||
    typeof json.note !== "string" ||
    !Array.isArray(json.reads) ||
    typeof json.taken_at !== "string" ||
    typeof json.passes !== "number" ||
    json.small === undefined ||
    json.large === undefined
  ) {
    throw new Error(`${file}: not the comparison make measure-scale writes`);
  }
  return json as ScaleWritten;
}
