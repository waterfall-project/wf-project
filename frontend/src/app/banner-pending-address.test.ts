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

import ts from "typescript";
import { describe, expect, it } from "vitest";

const APP = import.meta.dirname;

/** The pages of the routes, by their path under `app/`. */
function pages(): string[] {
  return readdirSync(APP, { recursive: true, encoding: "utf8" })
    .filter((file) => /(^|[/\\])page\.tsx$/.test(file))
    .map((file) => relative(APP, join(APP, file)).split(sep).join("/"));
}

/** The name of the tag of a JSX element, as written: `PendingAddress`, `ContextBanner`. */
function tagName(node: ts.Node, file: ts.SourceFile): string | undefined {
  if (ts.isJsxSelfClosingElement(node)) {
    return node.tagName.getText(file);
  }
  return ts.isJsxElement(node) ? node.openingElement.tagName.getText(file) : undefined;
}

/**
 * The banners a page writes outside any `PendingAddress` it writes, by their offset: none when it
 * writes no `PendingAddress` — the banner then shares the address among its own chips and choices.
 * The source is read by the parser of TypeScript, which tells an element from its props whatever
 * they hold — the `>` of an arrow function included (#3760).
 */
function bannersBeside(source: string): number[] {
  const file = ts.createSourceFile(
    "page.tsx",
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const written = { sharing: false };
  const beside: number[] = [];
  const visit = (node: ts.Node, under: boolean) => {
    const name = tagName(node, file);
    if (name === "PendingAddress") {
      written.sharing = true;
    } else if (name === "ContextBanner" && !under) {
      beside.push(node.getStart(file));
    }
    // A self-closing `PendingAddress` holds nothing: an element with children shares around them.
    const holds = under || (name === "PendingAddress" && ts.isJsxElement(node));
    ts.forEachChild(node, (child) => {
      visit(child, holds);
    });
  };
  visit(file, false);
  return written.sharing ? beside : [];
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
    expect(bannersBeside(`<><PendingAddress />${banner}</>`)).toHaveLength(1);
  });

  it("is told under one whose props hold a `>`, and beside one closed before it (#3760)", () => {
    const banner = "<ContextBanner reading={read} />";
    const kept = "<PendingAddress kept={(a) => a > 1}>";
    expect(bannersBeside(`${kept}${banner}<Grid /></PendingAddress>`)).toEqual([]);
    expect(bannersBeside(`<>${kept}<Grid /></PendingAddress>${banner}</>`)).toHaveLength(1);
  });
});
