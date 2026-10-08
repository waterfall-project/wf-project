// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { ROW_REM } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { RATE_SORTS, type RateSort } from "./rate-columns";
import { type HourlyRateGrid, RateGrid } from "./rate-grid";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const RATE = "PUT /reference/cost-categories/{cost_category_id}/hourly-rates/{year}";
// The grid of the volumes: a hundred and fifty categories of labour over fifteen years. Its third
// row, the mechanical engineering of level 1, has no rate before 2016.
const grid = example("volume/hourly_rate_grid") as HourlyRateGrid;
const MECHANICAL = 2;
const MECHANICAL_ID = "01926f3a-7c00-7000-8000-000400000000";
/** The height of a row of the grid, as the grid computes it on the default font of the browsers. */
const ROW_HEIGHT = ROW_REM * 16;
// The first rows of that grid, for the tests of the entry: a cell entered renders the rows in view
// anew, a screenful of a hundred and fifty took each keystroke a third of a second under happy-dom,
// and the test went past its time under load (#315). The volume is the first test's alone.
const FIRST_ROWS = 8;
const fewRows: HourlyRateGrid = { ...grid, rows: grid.rows.slice(0, FIRST_ROWS) };

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(
    { [RATE]: "hourly_rate_entered", "PATCH /me/preferences": "preferences", ...answers },
    { hold: () => hold },
  );
  server.client = client;
  return client;
}

/** The grid of the rates in a language, open to entry or not: its first rows unless the whole is asked. */
function rates(
  locale: Locale = "fr",
  editable = true,
  rows: HourlyRateGrid = fewRows,
  query: GridQuery<RateSort> = { sort: undefined, search: undefined },
) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <RateGrid
        grid={rows}
        currency="EUR"
        editable={editable}
        query={query}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the grid asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

/** The button that sorts by a column, by its heading. */
function sortButton(heading: string): HTMLElement {
  const header = within(screen.getByRole("grid"))
    .getAllByRole("columnheader")
    .find((each) => each.textContent === heading);
  const button = header?.querySelector("button");
  if (button === null || button === undefined) {
    throw new Error(`no sort on the column ${heading}`);
  }
  return button;
}

/** The cell of a row, by its index among the rows of the answer, and of a year. */
function cell(row: number, year: number): HTMLElement {
  const found = screen
    .getByRole("grid")
    .querySelector<HTMLElement>(
      `td[data-row="${row.toString()}"][data-column="year_${year.toString()}"]`,
    );
  if (found === null) {
    throw new Error(`no cell of ${year.toString()} in the row ${row.toString()}`);
  }
  return found;
}

/** Wait until a cell no longer shows a write under way: the server answered it. */
async function answered(row: number, year: number) {
  await vi.waitFor(() => {
    expect(cell(row, year)).not.toHaveAttribute("aria-busy");
  });
}

/** The writes the grid sent: the rate, and what was written. */
function written(client: FakeClient) {
  return client.calls
    .filter((call) => call.route === RATE)
    .map((call) => ({ path: call.path, body: call.body }));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  page.search = "";
});

