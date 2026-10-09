// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { ColumnLabel } from "@/components/grid/columns";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { refusedBounds } from "@/components/grid/filters";
import { example, fakeClient, type Problem } from "@/test/fixtures";

import { AccessRoleList, type RoleFilters, UserList } from "./account-lists";
import { CreateCommand, LaterCommands } from "./later-commands";
import {
  ACCESS_ROLE_SORTS,
  type AccessRole,
  type AccessRoleSort,
  accessRoleGrid,
  USER_SORTS,
  type User,
  type UserSort,
  userGrid,
} from "./admin-grids";

// The server of Next, as far as the screen needs it: the fake back, which keeps the settings of
// the grids a sort writes, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/users", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

const NO_QUERY = { sort: undefined, search: undefined };
const users = example("users") as { items: User[]; meta: Schemas["PaginationMeta"] };
const second = example("users_page") as { items: User[]; meta: Schemas["PaginationMeta"] };
const roles = example("access_roles") as AccessRole[];
const roleChoices = roles.map((role) => ({ id: role.access_role_id, label: role.label }));
const nodes = (example("org_nodes") as Schemas["OrgNode"][]).map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
}));

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The list of the accounts, a page of it, as the address asks it. */
function userList(
  query: GridQuery<UserSort> = NO_QUERY,
  shown: { items: User[]; meta: Schemas["PaginationMeta"] } = users,
  filters: {
    origins?: readonly Schemas["UserOrigin"][];
    orgNode?: string;
    accessRoles?: readonly string[];
    active?: boolean;
    editable?: boolean;
  } = {},
) {
  return inFrench(
    <LaterCommands>
      <UserList
        users={shown.items}
        page={shown.meta}
        query={query}
        preferences={undefined}
        origins={filters.origins ?? []}
        nodes={nodes}
        orgNode={filters.orgNode}
        roles={roleChoices}
        accessRoles={filters.accessRoles ?? []}
        active={filters.active}
        editable={filters.editable ?? false}
      />
    </LaterCommands>,
  );
}

/** No filter of the access roles. */
const NO_ROLE_FILTER: RoleFilters = {
  predefined: undefined,
  holders: { min: undefined, max: undefined },
};

