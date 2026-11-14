// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import {
  account,
  accounts,
  grid,
  heldActivation,
  holdRoute,
  told,
  users,
  writes,
} from "@/test/accounts";
import { expectAccessible } from "@/test/axe";
import { type FakeAnswers, type FakeTiming, fakeClient } from "@/test/fixtures";

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
function serve(answers: FakeAnswers, timing?: FakeTiming) {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers }, timing);
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

/** Choose in a list of the bar, and press its button: the choice alone writes nothing. */
async function apply(bar: HTMLElement, list: string, option: string) {
  await userEvent.selectOptions(within(bar).getByRole("combobox", { name: list }), option);
  await userEvent.click(within(bar).getByRole("button", { name: `Appliquer : ${list}` }));
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
    await apply(bar, "Ajouter un rôle", "Chiffreur");
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

  it("adds the role to those the account holds, never in their place; one that holds it is written all the same, the server deciding [WF-ADM-0180-A] #2917", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts(true, [account("Bernard"), account("Petit")]));
    const bar = await selectAll();
    await apply(bar, "Ajouter un rôle", "Chiffreur");
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    // Bernard keeps his role and gets the other after it; Petit, who holds it, is sent as he is:
    // the screen may be stale, and a 412 would tell it.
    const bernard = account("Bernard");
    const petit = account("Petit");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${bernard.user_id}/access-roles`,
        {
          access_role_ids: [...bernard.access_role_ids, CHIFFREUR],
          lock_version: bernard.lock_version,
        },
      ],
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${petit.user_id}/access-roles`,
        { access_role_ids: petit.access_role_ids, lock_version: petit.lock_version },
      ],
    ]);
  });

  it("writes nothing while a list is walked with the keyboard, and each account when its button is pressed [WF-ADM-0180-A] #2917", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts(true, [account("Bernard"), account("Petit")]));
    const bar = await selectAll();
    const list = within(bar).getByRole("combobox", { name: "Ajouter un rôle" });
    list.focus();
    // Chrome and Edge fire `change` at each arrow key on a closed list.
    await userEvent.keyboard("{ArrowDown}{ArrowDown}");
    expect(writes(client)).toEqual([]);
    expect(
      within(bar).getByRole("button", { name: "Appliquer : Ajouter un rôle" }),
    ).toHaveAttribute("aria-disabled", "true");
    await userEvent.selectOptions(list, "Chiffreur");
    expect(writes(client)).toEqual([]);
    await userEvent.click(within(bar).getByRole("button", { name: "Appliquer : Ajouter un rôle" }));
    await waitFor(() => {
      expect(writes(client)).toHaveLength(2);
    });
  });

  it("attaches each account selected to a node, and activates each, written whatever the screen shows [WF-ADM-0050-A] #2917", async () => {
    const client = serve({
      "PATCH /users/{user_id}": "user_renamed",
      "PUT /users/{user_id}/activation": "user_reactivated",
    });
    const node = "01926f3a-7c00-7000-8000-000000000471";
    render(
      accounts(true, [account("Moreau"), account("Roux")], undefined, [
        { id: node, code: "ACH", label: "Service des achats", level: 0 },
      ]),
    );
    const bar = await selectAll();
    await apply(bar, "Rattacher à", node);
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    expect(writes(client).map(([route, path]) => [route, path])).toEqual(
      ["Moreau", "Roux"].map((name) => [
        "PATCH /users/{user_id}",
        `/users/${account(name).user_id}`,
      ]),
    );
    await userEvent.click(within(bar).getByRole("button", { name: "Activer" }));
    await waitFor(() => {
      expect(writes(client)).toHaveLength(4);
    });
    // Roux, shown active, is written too: only the server knows whether it still is.
    expect(writes(client)[3]).toEqual([
      "PUT /users/{user_id}/activation",
      `/users/${account("Roux").user_id}/activation`,
      { is_active: true, lock_version: account("Roux").lock_version },
    ]);
  });

  it("goes on after a refusal, keeps the accounts done, and tells each refused with its reason: a 412, the last administrator [WF-ADM-0120-A] #2917", async () => {
    // Held at version 1, each is answered at another version (2, then 5): each is modified.
    const active = users.items
      .filter((user) => user.is_active)
      .map((user) => ({ ...user, lock_version: 1 }));
    expect(active).toHaveLength(6);
    // One answer for each account, in the order of the table.
    const client = serve({
      "PUT /users/{user_id}/activation": [
        "user_deactivated",
        { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
        { problem: { code: "LAST_ADMINISTRATOR", status: 409 } },
        { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
        { problem: { code: "LAST_ADMINISTRATOR", status: 409 } },
        // At version 5: the answers record the account they carry, and one may be written again.
        "user_reactivated",
      ],
    });
    render(accounts(true, active));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toBe(
        "2 comptes modifiés, 4 comptes refusés : la raison de chacun est dite ci-dessus.",
      );
    });
    // One call for each account, in the order of the table, none stopping the others.
    expect(writes(client).map(([route, path]) => [route, path])).toEqual(
      active.map((user) => [
        "PUT /users/{user_id}/activation",
        `/users/${user.user_id}/activation`,
      ]),
    );
    const stale = "refaites la modification si elle vaut encore.";
    const last = "Au moins un compte actif doit garder les permissions d’administration.";
    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(4);
    [
      [1, stale],
      [2, last],
      [3, stale],
      [4, last],
    ].forEach(([index, text], position) => {
      expect(alerts[position]).toHaveTextContent(active[Number(index)]?.last_name ?? "");
      expect(alerts[position]).toHaveTextContent(String(text));
    });
  });

  it("reads the account refused by a 412 anew, and a second try goes from the version read [WF-ADM-0120-A] [WF-IHM-0110-A] #3078", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": [
        "user_reactivated",
        { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
        "user_reactivated",
      ],
      "GET /users/{user_id}": "user_deactivated",
    });
    const bernard = account("Bernard");
    render(accounts(true, [bernard, account("Vidal")]));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toContain("1 compte refusé");
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "refaites la modification si elle vaut encore.",
    );
    // Only the account refused is read anew, and its row shows what the server holds.
    expect(client.calls.filter(({ route }) => route === "GET /users/{user_id}")).toHaveLength(1);
    await waitFor(() => {
      expect(
        within(grid()).getByRole("switch", { name: "Compte de «\u00a0Noé Vidal\u00a0» actif" }),
      ).not.toBeChecked();
    });
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    const puts = () =>
      writes(client).filter(([route]) => route === "PUT /users/{user_id}/activation");
    await waitFor(() => {
      expect(puts()).toHaveLength(4);
    });
    // The group is sent anew: Bernard from his version, Vidal from the one read.
    expect(puts()[2]?.[2]).toEqual({ is_active: false, lock_version: bernard.lock_version });
    expect(puts()[3]?.[2]).toEqual({ is_active: false, lock_version: 2 });
  });

  it("tells the refusal alone when the account refused cannot be read anew, and a second try goes from the version first held [WF-ADM-0120-A] #3078", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
      "GET /users/{user_id}": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    const vidal = account("Vidal");
    render(accounts(true, [vidal]));
    const bar = await selectAll();
    const name = "Compte de «\u00a0Noé Vidal\u00a0» actif";
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toContain("1 compte refusé");
    });
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(screen.getByRole("alert")).not.toHaveTextContent("dernière version");
    // The row stays as it was: still active.
    expect(within(grid()).getByRole("switch", { name })).toBeChecked();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    const puts = () =>
      writes(client).filter(([route]) => route === "PUT /users/{user_id}/activation");
    await waitFor(() => {
      expect(puts()).toHaveLength(2);
    });
    expect(puts()[1]?.[2]).toEqual({ is_active: false, lock_version: vidal.lock_version });
  });

  it("writes one group at a time: a second press while the first is under way sends nothing [WF-ADM-0120-A] #2917", async () => {
    const held = heldActivation();
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" }, held.timing);
    render(accounts(true, [account("Bernard"), account("Petit")]));
    const bar = await selectAll();
    const press = within(bar).getByRole("button", { name: "Désactiver" });
    await userEvent.click(press);
    await waitFor(() => {
      expect(press).toHaveAttribute("aria-busy", "true");
    });
    await userEvent.click(press);
    await userEvent.click(press);
    held.release();
    await waitFor(() => {
      expect(told().textContent).toBe("2 comptes modifiés.");
    });
    expect(writes(client)).toHaveLength(2);
  });

  it("tells no refusal, nor the summary that points at them, of a group answered after the list is read otherwise [WF-ADM-0120-A] #2917", async () => {
    const held = heldActivation();
    serve(
      {
        "PUT /users/{user_id}/activation": { problem: { code: "LAST_ADMINISTRATOR", status: 409 } },
      },
      held.timing,
    );
    const shown = [account("Bernard"), account("Petit")];
    const { rerender } = render(accounts(true, shown));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(within(bar).getByRole("button", { name: "Désactiver" })).toHaveAttribute(
        "aria-busy",
        "true",
      );
    });
    // The list is read otherwise while the group is under way.
    page.search = "sort_by=email";
    rerender(accounts(true, shown));
    held.release();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Désactiver" })).not.toHaveAttribute(
        "aria-disabled",
      );
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(told().textContent).toBe("");
  });

  it("counts as modified only the accounts the server answers at another version; one answered at the same is already in the state asked [WF-ADM-0120-A] #3082", async () => {
    // « user_deactivated » answers at lock_version 2: Petit, held at 2, is written nothing.
    const petit = { ...account("Petit"), lock_version: 2 };
    serve({ "PUT /users/{user_id}/activation": "user_deactivated" });
    render(accounts(true, [account("Bernard"), petit]));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toBe("1 compte modifié, 1 compte déjà dans l’état demandé.");
    });
  });

  it("tells the accounts already in the state asked in the summary with refusals, and none modified when none was [WF-ADM-0120-A] #3082", async () => {
    const same = [
      { ...account("Bernard"), lock_version: 2 },
      { ...account("Petit"), lock_version: 2 },
    ];
    serve({
      "PUT /users/{user_id}/activation": [
        "user_deactivated",
        { problem: { code: "LAST_ADMINISTRATOR", status: 409 } },
      ],
    });
    render(accounts(true, same));
    const bar = await selectAll();
    await userEvent.click(within(bar).getByRole("button", { name: "Désactiver" }));
    await waitFor(() => {
      expect(told().textContent).toBe(
        "Aucun compte modifié, 1 compte déjà dans l’état demandé, 1 compte refusé : la raison de chacun est dite ci-dessus.",
      );
    });
  });

  it("keeps the choice shown while its group is under way, and clears it at the end [WF-ADM-0180-A] #3083", async () => {
    const held = holdRoute("PUT /users/{user_id}/access-roles");
    serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" }, held.timing);
    render(accounts(true, [account("Bernard"), account("Petit")]));
    const bar = await selectAll();
    const list = within(bar).getByRole("combobox", { name: "Ajouter un rôle" });
    await apply(bar, "Ajouter un rôle", "Chiffreur");
    await waitFor(() => {
      expect(list).toHaveAttribute("aria-busy", "true");
    });
    expect(list).toHaveValue(CHIFFREUR);
    // The choice stays shown while the group is under way (the request is held); it is cleared
    // only when the group has ended, which the release below brings about.
    held.release();
    await waitFor(() => {
      expect(list).toHaveValue("");
    });
  });

  it("says an unavailable button by its attribute and its look, not by the attribute alone [WF-IHM-0110-A] #3081", async () => {
    render(accounts());
    const bar = await selectAll();
    const unavailable = within(bar).getByRole("button", { name: "Appliquer : Ajouter un rôle" });
    expect(unavailable).toHaveAttribute("aria-disabled", "true");
    expect(unavailable).toHaveClass("aria-disabled:cursor-not-allowed", "aria-disabled:opacity-50");
    expect(within(bar).getByRole("button", { name: "Désactiver" })).toHaveClass(
      "aria-disabled:cursor-not-allowed",
      "aria-disabled:opacity-50",
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
