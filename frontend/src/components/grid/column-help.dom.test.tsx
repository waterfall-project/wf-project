// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid, type EstimateGridProps } from "./estimate-grid";
import type { NodeList } from "./nodes";

// The headers of the columns of a grid carry their definition in a tooltip (US-0580/L2, #1137): the
// definition of the catalogue (`columns.<grid>.<column>.help`).

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const installation = example("nodes_installation") as NodeList;
const revision = example("revision") as components["schemas"]["Revision"];

/** The grid of the estimate of the witness, in a language, given what corrects its amounts. */
function renderGrid(locale: Locale = "fr", inflation?: EstimateGridProps["inflation"]) {
  server.client = fakeClient({});
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateGrid
        nodes={installation}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable={false}
        tasksEditable={false}
        query={{ sort: undefined, search: undefined, size: undefined }}
        filters={{}}
        preferences={undefined}
        inflation={inflation}
      />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the tooltip of the header of a column", () => {
  it("gives a column its definition of the catalogue [WF-IHM-0140-A]", async () => {
    renderGrid();
    const quantity = screen.getByRole("columnheader", { name: /Qté/ });
    await userEvent.hover(quantity);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      CATALOGUES.fr.columns.estimate.quantity.help,
    );
  });

  it("opens on the focus of the keyboard and speaks the language of the reader [WF-IHM-0140-A]", async () => {
    renderGrid("en");
    const header = screen.getByRole("columnheader", { name: /Amount \(reference year\)/ });
    header.focus();
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent(CATALOGUES.en.columns.estimate.referenceAmount.help);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(header).toHaveFocus();
  });

  it("names the year of reference and the rate of inflation on the header of the amount re-estimated, from the revision [WF-IHM-0140-A]", async () => {
    renderGrid("fr", { referenceYear: revision.reference_year, rate: revision.inflation_rate });
    const header = screen.getByRole("columnheader", { name: /Montant réestimé/ });
    await userEvent.hover(header);
    const tooltip = await screen.findByRole("tooltip");
    // The witness: reference year 2026, inflation of 3 %.
    expect(revision.reference_year).toBe(2026);
    expect(revision.inflation_rate).toBe("0.03");
    expect(tooltip).toHaveTextContent(/année de référence \(2026\)/);
    expect(tooltip).toHaveTextContent(/taux d’inflation de la révision \(3\s%/);
    expect(header).toHaveAccessibleDescription(/2026.*3\s%/);
  });

  it("speaks the language of the reader on that header, and names neither year nor rate when the revision is unknown [WF-IHM-0140-A]", async () => {
    const { unmount } = renderGrid("en", { referenceYear: 2027, rate: "0.025" });
    const header = screen.getByRole("columnheader", { name: /Re-estimated amount/ });
    header.focus();
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent(/reference year \(2027\)/);
    expect(tooltip).toHaveTextContent(/inflation rate of the revision \(2\.5% a year\)/);
    unmount();
    renderGrid("fr");
    const plain = screen.getByRole("columnheader", { name: /Montant réestimé/ });
    await userEvent.hover(plain);
    await waitFor(() => {
      expect(plain).toHaveAccessibleDescription(
        CATALOGUES.fr.columns.estimate.reestimatedAmountStatic.help,
      );
    });
    expect(plain).not.toHaveAccessibleDescription(/2026|3\s?%/);
  });
});
