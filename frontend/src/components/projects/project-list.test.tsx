// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { ListPages, ProjectList } from "./project-list";

/** Render in English, as the shell hands its texts to a screen. */
function html(children: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** What a rendering says, its tags left out. */
function text(markup: string): string {
  return markup
    .replaceAll(/<[^>]*>/g, " ")
    .replaceAll(/\s+/g, " ")
    .trim();
}

/** The links of a rendering: their address, and what they say. */
function links(markup: string): string[][] {
  return [...markup.matchAll(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/g)].map((match) => [
    match[1]?.replaceAll("&amp;", "&") ?? "",
    text(match[2] ?? ""),
  ]);
}

describe("the pages of the list of projects", () => {
  it("leads to the pages before and after the one shown, the filter kept, and says how many projects the list holds", () => {
    // The second page of a hundred and twenty projects, as `PaginationMeta` gives it.
    const page = { limit: 50, offset: 50, total: 120 };
    const filtered = html(<ListPages page={page} shown={50} filtered />);
    expect(filtered).toContain("120 projects");
    expect(filtered).toMatch(/<nav[^>]*aria-label="Pages of the list"/);
    expect(links(filtered)).toEqual([
      ["/", "Previous projects"],
      ["/?offset=100", "Next projects"],
    ]);
    const lifted = html(<ListPages page={page} shown={50} filtered={false} />);
    expect(links(lifted)).toEqual([
      ["/?is_contributor=false", "Previous projects"],
      ["/?is_contributor=false&offset=100", "Next projects"],
    ]);
  });

  it("offers no page after the last one", () => {
    const page = { limit: 50, offset: 100, total: 120 };
    expect(links(html(<ListPages page={page} shown={20} filtered />))).toEqual([
      ["/?offset=50", "Previous projects"],
    ]);
  });
});

describe("a page asked beyond the end of the list", () => {
  it.each([
    [true, "/?offset=50"],
    [false, "/?is_contributor=false&offset=50"],
  ])(
    "says it is beyond the list, never that there is no project, and leads to its last page (filtered: %s)",
    (filtered, last) => {
      // Sixty projects, the page of the third fifty asked.
      const markup = html(
        <ProjectList
          projects={[]}
          page={{ limit: 50, offset: 100, total: 60 }}
          filtered={filtered}
        />,
      );
      expect(text(markup)).toBe(
        "60 projects The page asked for lies beyond the end of the list. Previous projects",
      );
      expect(text(markup)).not.toMatch(/no project/i);
      expect(markup).not.toContain("<table");
      expect(links(markup)).toEqual([[last, "Previous projects"]]);
    },
  );

  it("leads to the last page however far beyond the end the address asks", () => {
    const markup = html(
      <ProjectList projects={[]} page={{ limit: 50, offset: 500, total: 100 }} filtered />,
    );
    expect(links(markup)).toEqual([["/?offset=50", "Previous projects"]]);
  });

  it("says there is no project only when the list holds none", () => {
    const empty = { limit: 50, offset: 0, total: 0 };
    expect(text(html(<ProjectList projects={[]} page={empty} filtered />))).toBe(
      "You contribute to no project.",
    );
    expect(text(html(<ProjectList projects={[]} page={empty} filtered={false} />))).toBe(
      "No project.",
    );
  });
});
