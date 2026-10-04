// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { type HourlyRateGrid, RateGrid } from "./rate-grid";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(),
}));

const RATE = "PUT /reference/cost-categories/{cost_category_id}/hourly-rates/{year}";
// The grid of the volumes: a hundred and fifty categories of labour over fifteen years. Its third
// row, the mechanical engineering of level 1, has no rate before 2016.
const grid = example("volume/hourly_rate_grid") as HourlyRateGrid;
const MECHANICAL = 2;
const MECHANICAL_ID = "01926f3a-7c00-7000-8000-000400000000";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient({ [RATE]: "hourly_rate_entered", ...answers }, { hold: () => hold });
  server.client = client;
  return client;
}

/** The grid of the rates in a language, open to entry or not. */
function rates(locale: Locale = "fr", editable = true) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <RateGrid
        grid={grid}
        currency="EUR"
        editable={editable}
        query={{ sort: undefined, search: undefined }}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
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
});

describe("the grid of the hourly rates", () => {
  it("is the dense grid: a hundred and fifty categories of labour over fifteen years, in the order of the server (US-0250)", async () => {
    serve();
    const { container } = render(rates());
    const table = screen.getByRole("grid", { name: "Grille des taux horaires" });
    // The header, the hundred and fifty categories, the totals: a row count the window keeps.
    expect(table).toHaveAttribute("aria-rowcount", "152");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers).toEqual(["Code", "Libellé", ...grid.years.map((year) => year.toString())]);
    expect(cell(0, 2026)).toHaveTextContent(/^80,00$/);
    // A year without a rate is an empty cell, never a zero.
    expect(cell(MECHANICAL, 2015)).toHaveTextContent(/^$/);
    // The totals row says the currency of the rates, and sums nothing.
    const totals = table.querySelector("tfoot tr");
    expect(totals?.textContent).toBe("Taux horaires en EUR");
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
    expect(screen.queryByRole("textbox")).toBeNull();
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

  it("offers no entry where the session may not modify the cost settings", async () => {
    const client = serve();
    render(rates("fr", false));
    expect(cell(MECHANICAL, 2016)).toHaveAttribute("aria-readonly", "true");
    cell(MECHANICAL, 2016).focus();
    await userEvent.keyboard("{F2}85");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(written(client)).toEqual([]);
  });

  it("is named and headed in English too", () => {
    serve();
    render(rates("en"));
    const table = screen.getByRole("grid", { name: "Hourly rate grid" });
    expect(within(table).getByRole("columnheader", { name: "Label" })).toBeVisible();
    expect(table.querySelector("tfoot tr")?.textContent).toBe("Hourly rates in EUR");
    expect(cell(0, 2026)).toHaveTextContent(/^80\.00$/);
  });
});
