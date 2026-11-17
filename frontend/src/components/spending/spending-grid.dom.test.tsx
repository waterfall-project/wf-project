// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { formatMoney } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { SpendingGrid } from "./spending-grid";
import { type SpendingPlan, spendingDetail } from "./spending-rows";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: FakeClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/spending",
  useSearchParams: () => new URLSearchParams(),
}));

const PLAN = example("spending") as SpendingPlan;

/** The cell of a row, by its index among the rows of the grid, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  // Laid out as a browser would: a window of rows in view.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

/** The grid of the projection of the witness, in French. */
function grid() {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <SpendingGrid
        detail={spendingDetail(PLAN)}
        revision={PLAN.context.revision_id}
        preferences={undefined}
      />
    </NextIntlClientProvider>,
  );
}

const FR = (value: string) => formatMoney(value, "fr");

describe("the grid of the spending projection", () => {
  it("is a tree grid from the cost type to the category, read only, a column for each month and one for the total [WF-DEV-0100-A]", () => {
    grid();
    const treegrid = screen.getByRole("treegrid", {
      name: "Projection de dépenses par nature de coût et par catégorie",
    });
    const rowCount = PLAN.cost_types.reduce((count, type) => count + 1 + type.categories.length, 0);
    expect(treegrid).toHaveAttribute("aria-rowcount", String(rowCount + 2));
    expect(within(treegrid).getAllByRole("columnheader")).toHaveLength(
      2 + PLAN.monthly_totals.length,
    );
    const [type] = PLAN.cost_types;
    expect(cell(0, "label")).toHaveTextContent(type?.label ?? "");
    expect(cell(0, "label").closest("tr")).toHaveAttribute("aria-level", "1");
    expect(cell(1, "label").closest("tr")).toHaveAttribute("aria-level", "2");
    expect(cell(0, "total").textContent).toBe(FR(type?.total ?? ""));
    const month = type?.months[0];
    expect(cell(0, `month_${month?.month ?? ""}`).textContent).toBe(FR(month?.amount ?? ""));
    expect(within(treegrid).queryByRole("textbox")).toBeNull();
    expect(within(treegrid).queryByRole("searchbox")).toBeNull();
  });

  it("shows the totals of the months and of the projection at the foot as the API gives them [WF-DEV-0100-A]", () => {
    grid();
    const totals = [...screen.getByRole("treegrid").querySelectorAll("tfoot td")].map(
      (each) => each.textContent,
    );
    expect(totals).toEqual([
      "Total de la projection",
      FR(PLAN.total),
      ...PLAN.monthly_totals.map(({ amount }) => FR(amount)),
    ]);
  });

  it("is accessible [WF-DEV-0100-A]", async () => {
    const { container } = grid();
    await expectAccessible(container);
  });
});
