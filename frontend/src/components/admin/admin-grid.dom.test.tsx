// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { ColumnLabel } from "@/components/grid/columns";
import type { KeptReading } from "@/components/grid/kept-address";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { refusedBounds } from "@/components/grid/filters";
import { NO_AUDIT } from "@/test/accounts";
import { example, type FakeClient, fakeClient, type Problem } from "@/test/fixtures";

import { AccessRoleList, type RoleFilters, UserList } from "./account-lists";
import { type AuditFilters, authorsOf } from "./audit-address";
import { ROLE_KEPT } from "./role-address";
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
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/users", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
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
const anonymized = example("users_anonymized") as {
  items: User[];
  meta: Schemas["PaginationMeta"];
};
const roles = example("access_roles") as AccessRole[];
const roleChoices = roles.map((role) => ({ id: role.access_role_id, label: role.label }));
const nodes = (example("org_nodes") as Schemas["OrgNode"][]).map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
}));

/**
 * A part of the screen, in French, sharing the address last asked as the page does — and, for the
 * screen of the roles, naming what its table keeps.
 */
function inFrench(children: ReactNode, kept?: KeptReading) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress kept={kept}>{children}</PendingAddress>
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
    audit?: AuditFilters;
    editable?: boolean;
  } = {},
) {
  return inFrench(
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
      audit={filters.audit ?? NO_AUDIT}
      authors={authorsOf(shown.items)}
      editable={filters.editable ?? false}
    />,
  );
}

/** No filter of the access roles. */
const NO_ROLE_FILTER: RoleFilters = {
  predefined: undefined,
  holders: { min: undefined, max: undefined },
  audit: NO_AUDIT,
  authors: authorsOf(roles),
};

/** The list of the access roles, as the address asks it. */
function roleList(
  editable: boolean,
  query: GridQuery<AccessRoleSort> = NO_QUERY,
  filters: RoleFilters = NO_ROLE_FILTER,
  shown: readonly AccessRole[] = roles,
  preferences?: GridPreferences,
) {
  return inFrench(
    <AccessRoleList
      roles={shown}
      query={query}
      preferences={preferences}
      filters={filters}
      editable={editable}
    />,
    ROLE_KEPT,
  );
}

const ROLES = "POST /access-roles";
const ROLE = "DELETE /access-roles/{access_role_id}";
const RENAMED = "PATCH /access-roles/{access_role_id}";

/** The region of the table of the roles that says what its last command did, by its name. */
function told(): HTMLElement {
  return screen.getByRole("status", { name: "Commandes des rôles d’habilitation" });
}

/** Confirm the deletion the table asks to confirm, which names the role. */
async function confirmDeletion(label: string) {
  const confirmation = await screen.findByRole("alertdialog", {
    name: `Supprimer «\u00a0${label}\u00a0»\u00a0?`,
  });
  expect(confirmation).toHaveAccessibleDescription(
    `La suppression de «\u00a0${label}\u00a0» est définitive\u00a0: rien ne restaure le rôle.`,
  );
  await userEvent.click(within(confirmation).getByRole("button", { name: "Supprimer" }));
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
  router.replace.mockClear();
  refresh.mockReset();
});

