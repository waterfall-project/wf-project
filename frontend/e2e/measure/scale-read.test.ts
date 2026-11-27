// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the comparison of the two platforms by the measure of a version (`scale-read.ts`,
 * US-2970): a tool of the measure, which carries the criterion of its own and cites the story.
 */
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterAll, describe, expect, it } from "vitest";

import { compareScale, summary } from "./scale";
import { scaleRead } from "./scale-read";

const directory = mkdtempSync(join(tmpdir(), "scale-read-"));
afterAll(() => {
  rmSync(directory, { recursive: true, force: true });
});

/** A comparison as `scale.measure.ts` writes it. */
function written() {
  const platform = (projects: number) => ({
    projects,
    reads: [summary("revision a", 0.5, [0.02, 0.03])],
  });
  return {
    taken_at: "2026-11-27T14:16:32.913Z",
    passes: 2,
    ...compareScale(platform(5), platform(393)),
  };
}

describe("scaleRead", () => {
  it("gives none without a file: the comparison is a measure of its own [US-2970]", () => {
    expect(scaleRead("")).toBeUndefined();
    expect(scaleRead(join(directory, "absent.json"))).toBeUndefined();
  });

  it("gives the comparison the file holds [US-2970]", () => {
    const file = join(directory, "scale.json");
    writeFileSync(file, JSON.stringify(written()));
    expect(scaleRead(file)).toEqual(written());
  });

  it("refuses a JSON that is invalid, naming the file [US-2970]", () => {
    const broken = join(directory, "broken.json");
    writeFileSync(broken, "{ not json");
    expect(() => scaleRead(broken)).toThrow(new RegExp(`${broken}: not a JSON`));
  });

  it("refuses a file that is not a comparison [US-2970]", () => {
    const other = join(directory, "other.json");
    writeFileSync(other, JSON.stringify({ finding: true }));
    expect(() => scaleRead(other)).toThrow(/not the comparison make measure-scale writes/);
  });
});