/** The list of the access roles, as the address asks it. */
function roleList(
  editable: boolean,
  query: GridQuery<AccessRoleSort> = NO_QUERY,
  filters: RoleFilters = NO_ROLE_FILTER,
  shown: readonly AccessRole[] = roles,
) {
  return inFrench(
    <AccessRoleList
      roles={shown}
      query={query}
      preferences={undefined}
      filters={filters}
      editable={editable}
    />,
  );
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

/** The heading of the column of a grid that shows a column of the contract. */
function headingOf(
  columns: readonly { readonly contract?: string; readonly label: ColumnLabel }[],
  sort: string,
): string {
  const label = columns.find((column) => column.contract === sort)?.label;
  return label === undefined ? "" : CATALOGUES.fr.grid.columns[label];
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  page.path = "/admin/users";
  page.search = "";
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

describe("the grid of the accounts", () => {
  it("presents each account with its origin, its roles and its node as the server names them, and says in its totals how many the server retained", () => {
    render(userList());
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    expect(within(grid).getByRole("row", { name: /^Moreau/ }).textContent).toBe(
      "MoreauAlixalix.moreau@example.comCréé dans WaterfallChef de projetBureau d'études électricitéDésactivé",
    );
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("7 comptes");
    // The header of every column is grey, as that of every table (#508).
    expect(grid.querySelector("thead th")?.className).toContain("bg-muted");
  });

  it.each(USER_SORTS)(
    "asks the server for the sort by %s, both ways, back to the first page [WF-IHM-0060-A]",
    async (column) => {
      page.search = "offset=2";
      const { rerender } = render(userList(NO_QUERY, second));
      const heading = headingOf(userGrid(false).columns, column);
      const header = () =>
        within(screen.getByRole("grid", { name: "Comptes utilisateurs" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/admin/users?sort_by=${column}&sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      page.search = ascending.split("?")[1] ?? "";
      rerender(userList({ sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(`/admin/users?sort_by=${column}&sort_order=desc`);
    },
  );

  it("is searched by the server, back to the first page, its filters kept", async () => {
    page.search = "origins=local&offset=2";
    render(userList(NO_QUERY, second, { origins: ["local"] }));
    // Named after its grid: the contract does not say the search reads labels.
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Rechercher dans «\u00a0Comptes utilisateurs\u00a0»" }),
      "Mor",
    );
    await userEvent.keyboard("{Enter}");
    expect(lastAddress()).toBe("/admin/users?origins=local&search=Mor");
  });

  it("is filtered by origin under the name of the contract, the values in its order, back to the first page", async () => {
    page.search = "sort_by=email&sort_order=desc&offset=2";
    const { rerender } = render(userList(NO_QUERY, second));
    const filter = screen.getByRole("group", { name: "Filtrer par origine" });
    expect(within(filter).getByRole("button", { name: "Toutes les origines" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(filter).getByRole("button", { name: "Importé de l’annuaire" }));
    expect(lastAddress()).toBe("/admin/users?sort_by=email&sort_order=desc&origins=directory");
    // The page answers; a second origin chosen keeps the first, written in the order of the
    // contract.
    page.search = "sort_by=email&sort_order=desc&origins=directory";
    rerender(userList(NO_QUERY, users, { origins: ["directory"] }));
    expect(within(filter).getByRole("button", { name: "Importé de l’annuaire" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(filter).getByRole("button", { name: "Créé dans Waterfall" }));
    expect(lastAddress()).toBe(
      "/admin/users?sort_by=email&sort_order=desc&origins=local%2Cdirectory",
    );
    await userEvent.click(within(filter).getByRole("button", { name: "Toutes les origines" }));
    expect(lastAddress()).toBe("/admin/users?sort_by=email&sort_order=desc");
  });

  it("is filtered by access role under the name of the contract, choosing every role still filtering, back to the first page [WF-IHM-0130-A]", async () => {
    page.search = "offset=2";
    const { rerender } = render(userList(NO_QUERY, second));
    const filter = screen.getByRole("group", { name: "Filtrer par rôle" });
    const first = roleChoices[0] ?? { id: "", label: "" };
    await userEvent.click(within(filter).getByRole("button", { name: first.label }));
    expect(lastAddress()).toBe(`/admin/users?access_role_ids=${first.id}`);
    // Every role chosen still filters: an account without a role is retained by none.
    const every = roleChoices.map((role) => role.id);
    page.search = `access_role_ids=${every.slice(0, -1).join("%2C")}`;
    rerender(userList(NO_QUERY, users, { accessRoles: every.slice(0, -1) }));
    const last = roleChoices.at(-1) ?? first;
    await userEvent.click(within(filter).getByRole("button", { name: last.label }));
    expect(lastAddress()).toBe(`/admin/users?access_role_ids=${every.join("%2C")}`);
  });

  it("is filtered by state by one choice, which says what the grid shows, and lifts the hiding of the deactivated accounts of an address of before", async () => {
    // Every account by default: « Tous les états » chosen, and no other control of the state.
    page.search = "offset=2";
    const { rerender } = render(userList(NO_QUERY, second));
    const state = () => screen.getByRole("combobox", { name: "État du compte" });
    expect(state()).toHaveValue("");
    expect(screen.queryByRole("link", { name: /les désactivés$/ })).toBeNull();
    await userEvent.selectOptions(state(), "Comptes désactivés");
    expect(lastAddress()).toBe("/admin/users?is_active=false");
    // An address of before hid the deactivated accounts: it says the active ones alone, which the
    // grid shows, and every state chosen lifts that hiding, the deactivated ones listed again.
    page.search = "origins=local&include_inactive=false&offset=2";
    rerender(userList(NO_QUERY, second, { origins: ["local"], active: true }));
    expect(state()).toHaveValue("true");
    await userEvent.selectOptions(state(), "Tous les états");
    expect(lastAddress()).toBe("/admin/users?origins=local");
    await userEvent.selectOptions(state(), "Comptes désactivés");
    expect(lastAddress()).toBe("/admin/users?origins=local&is_active=false");
  });

  it("is filtered by node of organisation under the name of the contract, back to the first page", async () => {
    page.search = "offset=2";
    render(userList(NO_QUERY, second));
    const bureau = nodes[1]?.id ?? "";
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Nœud d’organisation" }),
      bureau,
    );
    expect(lastAddress()).toBe(`/admin/users?org_node_id=${bureau}`);
  });

  it("leads to the pages before and after the one shown, its filters and its sort kept, and breaks no rule of accessibility", async () => {
    page.search = "origins=local&sort_by=email&sort_order=asc&offset=2";
    const { container } = render(userList(NO_QUERY, second, { origins: ["local"] }));
    const pages = screen.getByRole("navigation", { name: "Pages de la liste" });
    expect(within(pages).getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/admin/users?origins=local&sort_by=email&sort_order=asc",
    );
    expect(within(pages).getByRole("link", { name: /Page suivante/ })).toHaveAttribute(
      "href",
      "/admin/users?origins=local&sort_by=email&sort_order=asc&offset=4",
    );
    await expectAccessible(container);
  });

  it("turns a page from a filter under way to the first page of the accounts", async () => {
    page.search = "offset=2";
    render(userList(NO_QUERY, second));
    const filter = screen.getByRole("group", { name: "Filtrer par origine" });
    await userEvent.click(within(filter).getByRole("button", { name: "Importé de l’annuaire" }));
    expect(lastAddress()).toBe("/admin/users?origins=directory");
    // The origin asked and not arrived: the accounts read otherwise start from their first page.
    await userEvent.click(screen.getByRole("link", { name: /Page suivante/ }));
    expect(lastAddress()).toBe("/admin/users?origins=directory");
  });

  it("keeps its grid when a filter retains no account, and says empty a list nothing narrows", () => {
    const none = { items: [], meta: { limit: 50, offset: 0, total: 0 } };
    const { rerender } = render(userList(NO_QUERY, none, { origins: ["directory"] }));
    expect(screen.getByRole("grid", { name: "Comptes utilisateurs" })).toHaveTextContent(
      "Aucune ligne ne répond à la demande.",
    );
    rerender(userList(NO_QUERY, none));
    expect(screen.queryByRole("grid")).toBeNull();
    expect(screen.getByText("Aucun compte.")).toBeInTheDocument();
  });
});

describe("the commands and the state of the accounts", () => {
  it("offers to a session that may modify the accounts to modify each, to deactivate or reactivate it as it is, and to attribute its roles, each saying it is available with EP-03, and to delete none", async () => {
    const { container } = render(userList(NO_QUERY, users, { editable: true }));
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    expect(within(grid).getAllByRole("button", { name: /^Modifier «/ })).toHaveLength(7);
    expect(within(grid).getAllByRole("button", { name: /^Attribuer les rôles de «/ })).toHaveLength(
      7,
    );
    // Alix Moreau, deactivated, is offered her reactivation; the six others their deactivation.
    expect(within(grid).getAllByRole("button", { name: /^Désactiver «/ })).toHaveLength(6);
    expect(
      within(grid).getByRole("button", { name: "Réactiver «\u00a0Alix Moreau\u00a0»" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
    const told = screen.getByRole("status");
    await userEvent.click(
      within(grid).getByRole("button", { name: "Désactiver «\u00a0Lucas Petit\u00a0»" }),
    );
    expect(told.textContent).toBe(
      "Désactiver «\u00a0Lucas Petit\u00a0»\u00a0: disponible avec EP-03.",
    );
    expect(router.push).not.toHaveBeenCalled();
    await expectAccessible(container);
  });

  it("presents the deactivation of the last administrator unavailable, naming the condition she lacks, the attribution of her roles available, as the account lists them [WF-ADM-0120-A]", async () => {
    render(userList(NO_QUERY, users, { editable: true }));
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    // Camille Martin is the one account active that holds the permissions of administration.
    const deactivation = within(grid).getByRole("button", {
      name: "Désactiver «\u00a0Camille Martin\u00a0»",
    });
    const unmet =
      "Condition non remplie\u00a0: un autre compte actif portant les permissions d’administration.";
    expect(deactivation).toHaveAttribute("aria-disabled", "true");
    expect(deactivation).toHaveAccessibleDescription(unmet);
    // A press does not run it: it says the condition it lacks.
    await userEvent.click(deactivation);
    expect(screen.getByRole("status").textContent).toBe(
      `Désactiver «\u00a0Camille Martin\u00a0»\u00a0: ${unmet}`,
    );
    // Giving her more roles takes none of her permissions away: the attribution stays available.
    const attribution = within(grid).getByRole("button", {
      name: "Attribuer les rôles de «\u00a0Camille Martin\u00a0»",
    });
    expect(attribution).not.toHaveAttribute("aria-disabled");
    await userEvent.click(attribution);
    expect(screen.getByRole("status").textContent).toBe(
      "Attribuer les rôles de «\u00a0Camille Martin\u00a0»\u00a0: disponible avec EP-03.",
    );
    // Another account active is no last administrator: its deactivation is available.
    expect(
      within(grid).getByRole("button", { name: "Désactiver «\u00a0Lucas Petit\u00a0»" }),
    ).not.toHaveAttribute("aria-disabled");
  });

  it("presents no command an account does not list, its modification kept to a session that may modify the accounts", () => {
    // Dominique Bernard read as a session would that the server listed none of her commands for.
    const bare = {
      ...users,
      items: users.items.map((user, at) => (at === 0 ? { ...user, available_commands: [] } : user)),
    };
    render(userList(NO_QUERY, bare, { editable: true }));
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    const name = "«\u00a0Dominique Bernard\u00a0»";
    expect(within(grid).getByRole("button", { name: `Modifier ${name}` })).toBeInTheDocument();
    for (const command of ["Désactiver", "Réactiver", "Attribuer les rôles de"]) {
      expect(within(grid).queryByRole("button", { name: `${command} ${name}` })).toBeNull();
    }
    expect(within(grid).getAllByRole("button", { name: /^Attribuer les rôles de «/ })).toHaveLength(
      6,
    );
  });

  it("tells the creation of a local account pressed in the header when the list holds no account, nothing narrowing it", async () => {
    const none = { items: [], meta: { limit: 50, offset: 0, total: 0 } };
    render(
      inFrench(
        <LaterCommands>
          <CreateCommand kind="localAccount" />
          <UserList
            users={none.items}
            page={none.meta}
            query={NO_QUERY}
            preferences={undefined}
            origins={[]}
            nodes={nodes}
            orgNode={undefined}
            roles={roleChoices}
            accessRoles={[]}
            active={undefined}
            editable
          />
        </LaterCommands>,
      ),
    );
    expect(screen.getByText("Aucun compte.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Créer un compte local" }));
    expect(screen.getByRole("status").textContent).toBe(
      "Créer un compte local\u00a0: disponible avec EP-03.",
    );
  });

  it("presents no command of the accounts to a session that may not modify them", () => {
    render(userList());
    expect(
      screen.queryByRole("button", { name: /^(Modifier|Désactiver|Réactiver|Attribuer)/ }),
    ).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("the grid of the access roles", () => {
  it.each(ACCESS_ROLE_SORTS)(
    "asks the server for the sort by %s, both ways [WF-IHM-0060-A]",
    async (column) => {
      page.path = "/admin/access-roles";
      const { rerender } = render(roleList(false));
      const heading = headingOf(accessRoleGrid(false).columns, column);
      const header = () =>
        within(screen.getByRole("grid", { name: "Rôles d’habilitation" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/admin/access-roles?sort_by=${column}&sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      page.search = ascending.split("?")[1] ?? "";
      rerender(roleList(false, { sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(`/admin/access-roles?sort_by=${column}&sort_order=desc`);
    },
  );

  it("is searched by the server on the label, and says in its totals how many roles the answer holds", async () => {
    page.path = "/admin/access-roles";
    render(roleList(false));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("7 rôles");
    await userEvent.type(screen.getByRole("searchbox", { name: "Rechercher un libellé" }), "Chef");
    await userEvent.keyboard("{Enter}");
    expect(lastAddress()).toBe("/admin/access-roles?search=Chef");
  });

  it("offers to create a role, and to modify and delete each, to a session that may modify the roles, each saying it is available with EP-03, each press anew", async () => {
    page.path = "/admin/access-roles";
    const { container } = render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    expect(within(grid).getAllByRole("button", { name: /^Modifier «/ })).toHaveLength(7);
    expect(within(grid).getAllByRole("button", { name: /^Supprimer «/ })).toHaveLength(7);
    // The region is there from the start, empty, for a reader to hear what is put in it.
    const told = screen.getByRole("status");
    expect(told.textContent).toBe("");

    await userEvent.click(screen.getByRole("button", { name: "Créer un rôle" }));
    expect(told.textContent).toBe("Créer un rôle\u00a0: disponible avec EP-03.");
    const deletion = within(grid).getByRole("button", {
      name: "Supprimer «\u00a0Administrateur\u00a0»",
    });
    expect(deletion).not.toHaveAttribute("aria-disabled");
    await userEvent.click(deletion);
    expect(told.textContent).toBe(
      "Supprimer «\u00a0Administrateur\u00a0»\u00a0: disponible avec EP-03.",
    );
    // The same command pressed again puts a new text in the region, which a reader hears again.
    const said = told.firstElementChild;
    await userEvent.click(deletion);
    expect(told.firstElementChild).not.toBe(said);
    expect(told.textContent).toBe(
      "Supprimer «\u00a0Administrateur\u00a0»\u00a0: disponible avec EP-03.",
    );
    // Nothing is asked of the server: EP-03 wires the commands.
    expect(router.push).not.toHaveBeenCalled();
    expect(router.refresh).not.toHaveBeenCalled();
    await expectAccessible(container);
  });

  it("presents the deletion of a role an account holds unavailable, naming the condition, as the server would refuse it", async () => {
    page.path = "/admin/access-roles";
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    const deletion = within(grid).getByRole("button", {
      name: "Supprimer «\u00a0Chiffreur\u00a0»",
    });
    expect(deletion).toHaveAttribute("aria-disabled", "true");
    expect(deletion).toHaveAccessibleDescription(
      "Porté par 1 compte\u00a0: un rôle ne se supprime pas tant qu’un compte le porte.",
    );
    // A press does not run it, nothing being available: it says the condition it lacks.
    await userEvent.click(deletion);
    expect(screen.getByRole("status").textContent).toBe(
      "Supprimer «\u00a0Chiffreur\u00a0»\u00a0: Porté par 1 compte\u00a0: un rôle ne se supprime pas tant qu’un compte le porte.",
    );
    expect(screen.getByRole("status").textContent).not.toContain("EP-03");
  });

  it("presses the command of the active cell on Enter, the grid one stop of the tabulation", async () => {
    page.path = "/admin/access-roles";
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    const modify = within(grid).getByRole("button", { name: "Modifier «\u00a0Manager\u00a0»" });
    expect(modify).toHaveAttribute("tabindex", "-1");
    const cell = modify.closest("td");
    expect(cell).not.toBeNull();
    // The cell made active, its command not pressed; Enter presses it.
    await userEvent.click(cell as HTMLElement);
    expect(cell).toHaveFocus();
    expect(screen.getByRole("status").textContent).toBe("");
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("status").textContent).toBe(
      "Modifier «\u00a0Manager\u00a0»\u00a0: disponible avec EP-03.",
    );
  });

  it("presents no command to a session that may not modify the roles", () => {
    page.path = "/admin/access-roles";
    render(roleList(false));
    expect(screen.queryByRole("button", { name: "Créer un rôle" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Modifier|Supprimer) «/ })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: "Supprimer" })).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("says an empty list, and offers to create a role all the same to who may", () => {
    page.path = "/admin/access-roles";
    render(roleList(true, NO_QUERY, NO_ROLE_FILTER, []));
    expect(screen.getByText("Aucun rôle d’habilitation.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Créer un rôle" })).toBeInTheDocument();
  });

  it("is filtered by its kind under the name of the contract, and keeps its grid when a filter retains nothing", async () => {
    page.path = "/admin/access-roles";
    page.search = "sort_by=label&sort_order=asc";
    const { rerender } = render(roleList(false));
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Nature" }),
      "Rôles composés",
    );
    expect(lastAddress()).toBe(
      "/admin/access-roles?sort_by=label&sort_order=asc&is_predefined=false",
    );
    rerender(roleList(false, NO_QUERY, { ...NO_ROLE_FILTER, predefined: false }, []));
    expect(screen.queryByText("Aucun rôle d’habilitation.")).toBeNull();
    expect(screen.getByRole("grid", { name: "Rôles d’habilitation" })).toBeInTheDocument();
  });

  it("is bounded on the number of its holders, nought included, under the names of the contract [WF-IHM-0130-A]", async () => {
    page.path = "/admin/access-roles";
    render(roleList(false));
    const bounds = screen.getByRole("form", { name: "Bornes des rôles d’habilitation" });
    await userEvent.type(
      within(bounds).getByRole("textbox", { name: "Comptes porteurs, max." }),
      "0",
    );
    await userEvent.click(within(bounds).getByRole("button", { name: "Filtrer" }));
    expect(lastAddress()).toBe("/admin/access-roles?holder_count_max=0");
  });

  it("says at its field the upper bound the server refuses for preceding the lower one, the list unread, and takes no count that is none", async () => {
    page.path = "/admin/access-roles";
    page.search = "holder_count_min=2&holder_count_max=1";
    const refused = refusedBounds(
      (example("access_roles_bounds_inverted") as Problem).fields ?? [],
    );
    render(
      roleList(
        false,
        NO_QUERY,
        { predefined: undefined, holders: { min: "2", max: "1" }, refused },
        [],
      ),
    );
    const most = screen.getByRole("textbox", { name: "Comptes porteurs, max." });
    expect(most).toHaveAttribute("aria-invalid", "true");
    expect(most).toHaveFocus();
    expect(most).toHaveAccessibleDescription(
      "La borne supérieure ne peut précéder la borne inférieure, 2.",
    );
    expect(screen.queryByRole("grid", { name: "Rôles d’habilitation" })).toBeNull();
    expect(document.body.textContent).toContain(CATALOGUES.fr.reference.boundsRefused);
    // A count is a whole number: 1,5 is not one, and nothing is asked.
    router.push.mockClear();
    await userEvent.clear(most);
    await userEvent.type(most, "1,5{Enter}");
    expect(router.push).not.toHaveBeenCalled();
    expect(most).toHaveAccessibleDescription("Ce n’est pas un nombre valide.");
  });
});