describe("the grid of the accounts", () => {
  it("presents each account with its origin, its roles and its node as the server names them, and says in its totals how many the server retained", () => {
    render(userList());
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    const moreau = within(grid).getByRole("row", { name: /^Moreau/ });
    // Its audit columns after its state, each instant in the local time of the workstation.
    expect(moreau.textContent).toMatch(
      /^MoreauAlixalix\.moreau@example\.comCréé dans WaterfallBureau d'études électricitéChef de projetDésactivé.+Camille Martin.+Camille Martin$/,
    );
    expect([...moreau.querySelectorAll("time")].map((time) => time.dateTime)).toEqual([
      "2026-01-12T10:00:00Z",
      "2026-03-02T16:20:00Z",
    ]);
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("7 comptes");
    // The header of every column is grey, as that of every table (#508).
    expect(grid.querySelector("thead th")?.className).toContain("bg-muted");
  });

  it.each(USER_SORTS)(
    "asks the server for the sort by %s, both ways, back to the first page [WF-IHM-0060-A]",
    async (column) => {
      page.search = "offset=2";
      const { rerender } = render(userList(NO_QUERY, second));
      const heading = headingOf(userGrid().columns, column);
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

describe("an anonymised account", () => {
  it("presents neither its name nor its address, the neutral label in their place [WF-ADM-0060-A]", () => {
    render(userList(NO_QUERY, anonymized));
    const grid = screen.getByRole("grid", { name: "Comptes utilisateurs" });
    const row = within(grid).getAllByRole("row")[1];
    expect(row).toHaveTextContent(
      /^Compte anonymiséCréé dans WaterfallBureau d'études électricitéChef de projetDésactivé.+Camille Martin.+Camille Martin$/,
    );
    expect(grid).not.toHaveTextContent(/Alix|Moreau|alix\.moreau/);
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

  it("offers to a session that may modify the roles to create one in line, to rename each in its cell and to delete each, and breaks no rule of accessibility", async () => {
    page.path = "/admin/access-roles";
    const { container } = render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    expect(within(grid).getAllByRole("button", { name: /^Supprimer «/ })).toHaveLength(7);
    // The renaming is the entry of the label: no command modifies a role besides the matrix.
    expect(within(grid).queryByRole("button", { name: /^Modifier «/ })).toBeNull();
    const creation = screen.getByRole("form", { name: "Création d’un rôle" });
    expect(within(creation).getByRole("textbox", { name: "Nouveau rôle" })).toHaveAttribute(
      "maxlength",
      "100",
    );
    // The region is there from the start, empty, for a reader to hear what is put in it.
    expect(told().textContent).toBe("");
    await expectAccessible(container);
  });

  it("creates a role in line from its label alone, and says at its field the label the server refuses", async () => {
    page.path = "/admin/access-roles";
    const refused: Problem & { status: 422 } = {
      code: "VALIDATION_FAILED",
      status: 422,
      fields: [{ pointer: "/label", code: "VALUE_TOO_LONG", params: { max_length: 100 } }],
    };
    const client = fakeClient({ [ROLES]: { problem: refused } });
    server.client = client;
    render(roleList(true));
    const label = screen.getByRole("textbox", { name: "Nouveau rôle" });
    await userEvent.type(label, "Contrôle de gestion{Enter}");
    await waitFor(() => {
      expect(label).toHaveAttribute("aria-invalid", "true");
    });
    expect(label).toHaveAccessibleDescription(CATALOGUES.fr.errors.VALUE_TOO_LONG);
    expect(label).toHaveFocus();
    expect(client.calls.map(({ route, body }) => [route, body])).toEqual([
      [ROLES, { label: "Contrôle de gestion", permissions: [] }],
    ]);
    // Refused, the label typed stays, to be corrected.
    expect(label).toHaveValue("Contrôle de gestion");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("tells above the table a creation the server refuses otherwise than by its label", async () => {
    page.path = "/admin/access-roles";
    server.client = fakeClient({
      [ROLES]: { problem: { code: "PERMISSION_MISSING", status: 403 } },
    });
    render(roleList(true));
    await userEvent.type(screen.getByRole("textbox", { name: "Nouveau rôle" }), "Audit{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.PERMISSION_MISSING,
    );
  });

  it("deletes a role no account holds once its deletion is confirmed, says so, and reads the page anew", async () => {
    page.path = "/admin/access-roles";
    const client = fakeClient({ [ROLE]: { status: 204 } });
    server.client = client;
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    await userEvent.click(
      within(grid).getByRole("button", { name: "Supprimer «\u00a0Administrateur\u00a0»" }),
    );
    // Final, a predefined role included: nothing is asked before it is confirmed.
    expect(client.calls).toEqual([]);
    await confirmDeletion("Administrateur");
    await waitFor(() => {
      expect(told().textContent).toBe("«\u00a0Administrateur\u00a0» supprimé.");
    });
    const administrator = roles.find((role) => role.label === "Administrateur");
    expect(client.calls.map(({ route, path }) => [route, path])).toEqual([
      [ROLE, `/access-roles/${administrator?.access_role_id ?? ""}`],
    ]);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("tells by the catalogue a role the server refuses to delete, an account holding it since it was read", async () => {
    page.path = "/admin/access-roles";
    server.client = fakeClient({
      [ROLE]: { problem: { code: "ACCESS_ROLE_IN_USE", status: 409 } },
    });
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    await userEvent.click(
      within(grid).getByRole("button", { name: "Supprimer «\u00a0Administrateur\u00a0»" }),
    );
    await confirmDeletion("Administrateur");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      CATALOGUES.fr.errors.ACCESS_ROLE_IN_USE,
    );
    expect(told().textContent).toBe("");
    expect(refresh).not.toHaveBeenCalled();
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
    // A press does not run it: it says the condition it lacks, each press anew.
    await userEvent.click(deletion);
    expect(told().textContent).toBe(
      "Supprimer «\u00a0Chiffreur\u00a0»\u00a0: Porté par 1 compte\u00a0: un rôle ne se supprime pas tant qu’un compte le porte.",
    );
    const said = told().firstElementChild;
    await userEvent.click(deletion);
    expect(told().firstElementChild).not.toBe(said);
  });

  it("presses the command of the active cell on Enter, the grid one stop of the tabulation, which opens the confirmation of the deletion: Escape gives it up, nothing deleted, the focus back on the cell", async () => {
    page.path = "/admin/access-roles";
    const client = fakeClient({ [ROLE]: { status: 204 } });
    server.client = client;
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    const deletion = within(grid).getByRole("button", {
      name: "Supprimer «\u00a0Administrateur\u00a0»",
    });
    expect(deletion).toHaveAttribute("tabindex", "-1");
    const cell = deletion.closest("td");
    expect(cell).not.toBeNull();
    // The cell made active, its command not pressed; Enter presses it, and asks to confirm.
    await userEvent.click(cell as HTMLElement);
    expect(cell).toHaveFocus();
    expect(client.calls).toEqual([]);
    await userEvent.keyboard("{Enter}");
    const confirmation = await screen.findByRole("alertdialog");
    expect(within(confirmation).getByRole("button", { name: "Conserver" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).toBeNull();
    });
    expect(cell).toHaveFocus();
    expect(client.calls).toEqual([]);
    expect(told().textContent).toBe("");
    // Asked again and confirmed, the deletion is sent.
    await userEvent.keyboard("{Enter}");
    await confirmDeletion("Administrateur");
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual([ROLE]);
    });
  });

  it("renames a role in its cell, from the version read with the permissions the row reads, and tells the role changed meanwhile", async () => {
    page.path = "/admin/access-roles";
    const client = fakeClient({
      [RENAMED]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } },
    });
    server.client = client;
    render(roleList(true));
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    const label = within(grid).getByText("Manager").closest<HTMLElement>("[tabindex]");
    label?.focus();
    await userEvent.keyboard("Responsable de service{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(/Recharger/);
    const manager = roles.find((role) => role.label === "Manager");
    expect(client.calls.map(({ path, body }) => [path, body])).toEqual([
      [
        `/access-roles/${manager?.access_role_id ?? ""}`,
        {
          label: "Responsable de service",
          permissions: manager?.permissions,
          lock_version: manager?.lock_version,
        },
      ],
    ]);
  });

  it("presents no command to a session that may not modify the roles, nor any label to enter", async () => {
    page.path = "/admin/access-roles";
    render(roleList(false));
    expect(screen.queryByRole("form", { name: "Création d’un rôle" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Modifier|Supprimer) «/ })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: "Supprimer" })).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
    const grid = screen.getByRole("grid", { name: "Rôles d’habilitation" });
    within(grid).getByText("Manager").closest<HTMLElement>("[tabindex]")?.focus();
    await userEvent.keyboard("Responsable{Enter}");
    expect(screen.queryByRole("textbox", { name: "Libellé" })).toBeNull();
    expect(within(grid).getByText("Manager")).toBeInTheDocument();
  });

  it("keeps the filters the page shows with the settings of the grid, its sort and its columns as the account kept them", async () => {
    page.path = "/admin/access-roles";
    page.search = "search=Chef&is_predefined=false&holder_count_max=0";
    const kept: GridPreferences = {
      hidden_columns: ["holder_count"],
      sort: { column: "label", order: "desc" },
      filters: { is_predefined: "true" },
    };
    render(roleList(false, NO_QUERY, NO_ROLE_FILTER, roles, kept));
    const client = server.client as FakeClient;
    await waitFor(() => {
      expect(client.calls.map(({ route }) => route)).toEqual(["PATCH /me/preferences"]);
    });
    expect(client.calls[0]?.body).toEqual({
      grids: {
        access_roles: {
          hidden_columns: ["holder_count"],
          column_widths: {},
          sort: { column: "label", order: "desc" },
          filters: { search: "Chef", is_predefined: "false", holder_count_max: "0" },
        },
      },
    });
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("says in the address a reading whose last filter is lifted, which empties the filters kept and is never filled in [WF-IHM-0060-A]", async () => {
    page.path = "/admin/access-roles";
    page.search = "is_predefined=false";
    const kept: GridPreferences = { filters: { is_predefined: "false" } };
    const { rerender } = render(
      roleList(false, NO_QUERY, { ...NO_ROLE_FILTER, predefined: false }, roles, kept),
    );
    // Both natures chosen: the address would say nothing of the grid, and says the search empty, so
    // that the page does not find the filters kept again.
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Nature" }),
      "Toutes les natures",
    );
    expect(lastAddress()).toBe("/admin/access-roles?search=");
    page.search = "search=";
    rerender(roleList(false, NO_QUERY, NO_ROLE_FILTER, roles, kept));
    const client = server.client as FakeClient;
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual({
      grids: { access_roles: { hidden_columns: [], column_widths: {}, filters: {} } },
    });
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("opens at the address that says the grid as it says it, and keeps a reading whose filters are lifted within the screen", async () => {
    page.path = "/admin/access-roles";
    page.search = "sort_by=holder_count&sort_order=asc";
    const kept: GridPreferences = { filters: { is_predefined: "false" } };
    const { rerender } = render(roleList(false, NO_QUERY, NO_ROLE_FILTER, roles, kept));
    const client = server.client as FakeClient;
    // A sort said: the address is the truth, and its filters, none, are kept.
    await waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({ grids: { access_roles: { filters: {} } } });
    page.search = "is_predefined=true";
    rerender(roleList(false, NO_QUERY, NO_ROLE_FILTER, roles, kept));
    await waitFor(() => {
      expect(client.calls).toHaveLength(2);
    });
    // Lifted, the address says so: kept as such, never filled in.
    page.search = "search=";
    rerender(roleList(false, NO_QUERY, NO_ROLE_FILTER, roles, kept));
    await waitFor(() => {
      expect(client.calls).toHaveLength(3);
    });
    expect(client.calls[2]?.body).toMatchObject({ grids: { access_roles: { filters: {} } } });
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("says an empty list, and offers to create a role all the same to who may", () => {
    page.path = "/admin/access-roles";
    render(roleList(true, NO_QUERY, NO_ROLE_FILTER, []));
    expect(screen.getByText("Aucun rôle d’habilitation.")).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Création d’un rôle" })).toBeInTheDocument();
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
        { ...NO_ROLE_FILTER, holders: { min: "2", max: "1" }, refused },
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
