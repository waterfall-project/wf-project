// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The duration of the reading of a revision, on a platform of one project and on one of six hundred
 * (`make measure-scale`, US-2970/L2, WF-DAT-0050-A): « La durée de lecture d'une révision est la
 * même sur une plateforme d'un projet et sur une plateforme de six cents projets. » It plays on a
 * platform at a time, which the recipe of the Makefile prepares — the witness freshly loaded, then
 * the reference set restored at six hundred projects —, and writes what it read in a file of its
 * own (`E2E_SCALE_FILE`). The first play, on the witness, chooses the revisions: the marked ones of
 * PRJ-001, the same on both platforms, the reference set being built on the witness. The second,
 * given the file of the first (`E2E_SCALE_BASELINE`), reads those revisions and writes the
 * comparison (`E2E_SCALE_REPORT`): the gap of each read and of their sum, and the finding when it
 * exceeds a quarter (`scale.ts`). The durations are those of the API from the request to the whole
 * answer, planning and everything it takes included: a duration, not a plan. Not a path, and no
 * duration fails it: only a read that does not answer.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import { test } from "@playwright/test";

import { administratorReady, measureUsers, renewedToken } from "./accounts";
import { caller } from "./background";
import { compareScale, type ScalePlatform } from "./scale";
import { PROJECT } from "./steps";
import { markedOf, projectCount, revisionReads, revisionsOf } from "./volumes";

/** The passes of each read, after the first, which is read cold apart. */
const PASSES = Number(process.env.E2E_SCALE_PASSES ?? "9");

/** What a play writes: the platform, and the revisions it read, so that the next reads the same. */
interface Played extends ScalePlatform {
  readonly revisions: readonly string[];
}

/** Write a JSON file, its folder made. */
function written(file: string, content: unknown): void {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, `${JSON.stringify(content, null, 2)}\n`);
  console.log(`Written: ${file}`);
}

test("reads the same revisions of PRJ-001 on the platform and compares their durations to the other platform's [WF-DAT-0050-A]", async ({
  browser,
  playwright,
}) => {
  test.setTimeout(30 * 60_000);
  const file = process.env.E2E_SCALE_FILE ?? "";
  if (file === "" || !Number.isInteger(PASSES) || PASSES < 2) {
    throw new Error("E2E_SCALE_FILE is given by make measure-scale, E2E_SCALE_PASSES is 2 or more");
  }
  const baseline = process.env.E2E_SCALE_BASELINE ?? "";
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    await administratorReady(browser);
    const {
      users: [person],
    } = await measureUsers(browser, calls, 1);
    if (person === undefined) {
      throw new Error("no user to read as");
    }
    const api = caller(calls, renewedToken(browser, person));
    const first =
      baseline === "" ? undefined : (JSON.parse(readFileSync(baseline, "utf8")) as Played);
    const revisions =
      first?.revisions ?? markedOf(await revisionsOf(api, PROJECT)).map((one) => one.revision_id);
    const projects = await projectCount(api);
    const reads = await revisionReads(api, PROJECT, revisions, PASSES);
    for (const read of reads) {
      console.log(
        `${read.name}: first ${String(read.first_s)} s, median ${String(read.median_s)} s`,
      );
    }
    const played: Played = { projects, reads, revisions };
    written(file, played);
    if (first !== undefined) {
      const comparison = compareScale(first, played);
      console.log(comparison.note);
      const report = process.env.E2E_SCALE_REPORT ?? "";
      if (report === "") {
        throw new Error("E2E_SCALE_REPORT is given by make measure-scale with the baseline");
      }
      written(report, { taken_at: new Date().toISOString(), passes: PASSES, ...comparison });
    }
  } finally {
    await calls.dispose();
  }
});
