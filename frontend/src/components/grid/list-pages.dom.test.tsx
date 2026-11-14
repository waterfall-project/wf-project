// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The pages of a flat table (US-2080, #3073): at the right under the table, discreet — « Lignes par
 * page », the rows shown, « Précédent », the page among the pages, « Suivant » —, the two links in
 * their place, inert at the ends, everything read from the offset, the size and the total the server
 * answers, the navigation named after its list.
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage, PagedList } from "@/navigation/pages";

import { ListPages, pageSpan } from "./list-pages";

const PATHNAME = "/reference/costs";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams("category_offset=50"),
}));

const CATEGORIES: PagedList = {
  page: "category_offset",
  size: "category_limit",
  reads: ["category_offset", "category_limit"],
};

/** The pages of the categories of cost, at a page of the list, in a language. */
function pages(page: ListPage, shown: number, locale: "fr" | "en" = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <ListPages list={CATEGORIES} title="Catégories de coût" page={page} shown={shown} />
    </NextIntlClientProvider>,
  );
}

/** The navigation of the pages, named after its list. */
function navigation(): HTMLElement {
  return screen.getByRole("navigation", { name: "Pages de «\u00a0Catégories de coût\u00a0»" });
}

describe("the pages of a flat table", () => {
  it("say the rows shown and the page among the pages, between « Précédent » and « Suivant », after « Lignes par page » [WF-IHM-0060-A]", () => {
    const { container } = pages({ offset: 50, limit: 50, total: 150 }, 50);
    const nav = navigation();
    expect(within(nav).getByRole("link", { name: "Précédent" })).toHaveAttribute("href", PATHNAME);
    expect(within(nav).getByRole("link", { name: "Suivant" })).toHaveAttribute(
      "href",
      `${PATHNAME}?category_offset=100`,
    );
    expect(nav).toHaveTextContent(/^Précédent\s*Page 2 sur 3\s*Suivant$/);
    // In this order, at the right of the line: the size, the rows shown, then the navigation.
    const whole = container.firstElementChild;
    expect(whole).toHaveClass("justify-end");
    expect(whole?.textContent).toMatch(/^Lignes par page.*51–100 sur 150Précédent/);
    expect(
      screen.getByRole("combobox", { name: "Lignes par page de «\u00a0Catégories de coût\u00a0»" }),
    ).toHaveValue("50");
  });

  it("keep « Précédent » and « Suivant » in their place, inert, at the ends of the list [WF-IHM-0060-A]", () => {
    const { rerender } = pages({ offset: 0, limit: 50, total: 120 }, 50);
    const first = within(navigation());
    expect(first.getByRole("link", { name: "Précédent" })).toHaveAttribute("aria-disabled", "true");
    expect(first.getByRole("link", { name: "Précédent" })).not.toHaveAttribute("href");
    expect(first.getByRole("link", { name: "Suivant" })).not.toHaveAttribute("aria-disabled");
    expect(navigation()).toHaveTextContent("Page 1 sur 3");
    expect(screen.getByText("1–50 sur 120")).toBeVisible();
    rerender(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <ListPages
          list={CATEGORIES}
          title="Catégories de coût"
          page={{ offset: 100, limit: 50, total: 120 }}
          shown={20}
        />
      </NextIntlClientProvider>,
    );
    const last = within(navigation());
    expect(last.getByRole("link", { name: "Suivant" })).toHaveAttribute("aria-disabled", "true");
    expect(last.getByRole("link", { name: "Suivant" })).not.toHaveAttribute("href");
    expect(last.getByRole("link", { name: "Précédent" })).toHaveAttribute(
      "href",
      `${PATHNAME}?category_offset=50`,
    );
    expect(navigation()).toHaveTextContent("Page 3 sur 3");
    expect(screen.getByText("101–120 sur 120")).toBeVisible();
  });

  it("are written in English too, the numbers grouped as the language groups them [WF-IHM-0060-A]", () => {
    pages({ offset: 1000, limit: 100, total: 12_345 }, 100, "en");
    expect(screen.getByText("1,001–1,100 of 12,345")).toBeVisible();
    expect(
      screen.getByRole("navigation", { name: "Pages of “Catégories de coût”" }),
    ).toHaveTextContent(/^Previous\s*Page 11 of 124\s*Next$/);
  });
});

describe("where the page shown stands, read from the offset, the size and the total", () => {
  it.each([
    [
      "the first page",
      { offset: 0, limit: 50, total: 150 },
      50,
      { from: 1, to: 50, at: 1, pages: 3 },
    ],
    [
      "the last, short page",
      { offset: 100, limit: 50, total: 120 },
      20,
      { from: 101, to: 120, at: 3, pages: 3 },
    ],
    [
      "an offset between two pages",
      { offset: 70, limit: 50, total: 150 },
      50,
      { from: 71, to: 120, at: 2, pages: 3 },
    ],
    ["an empty list", { offset: 0, limit: 50, total: 0 }, 0, { from: 0, to: 0, at: 1, pages: 1 }],
  ])("counts %s from one [WF-IHM-0060-A]", (_name, page, shown, span) => {
    expect(pageSpan(page, shown)).toEqual(span);
  });
});
