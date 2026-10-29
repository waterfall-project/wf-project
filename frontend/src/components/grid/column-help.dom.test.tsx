// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
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

/** The grid of the estimate of the witness, in a language. */
function renderGrid(locale: Locale = "fr") {
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
});
