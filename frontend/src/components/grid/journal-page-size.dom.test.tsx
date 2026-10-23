// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { COST_IMPORT_GRID_KEY } from "@/components/costs/address";
import { type CostImport, ImportJournal } from "@/components/costs/import-journal";
import { ImportList } from "@/components/exchanges/import-list";
import { IMPORT_GRID_KEY } from "@/components/exchanges/offers";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { KeptListSize } from "./kept-list-size";
import { ListPages } from "./list-pages";
import { PendingAddress } from "./pending-address";
import { CONTRACT_ADDRESS } from "./query";
import type { GridPreferences } from "./settings";

// The server of Next, as far as the journals need it: the fake back, which keeps the settings of the
// grids, the address the journal reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/screen", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const journal = example("cost_imports") as { items: CostImport[] };
const listed = example("imports") as { items: React.ComponentProps<typeof ImportList>["imports"] };

/** The journal of the imports of actual costs, a hundred and twenty entries held. */
function costJournal(limit: number, kept?: GridPreferences) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ImportJournal
          imports={journal.items}
          page={{ limit, offset: 0, total: 120 }}
          preferences={kept}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The imports of a project, with the way through their pages, a hundred and twenty held. */
function projectImports(limit: number, kept?: GridPreferences) {
  const meta = { limit, offset: 0, total: 120 };
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ImportList imports={listed.items} total={120} current={undefined} start="/screen">
          <ListPages
            list={{ page: "offset", size: "limit", reads: ["limit"] }}
            texts="actualCosts.pages.exchanges"
            page={meta}
            shown={listed.items.length}
          />
          <KeptListSize gridKey={IMPORT_GRID_KEY} address={CONTRACT_ADDRESS} preferences={kept} />
        </ImportList>
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The calls the settings of the grids were written by. */
function writes(): FakeClient["calls"] {
  return (server.client as FakeClient).calls.filter(
    ({ route }) => route === "PATCH /me/preferences",
  );
}

beforeEach(() => {
  page.search = "";
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  router.push.mockReset();
});

describe("the number of rows per page of the journal of the imports of actual costs", () => {
  it("is offered beside its pages, named after the journal, and written in the address under its own name, back to its first page [WF-IHM-0060-A]", async () => {
    page.search = "offset=50&imports_offset=50";
    const { container } = render(costJournal(50));
    const choice = screen.getByRole("combobox", {
      name: "Lignes par page de «\u00a0Journal des imports\u00a0»",
    });
    expect(choice).toHaveValue("50");
    await expectAccessible(container);
    await userEvent.selectOptions(choice, "25");
    expect(router.push).toHaveBeenLastCalledWith("/screen?offset=50&imports_limit=25", {
      scroll: false,
    });
  });

  it("is recorded under the key of the journal once the address shows it, the rest of what the account kept sent back as it came [WF-IHM-0060-A]", async () => {
    page.search = "imports_limit=25";
    const kept: GridPreferences = { hidden_columns: ["x"], page_size: 50 };
    render(costJournal(25, kept));
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({
      grids: { [COST_IMPORT_GRID_KEY]: { hidden_columns: ["x"], page_size: 25 } },
    });
  });

  it("records nothing when the size shown is the one kept, or the address names none [WF-IHM-0060-A]", async () => {
    page.search = "imports_limit=25";
    const { unmount } = render(costJournal(25, { page_size: 25 }));
    unmount();
    page.search = "";
    render(costJournal(50));
    await new Promise((settle) => setTimeout(settle, 50));
    expect(writes()).toEqual([]);
  });
});

describe("the number of rows per page of the imports of a project", () => {
  it("is offered beside the pages, written in the address as `limit`, and kept apart from the other journal's [WF-IHM-0060-A]", async () => {
    render(projectImports(50));
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Lignes par page" }), "100");
    expect(router.push).toHaveBeenLastCalledWith("/screen?limit=100", { scroll: false });
  });

  it("is recorded under the key of the imports once the address shows it [WF-IHM-0060-A]", async () => {
    page.search = "limit=10";
    render(projectImports(10));
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({ grids: { [IMPORT_GRID_KEY]: { page_size: 10 } } });
  });
});
