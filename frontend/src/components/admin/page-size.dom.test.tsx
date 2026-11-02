// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, startTransition } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { keysOf } from "@/test/grid-preferences";

import { UserList } from "./account-lists";
import { type User, userGrid } from "./admin-grids";
import { authorsOf, readAuditFilters } from "./audit-address";
import { USER_KEPT } from "./user-address";

// The server of Next, as far as the page size needs it: the fake back, which keeps the settings of
// the grids, the address the table reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/users", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };

/** A list of a hundred and twenty accounts, of which the first page of `limit` is shown. */
function accounts(limit: number, kept?: GridPreferences, total = 120): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={users.items}
          page={{ limit, offset: 0, total }}
          query={{ sort: undefined, search: undefined, size: undefined }}
          preferences={kept}
          origins={[]}
          nodes={[]}
          orgNode={undefined}
          roles={[]}
          accessRoles={[]}
          active={undefined}
          audit={readAuditFilters(new URLSearchParams())}
          authors={authorsOf(users.items)}
          editable={false}
        />
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
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.path = "/admin/users";
  page.search = "";
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockReset();
});

describe("the number of rows per page of a flat table", () => {
  it("is offered beside the pagination, among 10, 25, 50 and 100, the size the server read chosen [WF-IHM-0060-A]", async () => {
    const { container } = render(accounts(25));
    const choice = screen.getByRole("combobox", { name: "Lignes par page" });
    expect(
      within(choice)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["10", "25", "50", "100"]);
    expect(choice).toHaveValue("25");
    expect(screen.getByRole("navigation", { name: "Pages de la liste" })).toBeInTheDocument();
    await expectAccessible(container);
  });

  it("is written in the address under the name of the contract, back to the first page, the rest of the query kept [WF-IHM-0060-A]", async () => {
    page.search = "origins=local&sort_by=email&offset=50";
    render(accounts(50));
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Lignes par page" }), "100");
    expect(router.push).toHaveBeenLastCalledWith(
      "/admin/users?origins=local&sort_by=email&limit=100",
      {
        scroll: false,
      },
    );
    // The links to the pages turn from the address asked, and carry the size chosen.
    page.search = "origins=local&limit=10";
    render(accounts(10));
    expect(screen.getAllByRole("link", { name: /Page suivante/ }).at(-1)).toHaveAttribute(
      "href",
      "/admin/users?origins=local&limit=10&offset=7",
    );
  });

  it("shows the size chosen while the server reads the list anew, and the size it answered once it has [WF-IHM-0060-A]", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    const { rerender } = render(accounts(50));
    const choice = screen.getByRole("combobox", { name: "Lignes par page" });
    await userEvent.selectOptions(choice, "100");
    expect(router.push).toHaveBeenCalledTimes(1);
    // The address has not changed yet: the choice shows, never the size before it.
    expect(choice).toHaveValue("100");
    page.search = "limit=100";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(accounts(100));
    expect(choice).toHaveValue("100");
  });

  it("is offered to a list that holds more rows than the smallest page, and to none other [WF-IHM-0060-A]", () => {
    const { unmount } = render(accounts(100, undefined, 60));
    expect(screen.getByRole("combobox", { name: "Lignes par page" })).toHaveValue("100");
    unmount();
    render(accounts(50, undefined, 8));
    expect(screen.queryByRole("combobox", { name: "Lignes par page" })).toBeNull();
  });

  it("is written to the settings of its grid alone once the page shows it, the others' kept [WF-IHM-0060-A]", async () => {
    page.search = "limit=25";
    render(accounts(25));
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toEqual({
      grids: {
        users: {
          hidden_columns: [],
          column_widths: {},
          known_columns: keysOf(userGrid().columns),
          filters: {},
          page_size: 25,
        },
      },
    });
  });

  it("is not written again when the settings hold it, nor when the address names none or a size no server takes [WF-IHM-0060-A]", async () => {
    const kept: GridPreferences = { hidden_columns: [], column_widths: {}, page_size: 25 };
    page.search = "limit=25";
    const { unmount } = render(accounts(25, kept));
    unmount();
    // An address that names none is read by the size the account keeps (`readGridQuery`).
    page.search = "";
    render(accounts(25, kept));
    page.search = "limit=7";
    render(accounts(50));
    await new Promise((done) => setTimeout(done, 50));
    expect(writes()).toEqual([]);
  });

  it("is written over the size kept when the address names another, and 50 is a size like any other [WF-IHM-0060-A]", async () => {
    page.search = "limit=50";
    render(accounts(50, { hidden_columns: [], column_widths: {}, page_size: 25 }));
    await waitFor(() => {
      expect(writes()).toHaveLength(1);
    });
    expect(writes()[0]?.body).toMatchObject({ grids: { users: { page_size: 50 } } });
  });
});
