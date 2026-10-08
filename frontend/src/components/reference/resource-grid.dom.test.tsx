// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import { listReads } from "./address";
import { type ActivationTarget, Reactivations, StateCell } from "./reactivation";
import { InactiveSwitch, OrgNodeFilter } from "./reference-filters";
import { ResourceGrid } from "./resource-grid";
import {
  CALENDAR_SORTS,
  type Calendar,
  type CalendarSort,
  calendarGrid as calendarGridConfig,
  ORG_NODE_ADDRESS,
  type OrgNode,
  RESOURCE_ROLE_ADDRESS,
  RESOURCE_ROLE_SORTS,
  ROLE_ORG_NODE,
  type ResourceRole,
  type ResourceRoleSort,
  resourceRoleGrid,
} from "./resource-grids";

// The server of Next, as far as the screen needs it: the fake back, the page rendered again once
// an object is reactivated, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const ROLE_ACTIVATION = "PUT /reference/resource-roles/{resource_role_id}/activation";
const NO_QUERY = { sort: undefined, search: undefined };

const nodes = example("org_nodes") as OrgNode[];
const rolePage = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };
const roles = rolePage.items;
const calendarPage = example("calendars") as { items: Calendar[]; meta: ListPage };
const calendars = calendarPage.items;
// The automation engineer, deactivated, as the list reads it with the deactivated ones.
const AUTOMATION = roles.find((role) => role.label === "Automaticien");
// The programmer of automata, deactivated under a node deactivated: its reactivation unavailable.
const PROGRAMMER = roles.find((role) => role.label === "Programmeur d'automates");

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({
    [ROLE_ACTIVATION]: "resource_role_reactivated",
    "PATCH /me/preferences": "preferences",
    ...answers,
  });
  server.client = client;
  return client;
}

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the roles, in its list, as the address asks it. */
function roleGrid(
  query: GridQuery<ResourceRoleSort> = NO_QUERY,
  rows: readonly ResourceRole[] = roles,
) {
  return inFrench(
    <Reactivations reads={listReads(RESOURCE_ROLE_ADDRESS, ROLE_ORG_NODE)}>
      <ResourceGrid
        kind="resourceRoles"
        rows={rows}
        page={rolePage.meta}
        query={query}
        preferences={undefined}
      />
    </Reactivations>,
  );
}

/** The cell of a row of the grid, by its index among the rows of the answer, and of a column. */
function cell(row: number, column: string): HTMLElement {
  const found = document.querySelector<HTMLElement>(
    `td[data-row="${row.toString()}"][data-column="${column}"]`,
  );
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The calls of the fake back but the preferences of the grids, which a sort writes. */
function activations(client: FakeClient) {
  return client.calls.filter((call) => call.route !== "PATCH /me/preferences");
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.search = "";
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
  refresh.mockClear();
});

describe("the tree of the organisation", () => {
  it("is a tree grid in the order the server gives, no header offering to sort it, which folds and unfolds [WF-IHM-0060-A]", async () => {
    serve();
    render(
      inFrench(
        <ResourceGrid
          kind="orgNodes"
          rows={nodes}
          query={NO_QUERY}
          preferences={undefined}
          narrowing={{}}
        />,
      ),
    );
    const tree = screen.getByRole("treegrid", { name: "Arbre d’organisation" });
    expect(within(tree).queryAllByRole("button", { name: /Trier/ })).toEqual([]);
    expect(tree.querySelectorAll("thead button")).toHaveLength(0);
    const labels = () =>
      within(tree)
        .getAllByRole("row")
        .slice(1, -1)
        .map((row) => row.querySelector('td[data-column="label"]')?.textContent);
    expect(labels()).toEqual([
      "Direction technique",
      "Bureau d'études électricité",
      "Atelier de câblage",
      "Service des achats",
    ]);
    const direction = within(tree).getAllByRole("row")[1];
    expect(direction).toHaveAttribute("aria-level", "1");
    expect(direction).toHaveAttribute("aria-expanded", "true");
    // The bureau folds the workshop under it.
    const bureau = within(tree).getAllByRole("row")[2];
    if (bureau === undefined) {
      throw new Error("no row of the bureau");
    }
    await userEvent.click(within(bureau).getByRole("button", { name: "Plier" }));
    expect(labels()).toEqual([
      "Direction technique",
      "Bureau d'études électricité",
      "Service des achats",
    ]);
    await userEvent.click(within(bureau).getByRole("button", { name: "Déplier" }));
    expect(labels()).toHaveLength(4);
    // The totals row counts the nodes of the answer, never a sum.
    expect(tree.querySelector("tfoot tr")?.textContent).toBe("4 nœuds");
  });

  it("asks the server for the nodes a search retains, under the names of its grid", async () => {
    serve();
    page.search = "role_sort_by=label";
    render(
      inFrench(
        <ResourceGrid
          kind="orgNodes"
          rows={nodes}
          query={NO_QUERY}
          preferences={undefined}
          narrowing={{}}
        />,
      ),
    );
    const search = screen.getByRole("searchbox", {
      name: "Rechercher dans «\u00a0Arbre d’organisation\u00a0»",
    });
    await userEvent.type(search, "BE{Enter}");
    expect(lastAddress()).toBe("/reference/resources?role_sort_by=label&org_search=BE");
  });
});

