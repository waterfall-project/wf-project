// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The banner of the reading context changes the address — a chip lifts its filter, a choice opens
 * another structure or another revision — from the address last asked (US-2330). A screen whose
 * other parts change it too — a grid, a filter, the pages of a list — shares that address among
 * them (`PendingAddress`), and must render its banner under it: a banner rendered beside would go
 * on from the address shown, and a filter lifted just before a revision is chosen would come back
 * (défaut n° 20 de `typescript.md`).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

const APP = import.meta.dirname;

/** The pages of the routes, by their path under `app/`. */
function pages(): string[] {
  return readdirSync(APP, { recursive: true, encoding: "utf8" })
    .filter((file) => /(^|[/\\])page\.tsx$/.test(file))
    .map((file) => relative(APP, join(APP, file)).split(sep).join("/"));
}

/**
 * The banners a page writes outside any `PendingAddress` it writes, by their offset: none when it
 * writes no `PendingAddress` — the banner then shares the address among its own chips and choices.
 */
function bannersBeside(source: string): number[] {
  if (!/<PendingAddress\b/.test(source)) {
    return [];
  }
  const beside: number[] = [];
  let depth = 0;
  for (const tag of source.matchAll(
    /<PendingAddress\b[^>]*?(\/)?>|<\/PendingAddress>|<ContextBanner\b/g,
  )) {
    const [text] = tag;
    if (text.startsWith("<ContextBanner")) {
      if (depth === 0) {
        beside.push(tag.index);
      }
    } else if (text.startsWith("</")) {
      depth -= 1;
    } else if (tag[1] === undefined) {
      depth += 1;
    }
  }
  return beside;
}

describe("the banner of a screen that shares the address last asked", () => {
  it("is rendered under it, so that a revision chosen goes on from the address asked [WF-IHM-0020-A]", () => {
    const sharing = pages().filter((file) => {
      const source = readFileSync(join(APP, file), "utf8");
      return /<ContextBanner\b/.test(source) && /<PendingAddress\b/.test(source);
    });
    // Not vacuous: the grids, the risks, the exchanges, the settings, the revisions share one.
    expect(sharing.length).toBeGreaterThanOrEqual(8);
    const beside = sharing.filter(
      (file) => bannersBeside(readFileSync(join(APP, file), "utf8")).length > 0,
    );
    expect(beside).toEqual([]);
  });

  it("is told beside one written before it, or after it", () => {
    const banner = "<ContextBanner reading={read} />";
    const shared = "<PendingAddress><Grid /></PendingAddress>";
    expect(bannersBeside(`<>${banner}${shared}</>`)).toHaveLength(1);
    expect(bannersBeside(`<>${shared}${banner}</>`)).toHaveLength(1);
    expect(bannersBeside(`<PendingAddress>${banner}<Grid /></PendingAddress>`)).toEqual([]);
  });
});