describe("the grid of the hourly rates", () => {
  it("is the dense grid: a hundred and fifty categories of labour over fifteen years, in the order of the server (US-0250)", () => {
    serve();
    render(rates("fr", true, grid));
    const table = screen.getByRole("grid", { name: "Grille des taux horaires" });
    // The header, the hundred and fifty categories, the totals: a row count the window keeps.
    expect(table).toHaveAttribute("aria-rowcount", "152");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers).toEqual([
      "Code",
      "Libellé",
      "État",
      ...grid.years.map((year) => year.toString()),
    ]);
    expect(cell(0, 2026)).toHaveTextContent(/^80,00$/);
    // A year without a rate is an empty cell, never a zero.
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^$/);
    // The totals row says the currency of the rates, and sums nothing.
    const totals = table.querySelector("tfoot tr");
    expect(totals?.textContent).toBe("150 catégories, taux horaires en EUR");
  });

  it("breaks no rule of accessibility, a window of the hundred and fifty categories rendered", async () => {
    serve();
    // A window of two rows — some fourteen rendered, with the overscan of the grid —: the rules of
    // axe hold for each row alike, and a screenful took as long to check as to render — past its
    // time under load (#315).
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2 * ROW_HEIGHT);
    const { container } = render(rates("fr", true, grid));
    await expectAccessible(container);
  });

  it("enters the first rate of a year without a version, shows the rate the server answered, and the cursor goes to the next row [WF-IHM-0040-A]", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    const client = serve(
      {},
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    render(rates());
    cell(MECHANICAL, 2015).focus();
    // What is typed differs from what the server answers: shown under way, then the answer.
    await userEvent.keyboard("85{Enter}");
    expect(cell(MECHANICAL + 1, 2015)).toHaveFocus();
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^85,00$/);
    expect(cell(MECHANICAL, 2015)).toHaveAttribute("aria-busy", "true");
    answer();
    await answered(MECHANICAL, 2015);
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^85,48$/);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(written(client)).toEqual([
      {
        path: `/reference/cost-categories/${MECHANICAL_ID}/hourly-rates/2015`,
        body: { amount: "85" },
      },
    ]);
  });

  it("corrects a rate with the version read, and shows the rate the server answered", async () => {
    const client = serve({ [RATE]: "hourly_rate_corrected" });
    render(rates());
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("{F2}");
    const field = screen.getByRole("textbox", { name: "2016" });
    expect(field).toHaveValue("86,98");
    await userEvent.clear(field);
    await userEvent.keyboard("87{Enter}");
    await answered(MECHANICAL, 2016);
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^87,20$/);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(written(client)).toEqual([
      {
        path: `/reference/cost-categories/${MECHANICAL_ID}/hourly-rates/2016`,
        body: { amount: "87", lock_version: 1 },
      },
    ]);
  });

  it("corrects a rate twice, the second time with the version the first answer gave", async () => {
    const client = serve({ [RATE]: ["hourly_rate_corrected", "hourly_rate_corrected"] });
    render(rates());
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("87{Enter}{ArrowUp}");
    await answered(MECHANICAL, 2016);
    await userEvent.keyboard("88{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    await answered(MECHANICAL, 2016);
    expect(written(client).map(({ body }) => body)).toEqual([
      { amount: "87", lock_version: 1 },
      { amount: "88", lock_version: 2 },
    ]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("takes no rate the server answered for another year, says the failure of the service, and leaves the cell as it was", async () => {
    // The rate of 2016 answered to a write of 2015.
    serve({ [RATE]: "hourly_rate_corrected" });
    render(rates());
    cell(MECHANICAL, 2015).focus();
    await userEvent.keyboard("85{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Erreur inattendue du service.");
    await answered(MECHANICAL, 2015);
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^$/);
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^86,98$/);
  });

  it("leaves a cell at its rate when its entry is abandoned [WF-IHM-0040-A]", async () => {
    const client = serve();
    render(rates());
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("99{Escape}");
    expect(within(screen.getByRole("grid")).queryByRole("textbox")).toBeNull();
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^86,98$/);
    expect(cell(MECHANICAL, 2016)).toHaveFocus();
    expect(written(client)).toEqual([]);
  });

  it("says a rate the server refuses — one already entered for the year, a value out of range —, the cell kept as it was", async () => {
    serve({
      [RATE]: [
        { problem: { code: "ALREADY_EXISTS", status: 409 } },
        { problem: { code: "VALUE_OUT_OF_RANGE", status: 422 } },
      ],
    });
    render(rates());
    cell(MECHANICAL, 2015).focus();
    await userEvent.keyboard("85,48{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Cet élément existe déjà.");
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^$/);
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("0{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La valeur sort des limites admises.",
    );
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^86,98$/);
  });

  it("says a correction sent with a version another one has made stale, the cell kept as it was", async () => {
    const stale = example("hourly_rate_stale") as Problem & { status: 412 };
    const client = serve({ [RATE]: { problem: stale } });
    render(rates());
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("87{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Quelqu’un a modifié cette donnée entre-temps ; rechargez-la pour voir sa dernière version.",
    );
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^86,98$/);
    expect(written(client)).toEqual([
      {
        path: `/reference/cost-categories/${MECHANICAL_ID}/hourly-rates/2016`,
        body: { amount: "87", lock_version: 1 },
      },
    ]);
  });

  it("offers no entry where the session may not modify the cost settings", async () => {
    const client = serve();
    render(rates("fr", false));
    expect(cell(MECHANICAL, 2016)).toHaveAttribute("aria-readonly", "true");
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("{F2}85");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(written(client)).toEqual([]);
    // Nor the column of a year to add.
    expect(screen.queryByRole("form", { name: "Ajouter une année à la grille" })).toBeNull();
  });

  it("says the state of each category, a deactivated one the page read on demand said so [WF-REF-0150-A]", () => {
    serve();
    const [first, second, ...rest] = fewRows.rows;
    if (first === undefined || second === undefined) {
      throw new Error("the grid of the volumes has its first rows");
    }
    render(
      rates("fr", true, { ...fewRows, rows: [first, { ...second, is_active: false }, ...rest] }),
    );
    const state = (row: number) =>
      screen
        .getByRole("grid")
        .querySelector(`td[data-row="${row.toString()}"][data-column="state"]`);
    expect(state(0)).toHaveTextContent(/^Actif$/);
    expect(state(1)).toHaveTextContent(/^Désactivé$/);
  });

  it("adds the column of a year the grid has none for, empty, in the order of the years, the rates of the other years unchanged [WF-REF-0060-A]", async () => {
    const client = serve();
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2011");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    const headers = within(screen.getByRole("grid"))
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers).toEqual([
      "Code",
      "Libellé",
      "État",
      "2011",
      ...grid.years.map((year) => year.toString()),
    ]);
    // The column added is empty, row by row; the rates of the years before are as they were.
    for (let row = 0; row < FIRST_ROWS; row += 1) {
      expect(cell(row, 2011)).toHaveTextContent(/^$/);
    }
    expect(cell(0, 2012)).toHaveTextContent(/^59,00$/);
    expect(cell(0, 2026)).toHaveTextContent(/^80,00$/);
    expect(within(form).getByRole("status")).toHaveTextContent(
      "Colonne 2011 ajoutée : elle reste vide jusqu’à son premier taux",
    );
    // Nothing is written until a rate is entered in it: the contract has no column to create.
    expect(written(client)).toEqual([]);
  });

  it("refuses the column of a year the grid already has, or that the contract does not take, and adds none [WF-REF-0060-A]", async () => {
    serve();
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    const year = within(form).getByRole("textbox", { name: "Année" });
    const add = within(form).getByRole("button", { name: "Ajouter la colonne" });
    await userEvent.type(year, "2026");
    await userEvent.click(add);
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "L’année 2026 a déjà sa colonne dans la grille.",
    );
    expect(year).toHaveAttribute("aria-invalid", "true");
    expect(year).toHaveAccessibleDescription("L’année 2026 a déjà sa colonne dans la grille.");
    const grid2026 = within(screen.getByRole("grid")).getAllByRole("columnheader", {
      name: "2026",
    });
    expect(grid2026).toHaveLength(1);
    await userEvent.clear(year);
    await userEvent.type(year, "1999");
    await userEvent.click(add);
    expect(within(form).getByRole("alert")).toHaveTextContent("Une année va de 2000 à 2100.");
    // A year added once is the grid's: a second time, it is refused as well.
    await userEvent.clear(year);
    await userEvent.type(year, "2011");
    await userEvent.click(add);
    expect(within(form).queryByRole("alert")).toBeNull();
    await userEvent.type(year, "2011");
    await userEvent.click(add);
    expect(within(form).getByRole("alert")).toHaveTextContent(
      "L’année 2011 a déjà sa colonne dans la grille.",
    );
    expect(
      within(screen.getByRole("grid")).getAllByRole("columnheader", { name: "2011" }),
    ).toHaveLength(1);
  });

  it("enters the first rate of the year added without a version, and shows the rate the server answered [WF-REF-0060-A]", async () => {
    const client = serve({ [RATE]: "hourly_rate_added_year" });
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2011");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    cell(0, 2011).focus();
    await userEvent.keyboard("57,5{Enter}");
    await answered(0, 2011);
    expect(cell(0, 2011)).toHaveTextContent(/^57,50$/);
    expect(cell(0, 2012)).toHaveTextContent(/^59,00$/);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(written(client)).toEqual([
      {
        path: "/reference/cost-categories/01926f3a-7c00-7000-8000-000000000402/hourly-rates/2011",
        body: { amount: "57.5" },
      },
    ]);
  });

  it("keeps the column of a year added through the entry of its rates and of the other years", async () => {
    serve({ [RATE]: ["hourly_rate_added_year", "hourly_rate_corrected"] });
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2011");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    cell(0, 2011).focus();
    await userEvent.keyboard("57,5{Enter}");
    await answered(0, 2011);
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("87{Enter}");
    await answered(MECHANICAL, 2016);
    expect(cell(MECHANICAL, 2016)).toHaveTextContent(/^87,20$/);
    expect(cell(0, 2011)).toHaveTextContent(/^57,50$/);
  });

  it("takes away the column of a year added while it holds no rate, the headers as they were, and keeps one whose rate was entered", async () => {
    serve({ [RATE]: "hourly_rate_added_year" });
    render(rates());
    const headers = () =>
      within(screen.getByRole("grid"))
        .getAllByRole("columnheader")
        .map((header) => header.textContent);
    const before = headers();
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    const year = within(form).getByRole("textbox", { name: "Année" });
    const add = within(form).getByRole("button", { name: "Ajouter la colonne" });
    await userEvent.type(year, "2027");
    await userEvent.click(add);
    expect(headers()).toContain("2027");
    await userEvent.click(within(form).getByRole("button", { name: "Retirer la colonne 2027" }));
    expect(headers()).toEqual(before);
    expect(within(form).queryByRole("button", { name: /^Retirer/ })).toBeNull();
    // A column whose first rate was entered is the server's: it is no longer taken away.
    await userEvent.type(year, "2011");
    await userEvent.click(add);
    cell(0, 2011).focus();
    await userEvent.keyboard("57,5{Enter}");
    await answered(0, 2011);
    expect(within(form).queryByRole("button", { name: "Retirer la colonne 2011" })).toBeNull();
    expect(headers()).toContain("2011");
  });

  it("offers no removal of the column of a year added while its first rate is being written", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    serve(
      { [RATE]: "hourly_rate_added_year" },
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2011");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    expect(within(form).getByRole("button", { name: "Retirer la colonne 2011" })).toBeVisible();
    cell(0, 2011).focus();
    await userEvent.keyboard("57,5{Enter}");
    expect(cell(0, 2011)).toHaveAttribute("aria-busy", "true");
    expect(within(form).queryByRole("button", { name: /^Retirer/ })).toBeNull();
    answer();
    await answered(0, 2011);
    expect(within(form).queryByRole("button", { name: /^Retirer/ })).toBeNull();
  });

  it("offers the removal again once the first rate of the column is refused", async () => {
    serve({ [RATE]: { problem: { code: "VALUE_OUT_OF_RANGE", status: 422 } } });
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2011");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    cell(0, 2011).focus();
    await userEvent.keyboard("0{Enter}");
    await answered(0, 2011);
    expect(within(form).getByRole("button", { name: "Retirer la colonne 2011" })).toBeVisible();
  });

  it.each([
    ["Code", "code"],
    ["Libellé", "label"],
    ["État", "is_active"],
    ["2012", "rate.2012"],
    ["2026", "rate.2026"],
  ])(
    "asks the server for the sort by the column %s, both ways, under the names of the contract [WF-IHM-0060-A]",
    async (heading, column) => {
      serve();
      page.search = "search=Automatisme&offset=50";
      const { rerender } = render(rates());
      await userEvent.click(sortButton(heading));
      // Back to the first page, the search kept.
      const ascending = `/reference/costs?search=Automatisme&sort_by=${column}&sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      page.search = ascending.split("?")[1] ?? "";
      const sort = RATE_SORTS.find((each) => each === column);
      rerender(
        rates("fr", true, fewRows, {
          sort: sort && { column: sort, order: "asc" },
          search: "Automatisme",
        }),
      );
      await userEvent.click(sortButton(heading));
      expect(lastAddress()).toBe(
        `/reference/costs?search=Automatisme&sort_by=${column}&sort_order=desc`,
      );
    },
  );

  it("sorts by the rate of a year it added, which the server takes as any year", async () => {
    serve();
    render(rates());
    const form = screen.getByRole("form", { name: "Ajouter une année à la grille" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Année" }), "2027");
    await userEvent.click(within(form).getByRole("button", { name: "Ajouter la colonne" }));
    await userEvent.click(sortButton("2027"));
    expect(lastAddress()).toBe("/reference/costs?sort_by=rate.2027&sort_order=asc");
  });

  it("shows a page of the categories the server sorted by the rate of a year, the years of the whole grid, its totals the number retained, and leads to the next page", () => {
    serve();
    page.search = "sort_by=rate.2026&sort_order=desc";
    const sorted = example("volume/hourly_rate_grid_by_rate") as HourlyRateGrid;
    render(
      rates("fr", true, sorted, {
        sort: { column: "rate.2026", order: "desc" },
        search: undefined,
      }),
    );
    const table = screen.getByRole("grid", { name: "Grille des taux horaires" });
    // The header, the fifty categories of the page, the totals.
    expect(table).toHaveAttribute("aria-rowcount", "52");
    expect(within(table).getByRole("columnheader", { name: /2026/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    expect(cell(0, 2026)).toHaveTextContent(/^119,92$/);
    expect(table.querySelector("tfoot tr")?.textContent).toBe(
      "150 catégories, taux horaires en EUR",
    );
    expect(
      screen.getByRole("navigation", { name: "Pages de «\u00a0Grille des taux horaires\u00a0»" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Page précédente/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Page suivante/ })).toHaveAttribute(
      "href",
      "/reference/costs?sort_by=rate.2026&sort_order=desc&offset=50",
    );
  });

  it("is named and headed in English too", () => {
    serve();
    render(rates("en"));
    const table = screen.getByRole("grid", { name: "Hourly rate grid" });
    expect(within(table).getByRole("columnheader", { name: "Label" })).toBeVisible();
    expect(table.querySelector("tfoot tr")?.textContent).toBe(
      "150 categories, hourly rates in EUR",
    );
    expect(cell(0, 2026)).toHaveTextContent(/^80\.00$/);
  });
});
