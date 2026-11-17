// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cost of the entry of the cache of the indicators, read in the JSON of `make measure-core
 * ONLY=indicators` (US-2420), which the measure of a version cannot play itself: both start from a
 * witness freshly loaded and take the workstation alone. Read before anything is prepared, so that
 * its absence costs no hour of measure.
 */
import { existsSync, readFileSync } from "node:fs";

import { type Cache, cacheOf } from "./version";

/** The cost of the cache in the file; a file that is absent, or not JSON, is refused by name. */
export function cacheRead(file: string): Cache {
  if (file === "" || !existsSync(file)) {
    throw new Error(
      `the cost of the cache of the indicators is read in ${file === "" ? "E2E_MEASURE_CACHE" : file}, ` +
        "which make measure-core ONLY=indicators JSON=<file> writes: run it first",
    );
  }
  let json: unknown;
  try {
    json = JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    throw new Error(
      `${file}: not a JSON (${error instanceof Error ? error.message : "unreadable"})`,
      { cause: error },
    );
  }
  return cacheOf(json);
}
