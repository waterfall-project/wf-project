// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { UserList } from "./account-lists";
import type { AccessRole, User } from "./admin-grids";
import { USER_KEPT } from "./user-address";

// The server of Next, as far as the screen needs it: the fake back, the address it reads and the
// navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/admin/users",
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };
const roles = (example("access_roles") as AccessRole[]).map((role) => ({
  id: role.access_role_id,
  label: role.label,
}));
const CHIFFREUR = "01926f3a-7c00-7000-8000-000000000705";
const DIRECTION = "01926f3a-7c00-7000-8000-000000000701";

/** Serve the fake back, which keeps the settings of the grid, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient({ "PATCH /me/preferences": "preferences", ...answers });
  server.client = client;
  return client;
}

/** The calls the screen made, but the settings of its grid. */
function writes(client: FakeClient) {
  return client.calls
    .filter(({ route }) => route !== "PATCH /me/preferences")
    .map(({ route, path, body }) => [route, path, body]);
}

/** The accounts of the witness, in French, as a session that may modify them, or not, reads them. */
function accounts(editable = true, shown: readonly User[] = users.items, kept?: GridPreferences) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={USER_KEPT}>
        <UserList
          users={shown}
          page={users.meta}
          query={{ sort: undefined, search: undefined }}
          preferences={kept}
          origins={[]}
          nodes={[]}
          orgNode={undefined}
          roles={roles}
          accessRoles={[]}
          active={undefined}
          editable={editable}
        />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the accounts. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Comptes utilisateurs" });
}

/** The region of the table that says what its last command did, by its name. */
function told(): HTMLElement {
  return screen.getByRole("status", { name: "Commandes des comptes" });
}

/** An account of the witness, by its last name. */
function account(lastName: string): User {
  const found = users.items.find((user) => user.last_name === lastName);
  if (found === undefined) {
    throw new Error(`no account ${lastName} in the witness`);
  }
  return found;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  serve({});
  page.search = "";
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  router.replace.mockClear();
  refresh.mockReset();
});

describe("the table of the accounts, its own entry", () => {
  it("offers to delete no account [WF-ADM-0060-A]; to a session that may modify them, a switch of the state and the roles on each row, and breaks no rule of accessibility", async () => {
    const { container } = render(accounts());
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
    expect(screen.queryByText(/Supprimer/)).toBeNull();
    expect(within(grid()).getAllByRole("switch")).toHaveLength(7);
    expect(
      within(grid()).getByRole("switch", { name: "Compte de « Alix Moreau » actif" }),
    ).not.toBeChecked();
    expect(within(grid()).getAllByRole("button", { name: /^Rôles de «/ })).toHaveLength(7);
    await expectAccessible(container);
  });

  it("offers nothing to write to a session that may not modify the accounts: the state and the roles read only", () => {
    render(accounts(false));
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.queryByRole("button", { name: /^Rôles de/ })).toBeNull();
    expect(screen.queryByRole("status", { name: "Commandes des comptes" })).toBeNull();
  });

  it("renames a local account in its cell from the version read, its name shown as the server answers it; the name of an account of the directory is not entered [WF-ADM-0050-A]", async () => {
    const client = serve({ "PATCH /users/{user_id}": "user_renamed" });
    render(accounts());
    const petit = within(grid()).getByText("Petit").closest<HTMLElement>("[tabindex]");
    petit?.focus();
    await userEvent.keyboard("Petit-Laurent{Enter}");
    expect(await within(grid()).findByText("Petit-Laurent")).toBeInTheDocument();
    const lucas = account("Petit");
    expect(writes(client)).toEqual([
      [
        "PATCH /users/{user_id}",
        `/users/${lucas.user_id}`,
        { last_name: "Petit-Laurent", lock_version: lucas.lock_version },
      ],
    ]);
    // Dominique Bernard comes from the directory, which holds her names.
    const bernard = within(grid()).getByText("Bernard").closest<HTMLElement>("[tabindex]");
    bernard?.focus();
    await userEvent.keyboard("Durand{Enter}");
    expect(writes(client)).toHaveLength(1);
  });
});