describe("the grid of the resource roles", () => {
  it.each(RESOURCE_ROLE_SORTS)(
    "asks the server for the sort by %s under the names of its grid, both ways [WF-IHM-0060-A]",
    async (column) => {
      serve();
      const { rerender } = render(roleGrid());
      const label = resourceRoleGrid().columns.find((each) => each.contract === column)?.label;
      const heading = label === undefined ? "" : CATALOGUES.fr.grid.columns[label];
      const header = () =>
        within(screen.getByRole("grid", { name: "Rôles de ressources" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/reference/resources?role_sort_by=${column}&role_sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      // The page answers the sort asked: a second click asks the other way.
      page.search = ascending.split("?")[1] ?? "";
      rerender(roleGrid({ sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(
        `/reference/resources?role_sort_by=${column}&role_sort_order=desc`,
      );
    },
  );

  it("says in its totals how many roles the server retains, never a count of the page [WF-IHM-0130-A]", () => {
    serve();
    // A page of the two first roles of the witness, of the five the server retains.
    render(roleGrid({ sort: undefined, search: "Ing" }, roles.slice(0, 2)));
    const grid = screen.getByRole("grid", { name: "Rôles de ressources" });
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("5 rôles");
    expect(
      screen.getByRole("searchbox", { name: "Rechercher dans «\u00a0Rôles de ressources\u00a0»" }),
    ).toHaveValue("Ing");
  });

  it("is filtered by node, the address changed under the name of its grid, the rest kept", async () => {
    serve();
    page.search = "include_inactive=true";
    render(
      inFrench(
        <OrgNodeFilter
          name="role_org_node_id"
          nodes={nodes.map((node) => ({
            id: node.org_node_id,
            code: node.code,
            label: node.label,
            level: node.level,
          }))}
          chosen={undefined}
        />,
      ),
    );
    const filter = screen.getByRole("combobox", { name: "Nœud d’organisation" });
    const bureau = nodes[1]?.org_node_id ?? "";
    await userEvent.selectOptions(filter, bureau);
    expect(lastAddress()).toBe(
      `/reference/resources?include_inactive=true&role_org_node_id=${bureau}`,
    );
  });

  it("keeps a node the address names that the tree does not hold, to be cleared", async () => {
    serve();
    page.search = "role_org_node_id=gone";
    render(inFrench(<OrgNodeFilter name="role_org_node_id" nodes={[]} chosen="gone" />));
    const filter = screen.getByRole("combobox", { name: "Nœud d’organisation" });
    expect(filter).toHaveValue("gone");
    await userEvent.selectOptions(filter, "");
    expect(lastAddress()).toBe("/reference/resources");
  });

  it("reactivates a deactivated role from the version read, and the page reads its lists anew [WF-REF-0150-A]", async () => {
    const client = serve();
    render(roleGrid());
    const reactivate = screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" });
    await userEvent.click(reactivate);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(activations(client)).toEqual([
      expect.objectContaining({
        route: ROLE_ACTIVATION,
        path: `/reference/resource-roles/${AUTOMATION?.resource_role_id ?? ""}/activation`,
        body: { is_active: true, lock_version: 1 },
      }),
    ]);
    expect(screen.queryByRole("alert")).toBeNull();
    // Only a deactivated role offers it.
    expect(screen.getAllByRole("button", { name: /^Réactiver/ })).toHaveLength(
      roles.filter((role) => !role.is_active).length,
    );
    // An active role carries its deactivation, which no screen offers yet.
    expect(screen.queryByRole("button", { name: /Désactiver/ })).toBeNull();
  });

  it("reactivates from the keyboard, Enter on the cell of the state, the grid one stop", async () => {
    const client = serve();
    render(roleGrid());
    const row = roles.findIndex((role) => role === AUTOMATION);
    expect(
      screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
    ).toHaveAttribute("tabindex", "-1");
    cell(row, "state").focus();
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(activations(client)).toHaveLength(1);
    });
  });

  it("says the refusal of a reactivation above the list until dismissed, and the page is not read anew", async () => {
    serve({ [ROLE_ACTIVATION]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    render(roleGrid());
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    expect(refresh).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the refusal of a reactivation said when another succeeds after it, and gives the focus back to the grid once dismissed", async () => {
    const client = serve({
      [ROLE_ACTIVATION]: [
        { problem: { code: "PERMISSION_MISSING", status: 403 } },
        "resource_role_reactivated",
      ],
    });
    // Every other role read deactivated, its reactivation available.
    const second = roles.map((role) =>
      role === AUTOMATION
        ? role
        : { ...role, is_active: false, available_commands: AUTOMATION?.available_commands ?? [] },
    );
    render(roleGrid(NO_QUERY, second));
    const [first, other] = screen.getAllByRole("button", { name: /^Réactiver/ });
    if (first === undefined || other === undefined) {
      throw new Error("two roles deactivated");
    }
    await userEvent.click(first);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    await userEvent.click(other);
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(activations(client)).toHaveLength(2);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    // The focus back on the active cell of the grid, the one stop of its tabulation.
    const active = screen
      .getByRole("grid", { name: "Rôles de ressources" })
      .querySelector('tbody [tabindex="0"]');
    expect(active).not.toBeNull();
    expect(active).toHaveFocus();
  });

  it("says nothing of a refusal answered after the address changed, on the list now shown", async () => {
    let answer: (value?: unknown) => void = () => undefined;
    const client = fakeClient(
      { [ROLE_ACTIVATION]: { problem: { code: "PERMISSION_MISSING", status: 403 } } },
      {
        hold: () =>
          new Promise((resolve) => {
            answer = resolve;
          }),
      },
    );
    server.client = client;
    page.search = "include_inactive=true";
    const { rerender } = render(roleGrid());
    const command = screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" });
    await userEvent.click(command);
    // The deactivated ones hidden meanwhile: another reading of the list.
    page.search = "";
    rerender(roleGrid());
    answer();
    await vi.waitFor(() => {
      expect(command).not.toHaveAttribute("aria-busy", "true");
    });
    expect(client.calls).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
    // Back on the reading it was asked from, it is said.
    page.search = "include_inactive=true";
    rerender(roleGrid());
    expect(await screen.findByRole("alert")).toHaveTextContent("Vous n’avez pas la permission");
  });

  it("keeps the refusal of a reactivation said when another list of the screen is sorted", async () => {
    serve({ [ROLE_ACTIVATION]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    page.search = "include_inactive=true";
    const { rerender } = render(roleGrid());
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Vous n’avez pas la permission");
    // The calendars sorted: the roles are read as they were.
    page.search = "include_inactive=true&calendar_sort_by=label&calendar_sort_order=asc";
    rerender(roleGrid());
    expect(screen.getByRole("alert")).toHaveTextContent("Vous n’avez pas la permission");
    // The roles filtered by a node: another reading of their list.
    page.search = `${page.search}&role_org_node_id=${nodes[1]?.org_node_id ?? ""}`;
    rerender(roleGrid());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("offers no reactivation the server does not list, as for a session that may not modify the settings of the resources [WF-IHM-0090-A]", () => {
    serve();
    // The server lists no command to who reads the reference without modifying it.
    const read = example("resource_roles_reader") as { items: ResourceRole[] };
    render(roleGrid(NO_QUERY, read.items));
    expect(screen.queryByRole("button", { name: /^Réactiver/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Désactiver/ })).toBeNull();
    expect(cell(0, "state")).toHaveTextContent(/^Actif$/);
  });

  it("presents the reactivation of a role whose node is deactivated unavailable, with its condition, and says it when pressed [WF-IHM-0090-A] [WF-REF-0080-A]", async () => {
    const client = serve();
    render(roleGrid());
    const command = screen.getByRole("button", {
      name: "Réactiver «\u00a0Programmeur d'automates\u00a0»",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      "Condition non remplie\u00a0: nœud d’organisation actif.",
    );
    await userEvent.click(command);
    expect(screen.getByRole("status")).toHaveTextContent(
      "La réactivation de « Programmeur d'automates » est indisponible. Condition non remplie : nœud d’organisation actif.",
    );
    // Never run: nothing asked of the server, nothing read anew.
    expect(activations(client)).toEqual([]);
    expect(refresh).not.toHaveBeenCalled();
    // From the keyboard too, Enter on its cell, the grid one stop.
    cell(
      roles.findIndex((role) => role === PROGRAMMER),
      "state",
    ).focus();
    await userEvent.keyboard("{Enter}");
    expect(activations(client)).toEqual([]);
  });

  it("says in the region of the list the conditions of an unavailable reactivation pressed from the keyboard, Enter on its cell [WF-IHM-0090-A]", async () => {
    const client = serve();
    render(roleGrid());
    expect(screen.getByRole("status")).toHaveTextContent(/^$/);
    cell(
      roles.findIndex((role) => role === PROGRAMMER),
      "state",
    ).focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("status")).toHaveTextContent(
      "La réactivation de « Programmeur d'automates » est indisponible. Condition non remplie : nœud d’organisation actif.",
    );
    expect(activations(client)).toEqual([]);
  });

  it("says the conditions of an unavailable reactivation on the reading of the list it was pressed on alone", async () => {
    serve();
    const { rerender } = render(roleGrid());
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Programmeur d'automates\u00a0»" }),
    );
    expect(screen.getByRole("status")).toHaveTextContent("est indisponible");
    // The roles filtered by a node meanwhile: another reading of their list, which it says nothing of.
    page.search = `role_org_node_id=${nodes[1]?.org_node_id ?? ""}`;
    rerender(roleGrid());
    expect(screen.getByRole("status")).toHaveTextContent(/^$/);
  });

  it("says the refusal of the server when the node was deactivated meanwhile, naming the node to reactivate first [WF-REF-0080-A]", async () => {
    // The programmer read while its node was active, its reactivation then available; the node
    // deactivated since, the server refuses it, nothing being written.
    const refused = example("resource_role_reactivation_refused") as Problem & { status: 409 };
    serve({ [ROLE_ACTIVATION]: { problem: refused } });
    const read = roles.map((role) =>
      role === PROGRAMMER
        ? { ...role, available_commands: AUTOMATION?.available_commands ?? [] }
        : role,
    );
    render(roleGrid(NO_QUERY, read));
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Programmeur d'automates\u00a0»" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : nœud d’organisation actif.",
    );
    expect(alert).toHaveTextContent("Objet en conflit : Bureau d'études automatismes.");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the refusal of a version stale, and offers to read the page anew", async () => {
    const stale = example("resource_role_activation_stale") as Problem & { status: 412 };
    serve({ [ROLE_ACTIVATION]: { problem: stale } });
    render(roleGrid());
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Quelqu’un a modifié cette donnée entre-temps ; rechargez-la pour voir sa dernière version.",
    );
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("breaks no rule of accessibility", async () => {
    serve();
    const { container } = render(roleGrid());
    await expectAccessible(container);
  });
});

describe("the grid of the calendars", () => {
  /** The grid of the calendars, as the address asks it. */
  const calendarGrid = (query: GridQuery<CalendarSort> = NO_QUERY) =>
    inFrench(
      <ResourceGrid
        kind="calendars"
        rows={calendars}
        page={calendarPage.meta}
        query={query}
        preferences={undefined}
      />,
    );

  it.each(CALENDAR_SORTS)(
    "asks the server for the sort by %s under the names of its grid, both ways [WF-IHM-0060-A]",
    async (column) => {
      serve();
      const { rerender } = render(calendarGrid());
      const label = calendarGridConfig().columns.find((each) => each.contract === column)?.label;
      const heading = label === undefined ? "" : CATALOGUES.fr.grid.columns[label];
      const header = () =>
        within(screen.getByRole("grid", { name: "Calendriers" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/reference/resources?calendar_sort_by=${column}&calendar_sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      // The page answers the sort asked: a second click asks the other way.
      page.search = ascending.split("?")[1] ?? "";
      rerender(calendarGrid({ sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(
        `/reference/resources?calendar_sort_by=${column}&calendar_sort_order=desc`,
      );
    },
  );

  it("offers to sort each of its columns, the hours of each day too, and marks the default calendar", () => {
    serve();
    render(calendarGrid());
    const grid = screen.getByRole("grid", { name: "Calendriers" });
    const sorted = [...grid.querySelectorAll("thead th")]
      .filter((header) => header.querySelector("button") !== null)
      .map((header) => header.textContent);
    expect(sorted).toEqual([
      "Libellé",
      "Lun.",
      "Mar.",
      "Mer.",
      "Jeu.",
      "Ven.",
      "Sam.",
      "Dim.",
      "Par défaut",
      "État",
    ]);
    // By label, as the list without sort gives them: the standard week, the default one, second.
    expect(cell(0, "is_default")).toHaveTextContent(/^$/);
    expect(cell(1, "is_default")).toHaveTextContent("Calendrier par défaut");
  });
});

describe("the reactivation of a node of the organisation", () => {
  const NODE_ACTIVATION = "PUT /reference/org-nodes/{org_node_id}/activation";
  // The tree with its deactivated nodes: the office of automation, and the robotics cell under it.
  const tree = example("org_nodes_with_inactive") as OrgNode[];

  /** The tree, in its list, its rows as given. */
  const nodeGrid = (rows: readonly OrgNode[] = tree) =>
    inFrench(
      <Reactivations reads={listReads(ORG_NODE_ADDRESS)}>
        <ResourceGrid
          kind="orgNodes"
          rows={rows}
          query={NO_QUERY}
          preferences={undefined}
          narrowing={{}}
        />
      </Reactivations>,
    );

  it("says the refusal of the server when the parent was deactivated meanwhile, naming the parent to reactivate first [WF-REF-0080-A]", async () => {
    const refused = example("org_node_reactivation_refused") as Problem & { status: 409 };
    serve({ [NODE_ACTIVATION]: { problem: refused } });
    // The robotics cell read while its parent was active, its reactivation then available.
    const office = tree.find((node) => node.code === "BE-AUTO");
    const read = tree.map((node) =>
      node.code === "CEL-ROBOT"
        ? { ...node, available_commands: office?.available_commands ?? [] }
        : node,
    );
    render(nodeGrid(read));
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Cellule robotique\u00a0»" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : nœud parent actif.",
    );
    expect(alert).toHaveTextContent("Objet en conflit : Bureau d'études automatismes.");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("says the refusal of a version stale, and reading the page anew gives the focus back to the active cell of the grid", async () => {
    const stale = example("org_node_activation_stale") as Problem & { status: 412 };
    serve({ [NODE_ACTIVATION]: { problem: stale } });
    render(nodeGrid());
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Bureau d'études automatismes\u00a0»" }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Quelqu’un a modifié cette donnée entre-temps ; rechargez-la pour voir sa dernière version.",
    );
    await userEvent.click(within(alert).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
    const active = screen
      .getByRole("treegrid", { name: "Arbre d’organisation" })
      .querySelector('tbody [tabindex="0"]');
    expect(active).not.toBeNull();
    expect(active).toHaveFocus();
  });

  it("reactivates the parent, whose reactivation the server lists available, from the version read [WF-REF-0150-A]", async () => {
    const client = serve({ [NODE_ACTIVATION]: "org_node_reactivated" });
    render(nodeGrid());
    expect(
      screen.getByRole("button", { name: "Réactiver «\u00a0Cellule robotique\u00a0»" }),
    ).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Bureau d'études automatismes\u00a0»" }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(activations(client).map((call) => [call.path, call.body])).toEqual([
      [
        "/reference/org-nodes/01926f3a-7c00-7000-8000-000000000474/activation",
        { is_active: true, lock_version: 1 },
      ],
    ]);
  });
});

describe("the three grids of the screen", () => {
  it("name their searches and their menus of the columns after each grid, told apart", () => {
    serve();
    render(
      inFrench(
        <>
          <ResourceGrid
            kind="orgNodes"
            rows={nodes}
            query={NO_QUERY}
            preferences={undefined}
            narrowing={{}}
          />
          <ResourceGrid
            kind="resourceRoles"
            rows={roles}
            page={rolePage.meta}
            query={NO_QUERY}
            preferences={undefined}
          />
          <ResourceGrid
            kind="calendars"
            rows={calendars}
            page={calendarPage.meta}
            query={NO_QUERY}
            preferences={undefined}
          />
        </>,
      ),
    );
    const searches = screen
      .getAllByRole("searchbox")
      .map((search) => search.getAttribute("aria-label"));
    expect(searches).toEqual([
      "Rechercher dans «\u00a0Arbre d’organisation\u00a0»",
      "Rechercher dans «\u00a0Rôles de ressources\u00a0»",
      "Rechercher dans «\u00a0Calendriers\u00a0»",
    ]);
    const menus = screen
      .getAllByRole("button", { name: /^Colonnes de/ })
      .map((menu) => menu.getAttribute("aria-label"));
    expect(menus).toEqual([
      "Colonnes de «\u00a0Arbre d’organisation\u00a0»",
      "Colonnes de «\u00a0Rôles de ressources\u00a0»",
      "Colonnes de «\u00a0Calendriers\u00a0»",
    ]);
  });
});

describe("the reactivation of each kind of object", () => {
  // The reactivation available, as the server lists it on the automation engineer.
  const REACTIVATE = AUTOMATION?.available_commands ?? [];

  it("says a 409 the server opposes as any refusal, by the condition it names", async () => {
    // The refusal of the reactivation of a node whose parent is deactivated, as its example gives it,
    // in a simple table: the list says it by the condition it names.
    const refused = example("org_node_reactivation_refused") as Problem & { status: 409 };
    serve({ "PUT /reference/org-nodes/{org_node_id}/activation": { problem: refused } });
    render(
      inFrench(
        <Reactivations reads={listReads()}>
          <StateCell
            active={false}
            target={{ kind: "org_node", id: "n", lockVersion: 1 }}
            name="Cellule robotique"
            commands={REACTIVATE}
          />
        </Reactivations>,
      ),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Réactiver «\u00a0Cellule robotique\u00a0»" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : nœud parent actif.",
    );
    expect(refresh).not.toHaveBeenCalled();
    // A simple table holds no grid: the focus goes back to the list, ringed when it is visible.
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    const list = document.querySelector<HTMLElement>('div[tabindex="-1"]');
    expect(list).toHaveFocus();
    expect(list?.className).toContain("focus-visible:ring-2");
  });

  const targets: readonly [ActivationTarget, string][] = [
    [{ kind: "org_node", id: "n", lockVersion: 3 }, "/reference/org-nodes/n/activation"],
    [{ kind: "calendar", id: "c", lockVersion: 2 }, "/reference/calendars/c/activation"],
    [{ kind: "cost_type", id: "t", lockVersion: 1 }, "/reference/cost-types/t/activation"],
    [{ kind: "cost_category", id: "k", lockVersion: 4 }, "/reference/cost-categories/k/activation"],
  ];

  it.each(targets)(
    "asks the operation of its kind, from the version read [WF-REF-0150-A]",
    async (target, path) => {
      const client = serve({
        "PUT /reference/org-nodes/{org_node_id}/activation": {
          problem: { code: "NOT_FOUND", status: 404 },
        },
        "PUT /reference/calendars/{calendar_id}/activation": {
          problem: { code: "NOT_FOUND", status: 404 },
        },
        "PUT /reference/cost-types/{cost_type_id}/activation": {
          problem: { code: "NOT_FOUND", status: 404 },
        },
        "PUT /reference/cost-categories/{cost_category_id}/activation": {
          problem: { code: "NOT_FOUND", status: 404 },
        },
      });
      render(
        inFrench(
          <Reactivations reads={listReads()}>
            <StateCell active={false} target={target} name="Objet" commands={REACTIVATE} />
          </Reactivations>,
        ),
      );
      await userEvent.click(screen.getByRole("button", { name: "Réactiver «\u00a0Objet\u00a0»" }));
      expect(await screen.findByRole("alert")).toHaveTextContent("Introuvable");
      expect(activations(client).map((call) => [call.path, call.body])).toEqual([
        [path, { is_active: true, lock_version: target.lockVersion }],
      ]);
    },
  );
});

describe("the switch of the deactivated objects", () => {
  it("shows them too, the rest of the address kept, and hides them again [WF-REF-0150-A]", async () => {
    page.search = "role_search=Ing";
    const { rerender } = render(inFrench(<InactiveSwitch shown={false} />));
    const show = screen.getByRole("link", { name: "Afficher aussi les désactivés" });
    expect(show).toHaveAttribute(
      "href",
      "/reference/resources?role_search=Ing&include_inactive=true",
    );
    await userEvent.click(show);
    expect(lastAddress()).toBe("/reference/resources?role_search=Ing&include_inactive=true");
    page.search = "role_search=Ing&include_inactive=true";
    rerender(inFrench(<InactiveSwitch shown />));
    expect(screen.getByRole("link", { name: "Masquer les désactivés" })).toHaveAttribute(
      "href",
      "/reference/resources?role_search=Ing",
    );
  });
});
