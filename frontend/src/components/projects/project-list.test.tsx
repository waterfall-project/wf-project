// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { isContributorFiltered } from "@/navigation/home";

import { ListPages } from "./project-list";

/** Render in English, as the shell hands its texts to a screen. */
function html(children: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** The links of a rendering: their address, and what they say. */
function links(markup: string): string[][] {
  return [...markup.matchAll(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/g)].map((match) => [
    match[1]?.replaceAll("&amp;", "&") ?? "",
    (match[2] ?? "").replace(/<[^>]*>/g, ""),
  ]);
}

describe("the pages of the list of projects", () => {
  it("leads to the pages before and after the one shown, the filter kept, and says how many projects the list holds", () => {
    // The second page of a hundred and twenty projects, as `PaginationMeta` gives it.
    const page = { limit: 50, offset: 50, total: 120 };
    const filtered = html(<ListPages page={page} shown={50} filtered />);
    expect(filtered).toContain("120 projects");
    expect(filtered).toContain('<nav aria-label="Pages of the list"');
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

describe("the filter of the home", () => {
  it.each([
    ["", true],
    ["is_contributor=true", true],
    ["is_contributor=false", false],
  ])(
    "at the address ?%s, filters on the projects the user contributes to: %s",
    (query, filtered) => {
      expect(isContributorFiltered(new URLSearchParams(query))).toBe(filtered);
    },
  );
});