describe("the state of an account, on its switch", () => {
  it("deactivates an account from the version read, says so and reads the page anew; it stays listed [WF-ADM-0060-A]", async () => {
    const client = serve({ "PUT /users/{user_id}/activation": "user_deactivated" });
    render(accounts());
    const vidal = within(grid()).getByRole("switch", {
      name: "Compte de « Noé Vidal » actif",
    });
    expect(vidal).toBeChecked();
    await userEvent.click(vidal);
    await waitFor(() => {
      expect(told().textContent).toBe("« Noé Vidal » désactivé.");
    });
    expect(vidal).not.toBeChecked();
    expect(vidal.closest("td")).toHaveTextContent("Désactivé");
    const noe = account("Vidal");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/activation",
        `/users/${noe.user_id}/activation`,
        { is_active: false, lock_version: noe.lock_version },
      ],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("presents the deactivation of the last administrator unavailable, naming the condition she lacks, and asks nothing when pressed [WF-ADM-0120-A]", async () => {
    const client = serve({});
    render(accounts());
    const camille = within(grid()).getByRole("switch", {
      name: "Compte de « Camille Martin » actif",
    });
    const unmet =
      "Condition non remplie : un autre compte actif portant les permissions d’administration.";
    expect(camille).toHaveAttribute("aria-disabled", "true");
    expect(camille).toHaveAccessibleDescription(unmet);
    await userEvent.click(camille);
    expect(camille).toBeChecked();
    expect(screen.getAllByRole("status").map((region) => region.textContent)).toContain(
      `La désactivation de «\u00a0Camille Martin\u00a0» est indisponible. ${unmet}`,
    );
    expect(writes(client)).toEqual([]);
  });

  it("tells a deactivation the server refuses, the account changed since it was read, the switch showing it as it was", async () => {
    serve({
      "PUT /users/{user_id}/activation": { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
    });
    render(accounts());
    const roux = within(grid()).getByRole("switch", {
      name: "Compte de «\u00a0Inès Roux\u00a0» actif",
    });
    await userEvent.click(roux);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Recharger/);
    expect(roux).toBeChecked();
    expect(told().textContent).toBe("");
  });
});

describe("the access roles of an account, cell by cell", () => {
  it("attributes a role of the installation to an account that holds none, from the version read, and says so (WF-ADM-0050, WF-ADM-0090)", async () => {
    const client = serve({ "PUT /users/{user_id}/access-roles": "user_access_roles_set" });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("button", { name: "Rôles de « Sacha Lefèvre »" }),
    );
    const list = await screen.findByRole("group", { name: "Rôles de « Sacha Lefèvre »" });
    // Every role of the installation, whatever the node of the account (WF-ADM-0030).
    expect(within(list).getAllByRole("checkbox")).toHaveLength(roles.length);
    expect(within(list).getByRole("checkbox", { name: "Chiffreur" })).not.toBeChecked();
    await userEvent.click(within(list).getByRole("checkbox", { name: "Chiffreur" }));
    await waitFor(() => {
      expect(told().textContent).toBe("Rôles de « Sacha Lefèvre » attribués.");
    });
    expect(within(list).getByRole("checkbox", { name: "Chiffreur" })).toBeChecked();
    const sacha = account("Lefèvre");
    expect(writes(client)).toEqual([
      [
        "PUT /users/{user_id}/access-roles",
        `/users/${sacha.user_id}/access-roles`,
        { access_role_ids: [CHIFFREUR], lock_version: sacha.lock_version },
      ],
    ]);
  });

  it("refuses by the catalogue the withdrawal of her role from the last administrator, her role still checked [WF-ADM-0120-A]", async () => {
    serve({
      "PUT /users/{user_id}/access-roles": {
        problem: example("user_access_roles_refused") as Problem & { status: 409 },
      },
    });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("button", { name: "Rôles de « Camille Martin »" }),
    );
    const list = await screen.findByRole("group", {
      name: "Rôles de « Camille Martin »",
    });
    const direction = roles.find((role) => role.id === DIRECTION)?.label ?? "";
    await userEvent.click(within(list).getByRole("checkbox", { name: direction }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Au moins un compte actif doit garder les permissions d’administration.",
    );
    expect(within(list).getByRole("checkbox", { name: direction })).toBeChecked();
  });

  it("writes the roles of an account deactivated before the page is read anew from the version the deactivation answered", async () => {
    const client = serve({
      "PUT /users/{user_id}/activation": "user_deactivated",
      "PUT /users/{user_id}/access-roles": {
        problem: { code: "STALE_LOCK_VERSION", status: 412 },
      },
    });
    render(accounts());
    await userEvent.click(
      within(grid()).getByRole("switch", { name: "Compte de « Noé Vidal » actif" }),
    );
    await waitFor(() => {
      expect(told().textContent).toBe("« Noé Vidal » désactivé.");
    });
    await userEvent.click(within(grid()).getByRole("button", { name: "Rôles de « Noé Vidal »" }));
    const list = await screen.findByRole("group", { name: "Rôles de « Noé Vidal »" });
    await userEvent.click(within(list).getByRole("checkbox", { name: "Chiffreur" }));
    await waitFor(() => {
      expect(writes(client)).toHaveLength(2);
    });
    const deactivated = example("user_deactivated") as User;
    expect(writes(client)[1]?.[2]).toEqual({
      access_role_ids: [...deactivated.access_role_ids, CHIFFREUR],
      lock_version: deactivated.lock_version,
    });
  });

  it("opens the roles of the active cell on Enter, the grid one stop of the tabulation, and gives the focus back to the cell on Escape", async () => {
    render(accounts());
    const trigger = within(grid()).getByRole("button", {
      name: "Rôles de « Lucas Petit »",
    });
    expect(trigger).toHaveAttribute("tabindex", "-1");
    const cell = trigger.closest("td") as HTMLElement;
    cell.focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByRole("group", { name: "Rôles de « Lucas Petit »" }),
    ).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(cell).toHaveFocus();
    });
  });
});

describe("the filters of the table", () => {
  it("are kept with the settings of the grid, as the page shows them [WF-IHM-0060-A]", async () => {
    page.search = "search=Mor&origins=local&is_active=false&offset=2";
    render(accounts(false, users.items, { hidden_columns: [], column_widths: {} }));
    const client = server.client as FakeClient;
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual(["PATCH /me/preferences"]);
    });
    expect(client.calls[0]?.body).toEqual({
      grids: {
        users: {
          hidden_columns: [],
          column_widths: {},
          filters: { search: "Mor", origins: "local", is_active: "false" },
        },
      },
    });
  });
});
