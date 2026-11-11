// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { NO_AUDIT } from "@/test/accounts";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { UserList } from "./account-lists";
import type { User } from "./admin-grids";
import { authorsOf } from "./audit-address";
import { USER_KEPT } from "./user-address";

// Filters folded into the bar of the table of the accounts (#2916): the panel, closed by default
// and kept with the settings of the grid, and the chips of the filters on, built from the address.
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

const users = example("users") as {
  items: User[];
  meta: components["schemas"]["PaginationMeta"];
};

/** The accounts, filtered as the address says, with the preferences given. */
function list(preferences?: GridPreferences) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={users.items}
          page={users.meta}
          query={{ sort: undefined, search: undefined, size: undefined }}
          preferences={preferences}
          origins={page.search.includes("origins=local") ? ["local"] : []}
          nodes={[]}
          orgNode={undefined}
          roles={[]}
          accessRoles={[]}
          active={page.search.includes("is_active=true") ? true : undefined}
          audit={NO_AUDIT}
          authors={authorsOf(users.items)}
          editable={false}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

const lastAddress = (): unknown => router.push.mock.calls.at(-1)?.[0];
const toggle = () => screen.getByRole("button", { name: /^Filtres( \(|$)/ });

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  page.search = "";
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

/** The settings the grid recorded, by the calls of the fake back. */
function recorded(): (GridPreferences | undefined)[] {
  const client = server.client as FakeClient;
  return client.calls
    .filter((call) => call.route === "PATCH /me/preferences")
    .map((call) => {
      const body = call.body as { grids: Record<string, GridPreferences> };
      return body.grids.users;
    });
}

describe("the panel of the filters of the table of the accounts", () => {
  it("is closed by default, its button saying it and naming the panel it controls [WF-IHM-0060-A]", () => {
    render(list());
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: /^Filtrer par origine/ })).toBeNull();
    const panel = document.getElementById(toggle().getAttribute("aria-controls") ?? "");
    expect(panel).not.toBeNull();
    expect(panel).not.toBeVisible();
  });

  it("opens and closes, writes whether it is open with the settings of the grid, and opens as the account keeps it [WF-IHM-0060-A, #2916]", async () => {
    const { unmount } = render(list());
    await userEvent.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: /^Filtrer par origine/ })).toBeVisible();
    expect(recorded().at(-1)).toMatchObject({ filters_open: true });
    await userEvent.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(recorded().at(-1)).toMatchObject({ filters_open: false });
    unmount();
    render(list({ filters_open: true }));
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: /^Filtrer par origine/ })).toBeVisible();
  });

  it("tells the filters on as chips from the address, counted by the button, whether the panel is open or not [WF-IHM-0130-A]", () => {
    page.search = "origins=local&is_active=true";
    render(list());
    expect(toggle()).toHaveAccessibleName("Filtres (2)");
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(within(chips).getAllByRole("listitem")).toHaveLength(2);
    expect(within(chips).getByText("Origine : Créé dans Waterfall")).toBeVisible();
    expect(within(chips).getByText("État du compte : Comptes actifs")).toBeVisible();
  });

  it("lifts a filter by the cross of its chip, in the address, back to the first page [WF-IHM-0130-A]", async () => {
    page.search = "origins=local&is_active=true&offset=2";
    render(list());
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer le filtre Origine : Créé dans Waterfall" }),
    );
    expect(lastAddress()).toBe("/admin/users?is_active=true");
  });

  it("lifts every filter by « Effacer les filtres », the search kept as the field of the bar shows it [WF-IHM-0130-A]", async () => {
    page.search = "origins=local&is_active=true&search=Mor&offset=2";
    render(list());
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    expect(lastAddress()).toBe("/admin/users?search=Mor");
  });

  it("offers no chip, and no way to clear, while no filter is on, and breaks no rule of accessibility", async () => {
    const { container } = render(list());
    expect(screen.queryByRole("list", { name: "Filtres actifs" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Effacer les filtres" })).toBeNull();
    await userEvent.click(toggle());
    await expectAccessible(container);
  });
});
