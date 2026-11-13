// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { account, accounts, grid, told, users, writes } from "@/test/accounts";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import type { User } from "./admin-grids";

// The actions of the bar on the accounts selected (#2917, US-1860/L3): one call for each account,
// one after the other, with no atomicity, and the accounts refused told with their reason.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const CHIFFREUR = "01926f3a-7c00-7000-8000-000000000705";

/** Serve the fake back, which keeps the settings of the grid. */
function serve(answers: FakeAnswers) {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers });
  server.client = client;
  return client;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  serve({});
  page.search = "";
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockReset();
});

/** Select every row shown, and give the bar. */
async function selectAll(): Promise<HTMLElement> {
  await userEvent.click(
    within(grid()).getByRole("checkbox", { name: "Sélectionner toutes les lignes affichées" }),
  );
  return screen.getByRole("group", { name: "Actions sur la sélection" });
}

/** An account of the identity provider that holds no role, as the filters of the screen retain. */
function arrivals(): User[] {
  const first = account("Lefèvre");
  return [
    first,
    {
      ...first,
      user_id: "01926f3a-7c00-7000-8000-0000000007f1",
      first_name: "Jo",
      last_name: "Neuf",
    },
  ];
}

describe("the actions of the bar on the accounts selected", () => {
  it("gives a role to each account the filters of the screen retained: the welcome of those who arrive without a role [WF-ADM-0180-A] #2917", async () => {
    // « Créé par le fournisseur d'identité » + « Sans rôle » retain these two accounts.
    const arrived = arrivals();
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts(true, arrived));
    const bar = await selectAll();
    expect(bar).toHaveTextContent("2 comptes sélectionnés");
    await userEvent.selectOptions(
      within(bar).getByRole("combobox", { name: "Ajouter un rôle" }),
      "Chiffreur",
    );
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    expect(writes(client)).toEqual(
      arrived.map((user) => [
        "PUT /users/{user_id}/access-roles",
        `/users/${user.user_id}/access-roles`,
        { access_role_ids: [CHIFFREUR], lock_version: user.lock_version },
      ]),
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("adds the role to those the account holds, never in their place, and writes none for an account that holds it [WF-ADM-0180-A] #2917", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts(true, [account("Bernard"), account("Petit")]));
    const bar = await selectAll();
    await userEvent.selectOptions(
      within(bar).getByRole("combobox", { name: "Ajouter un rôle" }),
      "Chiffreur",
    );
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    // Petit holds it already; Bernard keeps his role, and gets the other after it.
    const bernard = account("Bernard");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${bernard.user_id}/access-roles`,
        {
          access_role_ids: [...bernard.access_role_ids, CHIFFREUR],
          lock_version: bernard.lock_version,
        },
      ],
    ]);
  });

  it("attaches each account selected to a node, and activates those that are not [WF-ADM-0050-A] #2917", async () => {
    const client = serve({
      "PATCH /users/{user_id}": "user_renamed",
      "PUT /users/{user_id}/activation": "user_deactivated",
    });
    const node = "01926f3a-7c00-7000-8000-000000000471";
    render(
      accounts(true, [account("Moreau"), account("Roux")], undefined, [
        { id: node, code: "ACH", label: "Service des achats", level: 0 },
      ]),
    );
    const bar = await selectAll();
    await userEvent.selectOptions(within(bar).getByRole("combobox", { name: "Rattacher à" }), node);
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    expect(writes(client).map(([route, path]) => [route, path])).toEqual([
      ["PATCH /users/{user_id}", `/users/${account("Roux").user_id}`],
    ]);
    await userEvent.click(within(bar).getByRole("button", { name: "Activer" }));
    await waitFor(() => {
      expect(writes(client)).toHaveLength(2);
    });
    expect(writes(client)[1]).toEqual([
      "PUT /users/{user_id}/activation",
      `/users/${account("Moreau").user_id}/activation`,
      { is_active: true, lock_version: account("Moreau").lock_version },
    ]);
  });

  it("goes on after a refusal, keeps the accounts done, and tells each refused with its reason: a 412, the last administrator [WF-ADM-0120-A] #2917", async () => {
    const active = users.items.filter((user) => user.is_active);
    const client = serve({
      "PUT /users/{user_id}/activation": [
        "user_deactivated",
        { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
        { problem: { code: "LAST_ADMINISTRATOR", status: 409 } },
      ],
    });
    render(accounts(true, active));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toMatch(/2 comptes modifiés, 4 comptes refusés/);
    });
    // One call for each account, in the order of the table, none stopping the others — but the
    // last, whose answer of the first call already says it deactivated: nothing is written for it.
    expect(writes(client).map(([route]) => route)).toEqual(
      active.slice(0, -1).map(() => "PUT /users/{user_id}/activation"),
    );
    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(4);
    expect(alerts[0]).toHaveTextContent(active[1]?.last_name ?? "");
    expect(alerts[0]).toHaveTextContent("Quelqu’un a modifié cette donnée entre-temps");
    expect(alerts[1]).toHaveTextContent(
      "Au moins un compte actif doit garder les permissions d’administration.",
    );
  });

  it("offers no action on a selection to a session that may not modify the accounts #2917", async () => {
    render(accounts(false));
    const bar = await selectAll();
    expect(within(bar).queryByRole("combobox")).toBeNull();
    expect(within(bar).queryByRole("button", { name: "Désactiver" })).toBeNull();
  });

  it("breaks no rule of accessibility with its bar open #2917", async () => {
    const { container } = render(accounts());
    await selectAll();
    await expectAccessible(container);
  });
});
