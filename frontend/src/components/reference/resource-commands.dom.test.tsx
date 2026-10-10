// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
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

import type { CostCategory, CostType } from "./cost-kinds";
import { type Choice, labourOf } from "./kinds";
import type { Calendar, OrgNode, ResourceRole } from "./resource-grids";
import {
  CalendarList,
  type DayBounds,
  type NodeOffered,
  OrgNodeList,
  ResourceRoleList,
} from "./resource-lists";

// The server of Next, as far as the lists need it: the fake back, the page rendered again once an
// object is written, the address they read and the navigations they ask.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const refresh = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));

const NODES = "POST /reference/org-nodes";
const NODE = "PATCH /reference/org-nodes/{org_node_id}";
const NODE_ACTIVATION = "PUT /reference/org-nodes/{org_node_id}/activation";
const ROLES = "POST /reference/resource-roles";
const ROLE = "PATCH /reference/resource-roles/{resource_role_id}";
const ROLE_ACTIVATION = "PUT /reference/resource-roles/{resource_role_id}/activation";
const CALENDARS = "POST /reference/calendars";
const CALENDAR = "PATCH /reference/calendars/{calendar_id}";
const DEFAULT = "PUT /reference/calendars/{calendar_id}/default";

const NO_QUERY = { sort: undefined, search: undefined };
const NO_BOUNDS = { min: undefined, max: undefined };
const tree = example("org_nodes_with_inactive") as OrgNode[];
const roles = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };
const calendars = example("calendars_with_inactive") as { items: Calendar[]; meta: ListPage };
const natures = example("cost_types") as { items: CostType[] };

/** The nodes of the whole tree, deactivated ones among them, as the page offers them. */
const NODE_CHOICES: NodeOffered[] = tree.map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
  active: node.is_active,
}));

/** The nodes of the tree read without the deactivated ones. */
const ACTIVE_NODES = NODE_CHOICES.filter((node) => node.active);

/** The first categories of labour of the volumes, as the page offers them to a role. */
const LABOUR: Choice[] = (
  labourOf((example("volume/cost_categories") as { items: CostCategory[] }).items, natures.items) ??
  []
).slice(0, 2);

/** The calendars, the thirty-nine-hour week deactivated among them. */
const CALENDAR_CHOICES: Choice[] = calendars.items.map((calendar) => ({
  id: calendar.calendar_id,
  label: calendar.label,
  active: calendar.is_active,
}));

/** The node of an example by its code. */
function nodeOf(code: string): OrgNode {
  const found = tree.find((node) => node.code === code);
  if (found === undefined) {
    throw new Error(`the tree holds ${code}`);
  }
  return found;
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({
    [NODES]: { example: "org_node_created", status: 201 },
    [NODE]: "org_node_updated",
    [NODE_ACTIVATION]: { example: "org_node_deactivated", status: 200 },
    [ROLES]: { example: "resource_role_created", status: 201 },
    [ROLE]: "resource_role_updated",
    [ROLE_ACTIVATION]: { example: "resource_role_deactivated", status: 200 },
    [CALENDARS]: { example: "calendar_created", status: 201 },
    [CALENDAR]: "calendar_updated",
    [DEFAULT]: "calendar_default",
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

/** The tree of the organisation, the active nodes alone unless told, for who may write. */
function organisation(
  rows: readonly OrgNode[] = tree.filter((node) => node.is_active),
  nodes: readonly NodeOffered[] = NODE_CHOICES,
) {
  return inFrench(
    <OrgNodeList
      rows={rows}
      query={NO_QUERY}
      preferences={undefined}
      readsInactive
      editable
      filters={{ code: undefined, level: undefined, state: undefined, levels: NO_BOUNDS }}
      levels={[1, 2, 3]}
      nodes={nodes}
    />,
  );
}

/**
 * The roles of the witness, for a session that may write them or not, the categories of labour as
 * the page read them — none when it could not read them.
 */
function roleList(editable = true, categoriesRead = true) {
  const labour = categoriesRead ? LABOUR : undefined;
  return inFrench(
    <ResourceRoleList
      rows={roles.items}
      page={roles.meta}
      query={NO_QUERY}
      preferences={undefined}
      readsInactive
      editable={editable}
      nodes={NODE_CHOICES}
      categories={labour}
      labour={labour}
      calendars={CALENDAR_CHOICES}
      filters={{
        orgNode: undefined,
        category: undefined,
        calendar: undefined,
        state: undefined,
        monthlyHours: NO_BOUNDS,
        headcount: NO_BOUNDS,
      }}
    />,
  );
}

/** The calendars, the active ones, for a session that may write them or not. */
function calendarList(editable = true) {
  return inFrench(
    <CalendarList
      rows={calendars.items.filter((calendar) => calendar.is_active)}
      page={calendars.meta}
      query={NO_QUERY}
      preferences={undefined}
      readsInactive
      editable={editable}
      state={undefined}
      hours={
        Object.fromEntries(
          ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map(
            (day) => [day, NO_BOUNDS],
          ),
        ) as DayBounds
      }
    />,
  );
}

/** The calls the lists made of the fake back. */
function writes(client: FakeClient) {
  return client.calls.map(({ route, path, body }) => ({ route, path, body }));
}

/** The row of a grid of the screen by the label it shows, a dialog open over it or not. */
function rowOf(label: string): HTMLElement {
  const found = [...document.querySelectorAll<HTMLElement>("tbody tr")].find((row) =>
    row.querySelector('td[data-column="label"]')?.textContent.includes(label),
  );
  if (found === undefined) {
    throw new Error(`no row shows ${label}`);
  }
  return found;
}

/** What the regions of the screen announce. */
function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The texts of the options of a choice. */
function options(choice: HTMLElement): (string | null)[] {
  return within(choice)
    .getAllByRole("option")
    .map((option) => option.textContent);
}

/** Open a dialog by the command named, and give it back by its name. */
async function opened(command: string, name: string): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: command }));
  return screen.getByRole("dialog", { name });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  refresh.mockClear();
  router.refresh.mockClear();
});

describe("the organisation", () => {
  it("creates a node under an active parent, each offered in the order of the tree set in by its depth, and reads the page anew [WF-REF-0070-A]", async () => {
    const client = serve();
    render(organisation());
    const form = await opened("Nouveau nœud", "Nouveau nœud d’organisation");
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    // An active node takes place under an active one alone: the office of automation is not offered.
    expect(options(parent)).toEqual([
      "Aucun — racine",
      "DT · Direction technique",
      " BE-ELEC · Bureau d'études électricité",
      "  AT-CABL · Atelier de câblage",
      " ACHATS · Service des achats",
    ]);
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), " BE-MECA ");
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      "Bureau d'études mécanique",
    );
    await userEvent.selectOptions(parent, "DT · Direction technique");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)).toEqual([
      {
        route: NODES,
        path: "/reference/org-nodes",
        body: {
          code: "BE-MECA",
          label: "Bureau d'études mécanique",
          parent_id: nodeOf("DT").org_node_id,
        },
      },
    ]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(announced()).toContain("« Bureau d'études mécanique » créé.");
  });

  it("creates a root when no parent is chosen", async () => {
    const client = serve();
    render(organisation());
    const form = await opened("Nouveau nœud", "Nouveau nœud d’organisation");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "DG");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Direction");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toEqual({ code: "DG", label: "Direction", parent_id: null });
  });

  it.each([
    // The technical direction, which the tree names.
    [
      "01926f3a-7c00-7000-8000-000000000470",
      "Déjà porté par «\u00a0DT · Direction technique\u00a0».",
    ],
    // A node the tree read does not hold.
    ["01926f3a-7c00-7000-8000-000000000499", "Déjà porté par un autre nœud."],
  ])(
    "says at the code the refusal of a code that exists already, naming the node %s that holds it, the form kept to be corrected [WF-REF-0070-A]",
    async (holder, named) => {
      // The envelope of the contract: the field taken, and the node that holds it.
      serve({
        [NODES]: {
          problem: {
            code: "ALREADY_EXISTS",
            status: 409,
            fields: [
              {
                pointer: "/code",
                code: "ALREADY_EXISTS",
                params: { conflicting_object_id: holder },
              },
            ],
          },
        },
      });
      render(organisation());
      const form = await opened("Nouveau nœud", "Nouveau nœud d’organisation");
      const code = within(form).getByRole("textbox", { name: "Code" });
      await userEvent.type(code, "DT");
      await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Doublon");
      await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
      // La création d'un nœud dont le code existe déjà est refusée.
      await vi.waitFor(() => {
        expect(code).toHaveFocus();
      });
      expect(code).toHaveAccessibleDescription(`Cet élément existe déjà. ${named}`);
      expect(code).toHaveValue("DT");
      expect(within(form).queryByRole("alert")).toBeNull();
      expect(refresh).not.toHaveBeenCalled();
    },
  );

  it("says at the parent the refusal of a parent deactivated meanwhile, the parent taking the focus", async () => {
    serve({
      [NODES]: { problem: example("org_node_creation_refused") as Problem & { status: 422 } },
    });
    render(organisation());
    const form = await opened("Nouveau nœud", "Nouveau nœud d’organisation");
    await userEvent.type(within(form).getByRole("textbox", { name: "Code" }), "VIS");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Cellule vision");
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    await userEvent.selectOptions(parent, " BE-ELEC · Bureau d'études électricité");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(parent).toHaveFocus();
    });
    expect(parent).toHaveAccessibleDescription("Cet élément du référentiel est désactivé.");
    expect(within(form).queryByRole("alert")).toBeNull();
  });

  it("moves a node under another, never under itself nor its descendants, from the version read, its row then as the server answers it", async () => {
    const client = serve();
    render(organisation());
    const office = nodeOf("BE-ELEC");
    const form = await opened(
      "Modifier « Bureau d'études électricité »",
      "Modifier « Bureau d'études électricité »",
    );
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    expect(parent).toHaveValue(nodeOf("DT").org_node_id);
    // Neither the office itself nor the workshop under it.
    expect(options(parent)).toEqual([
      "Aucun — racine",
      "DT · Direction technique",
      "\u2003ACHATS · Service des achats",
    ]);
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    // The workshop moved under the direction, as the example of the fake back answers it.
    const workshop = nodeOf("AT-CABL");
    const moved = await opened(
      "Modifier « Atelier de câblage »",
      "Modifier « Atelier de câblage »",
    );
    const workshopParent = within(moved).getByRole("combobox", { name: "Parent" });
    expect(workshopParent).toHaveValue(office.org_node_id);
    await userEvent.selectOptions(workshopParent, "DT · Direction technique");
    await userEvent.click(within(moved).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(writes(client)[0]).toEqual({
      route: NODE,
      path: `/reference/org-nodes/${workshop.org_node_id}`,
      body: {
        code: "AT-CABL",
        label: "Atelier de câblage",
        parent_id: nodeOf("DT").org_node_id,
        lock_version: 1,
      },
    });
    await vi.waitFor(() => {
      expect(announced()).toContain("« Atelier de câblage » enregistré.");
    });
    expect(refresh).toHaveBeenCalledOnce();
    // Its row as the server answers it: on the second level now.
    const row = rowOf("Atelier de câblage");
    expect(row.querySelector('td[data-column="level"]')).toHaveTextContent("2");
  });

  it("tells the modification of a node answered for another one as a failure of the service, the form kept open", async () => {
    const client = serve();
    render(organisation());
    // The example answers the workshop, whatever node was modified.
    const form = await opened(
      "Modifier « Bureau d'études électricité »",
      "Modifier « Bureau d'études électricité »",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Erreur inattendue du service.",
    );
    expect(client.calls).toHaveLength(1);
    expect(announced()).not.toContain("« Atelier de câblage » enregistré.");
    expect(refresh).toHaveBeenCalledOnce();
    expect(rowOf("Atelier de câblage").querySelector('td[data-column="level"]')).toHaveTextContent(
      "3",
    );
  });

  it("offers the deactivated parent of a node the tree read without the deactivated ones, marked, and shows it chosen", async () => {
    serve();
    // `org_is_active=false`: the deactivated nodes alone, under a tree read without them.
    render(
      organisation(
        tree.filter((node) => !node.is_active),
        ACTIVE_NODES,
      ),
    );
    const form = await opened("Modifier « Cellule robotique »", "Modifier « Cellule robotique »");
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    expect(parent).toHaveValue(nodeOf("BE-AUTO").org_node_id);
    // Under the direction, its own parent, as the row of the list names it.
    expect(options(parent)).toEqual([
      "Aucun — racine",
      "DT · Direction technique",
      "\u2003BE-AUTO · Bureau d'études automatismes (désactivé)",
      "\u2003BE-ELEC · Bureau d'études électricité",
      "\u2003\u2003AT-CABL · Atelier de câblage",
      "\u2003ACHATS · Service des achats",
    ]);
    // Chosen a root: the choice changes, and is sent.
    await userEvent.selectOptions(parent, "Aucun — racine");
    expect(parent).toHaveValue("");
  });

  it("offers at the end, set in by nothing, the deactivated parent of a node no row names", async () => {
    serve();
    // The cell alone listed — narrowed by its code —: nothing says where its parent stands.
    render(organisation([nodeOf("CEL-ROBOT")], ACTIVE_NODES));
    const form = await opened("Modifier « Cellule robotique »", "Modifier « Cellule robotique »");
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    expect(parent).toHaveValue(nodeOf("BE-AUTO").org_node_id);
    expect(options(parent).at(-1)).toBe("Bureau d'études automatismes (désactivé)");
  });

  it("offers a deactivated node every node as its parent, the deactivated ones marked", async () => {
    serve();
    render(organisation(tree));
    const form = await opened("Modifier « Cellule robotique »", "Modifier « Cellule robotique »");
    expect(options(within(form).getByRole("combobox", { name: "Parent" }))).toEqual([
      "Aucun — racine",
      "DT · Direction technique",
      " BE-AUTO · Bureau d'études automatismes (désactivé)",
      " BE-ELEC · Bureau d'études électricité",
      "  AT-CABL · Atelier de câblage",
      " ACHATS · Service des achats",
    ]);
  });

  it("says at the parent the refusal of an active node moved under a deactivated one", async () => {
    serve({ [NODE]: { problem: example("org_node_move_refused") as Problem & { status: 422 } } });
    render(organisation());
    const form = await opened("Modifier « Atelier de câblage »", "Modifier « Atelier de câblage »");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    const parent = within(form).getByRole("combobox", { name: "Parent" });
    await vi.waitFor(() => {
      expect(parent).toHaveAccessibleDescription("Cet élément du référentiel est désactivé.");
    });
  });

  it("deactivates a node from the version read, its rows then as the server answers them", async () => {
    const client = serve();
    render(organisation());
    await userEvent.click(
      screen.getByRole("button", { name: "Désactiver « Atelier de câblage »" }),
    );
    expect(
      await screen.findByRole("button", { name: "Réactiver « Atelier de câblage »" }),
    ).toBeInTheDocument();
    expect(writes(client)).toEqual([
      {
        route: NODE_ACTIVATION,
        path: `/reference/org-nodes/${nodeOf("AT-CABL").org_node_id}/activation`,
        body: { is_active: false, lock_version: 1 },
      },
    ]);
    expect(announced()).toContain("« Atelier de câblage » désactivé.");
    // The page is read anew: the roles deactivated with it are the other list's (WF-REF-0080).
    expect(refresh).toHaveBeenCalledOnce();
  });
});

describe("the resource roles", () => {
  it("refuses at its fields the attachments the form requires before asking anything, and a capacity that is no number [WF-REF-0090-A]", async () => {
    const client = serve();
    render(roleList());
    const form = await opened("Nouveau rôle", "Nouveau rôle de ressource");
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      "Dessinateur électricien",
    );
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Heures par mois" }),
      "beaucoup",
    );
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    // La création d'un rôle auquel manque l'un des trois rattachements est refusée.
    const node = within(form).getByRole("combobox", { name: "Nœud d’organisation" });
    expect(node).toHaveFocus();
    expect(node).toHaveAccessibleDescription("Une valeur est requise.");
    for (const name of ["Catégorie de coût", "Calendrier"]) {
      expect(within(form).getByRole("combobox", { name })).toHaveAccessibleDescription(
        "Une valeur est requise.",
      );
    }
    expect(
      within(form).getByRole("textbox", { name: "Heures par mois" }),
    ).toHaveAccessibleDescription("Ce n’est pas un nombre valide.");
    expect(client.calls).toEqual([]);
  });

  it("offers the active nodes, the categories of labour and the active calendars alone [WF-REF-0090-A] [WF-REF-0010-A]", async () => {
    serve();
    render(roleList());
    const form = await opened("Nouveau rôle", "Nouveau rôle de ressource");
    // Son rattachement à une catégorie hors main-d'œuvre ou à un objet désactivé est refusé : none is
    // offered — the office of automation and the thirty-nine-hour week are deactivated.
    expect(options(within(form).getByRole("combobox", { name: "Nœud d’organisation" }))).toEqual([
      "Choisir…",
      "DT · Direction technique",
      " BE-ELEC · Bureau d'études électricité",
      "  AT-CABL · Atelier de câblage",
      " ACHATS · Service des achats",
    ]);
    expect(options(within(form).getByRole("combobox", { name: "Catégorie de coût" }))).toEqual([
      "Choisir…",
      ...LABOUR.map((category) => `${category.code ?? ""} · ${category.label}`),
    ]);
    expect(options(within(form).getByRole("combobox", { name: "Calendrier" }))).toEqual([
      "Choisir…",
      "Semaine de quatre jours",
      "Semaine standard",
    ]);
    await expectAccessible(form);
  });

  it("creates a role with its attachments and its single capacity, the numbers written as the contract writes them [WF-REF-0100-A]", async () => {
    const client = serve();
    render(roleList());
    const form = await opened("Nouveau rôle", "Nouveau rôle de ressource");
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      "Dessinateur électricien",
    );
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Nœud d’organisation" }),
      " BE-ELEC · Bureau d'études électricité",
    );
    const [category] = LABOUR;
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Catégorie de coût" }),
      category?.id ?? "",
    );
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Calendrier" }),
      "Semaine standard",
    );
    // Un rôle ne porte qu'une capacité, sans date de validité.
    await userEvent.type(within(form).getByRole("textbox", { name: "Heures par mois" }), "1 520,5");
    await userEvent.type(within(form).getByRole("textbox", { name: "Effectif" }), "3");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)).toEqual([
      {
        route: ROLES,
        path: "/reference/resource-roles",
        body: {
          label: "Dessinateur électricien",
          org_node_id: nodeOf("BE-ELEC").org_node_id,
          cost_category_id: category?.id,
          calendar_id: "01926f3a-7c00-7000-8000-000000000481",
          capacity: { monthly_hours: "1520.5", headcount: "3" },
        },
      },
    ]);
    expect(announced()).toContain("« Dessinateur électricien » créé.");
  });

  it("says at the node the refusal of a node deactivated meanwhile", async () => {
    serve({
      [ROLES]: { problem: example("resource_role_creation_refused") as Problem & { status: 422 } },
    });
    render(roleList());
    const form = await opened("Nouveau rôle", "Nouveau rôle de ressource");
    await userEvent.type(within(form).getByRole("textbox", { name: "Libellé" }), "Roboticien");
    const node = within(form).getByRole("combobox", { name: "Nœud d’organisation" });
    await userEvent.selectOptions(node, "DT · Direction technique");
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Catégorie de coût" }),
      LABOUR[0]?.id ?? "",
    );
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Calendrier" }),
      "Semaine standard",
    );
    await userEvent.type(within(form).getByRole("textbox", { name: "Heures par mois" }), "520");
    await userEvent.type(within(form).getByRole("textbox", { name: "Effectif" }), "3");
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(node).toHaveFocus();
    });
    expect(node).toHaveAccessibleDescription("Cet élément du référentiel est désactivé.");
  });

  it("modifies a role but its node, which its form names, from the version read, its capacity shown in the language of the reader", async () => {
    const client = serve();
    render(roleList());
    const technician = roles.items.find((role) => role.label === "Technicien de mise en service");
    const form = await opened(
      "Modifier « Technicien de mise en service »",
      "Modifier « Technicien de mise en service »",
    );
    // The node is set at the creation: a role is recreated under another rather than moved.
    expect(within(form).queryByRole("combobox", { name: "Nœud d’organisation" })).toBeNull();
    expect(form).toHaveAccessibleDescription(
      "Le libellé, une catégorie de main-d’œuvre, le calendrier et la capacité sont requis. Le rôle reste sous « Bureau d'études électricité » : il se recrée sous un autre nœud plutôt que de s’y déplacer.",
    );
    expect(within(form).getByRole("textbox", { name: "Heures par mois" })).toHaveValue("485324,00");
    expect(within(form).getByRole("combobox", { name: "Calendrier" })).toHaveValue(
      technician?.calendar_id,
    );
    // Its category, among the labour ones offered, is kept as the row names it.
    expect(within(form).getByRole("combobox", { name: "Catégorie de coût" })).toHaveValue(
      technician?.cost_category_id,
    );
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(writes(client)[0]).toEqual({
      route: ROLE,
      path: `/reference/resource-roles/${technician?.resource_role_id ?? ""}`,
      body: {
        label: "Technicien de mise en service",
        cost_category_id: technician?.cost_category_id,
        calendar_id: technician?.calendar_id,
        capacity: { monthly_hours: "485324.00", headcount: "2800" },
        lock_version: 1,
      },
    });
    await vi.waitFor(() => {
      expect(screen.getByRole("grid", { name: "Rôles de ressources" })).toHaveTextContent(
        "Technicien de mise en service et d'essais",
      );
    });
  });

  it("keeps a deactivated calendar a role is attached to, marked, among the active ones offered", async () => {
    serve();
    render(roleList());
    const form = await opened("Modifier « Automaticien »", "Modifier « Automaticien »");
    expect(options(within(form).getByRole("combobox", { name: "Calendrier" }))).toEqual([
      "Choisir…",
      "Semaine de quatre jours",
      "Semaine standard",
      "Semaine de trente-neuf heures (désactivé)",
    ]);
  });

  it("offers no creation of a role to a session that reads no category, and names the category of a role modified without a mark", async () => {
    serve();
    render(roleList(true, false));
    // A role cannot do without a category of labour, which the session cannot choose.
    expect(screen.queryByRole("button", { name: "Nouveau rôle" })).toBeNull();
    const technician = roles.items.find((role) => role.label === "Technicien de mise en service");
    const form = await opened(
      "Modifier «\u00a0Technicien de mise en service\u00a0»",
      "Modifier «\u00a0Technicien de mise en service\u00a0»",
    );
    const category = within(form).getByRole("combobox", { name: "Catégorie de coût" });
    expect(category).toHaveValue(technician?.cost_category_id);
    // Not read is not deactivated: the category is named as the row names it, without a mark.
    expect(options(category)).toEqual(["Choisir…", technician?.cost_category_label]);
  });

  it("deactivates an active role from its row, its row then as the server answers it", async () => {
    serve();
    render(roleList());
    await userEvent.click(
      screen.getByRole("button", { name: "Désactiver « Ingénieur électricien »" }),
    );
    expect(
      await screen.findByRole("button", { name: "Réactiver « Ingénieur électricien »" }),
    ).toBeInTheDocument();
    expect(announced()).toContain("« Ingénieur électricien » désactivé.");
  });
});

describe("the calendars", () => {
  it("creates a calendar by its seven values of hours, from Monday, and asks nothing else [WF-REF-0110-A]", async () => {
    const client = serve();
    render(calendarList());
    const form = await opened("Nouveau calendrier", "Nouveau calendrier");
    // Un calendrier se saisit par sept valeurs d'heures, du lundi au dimanche, et aucune autre
    // donnée n'est demandée.
    expect(
      within(form)
        .getAllByRole("textbox")
        .map((field) => (field as HTMLInputElement).labels?.[0]?.textContent),
    ).toEqual(["Libellé", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]);
    expect(within(form).queryByRole("combobox")).toBeNull();
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Libellé" }),
      "Semaine de trente-cinq heures",
    );
    for (const day of ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]) {
      await userEvent.type(within(form).getByRole("textbox", { name: day }), "7");
    }
    for (const day of ["Samedi", "Dimanche"]) {
      await userEvent.type(within(form).getByRole("textbox", { name: day }), "0");
    }
    await userEvent.click(within(form).getByRole("button", { name: "Créer" }));
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    expect(writes(client)[0]?.body).toEqual({
      label: "Semaine de trente-cinq heures",
      weekly_hours: {
        monday: "7",
        tuesday: "7",
        wednesday: "7",
        thursday: "7",
        friday: "7",
        saturday: "0",
        sunday: "0",
      },
    });
    expect(announced()).toContain("« Semaine de trente-cinq heures » créé.");
  });

  it("modifies a calendar from the version read, its hours shown in the language of the reader", async () => {
    const client = serve();
    render(calendarList());
    const form = await opened(
      "Modifier « Semaine de quatre jours »",
      "Modifier « Semaine de quatre jours »",
    );
    expect(within(form).getByRole("textbox", { name: "Lundi" })).toHaveValue("10");
    const label = within(form).getByRole("textbox", { name: "Libellé" });
    await userEvent.clear(label);
    await userEvent.type(label, "Semaine de quatre jours de dix heures");
    await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
    await vi.waitFor(() => {
      expect(client.calls).toHaveLength(1);
    });
    expect(client.calls[0]?.body).toMatchObject({
      label: "Semaine de quatre jours de dix heures",
      weekly_hours: { monday: "10", friday: "0" },
      lock_version: 1,
    });
  });

  it("designates an active calendar by default from its row, reads the page anew, and shows the answer in its row", async () => {
    const client = serve();
    render(calendarList());
    // The default calendar is marked, and offers no designation.
    expect(
      screen.queryByRole("button", { name: "Désigner « Semaine standard » par défaut" }),
    ).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Désigner « Semaine de quatre jours » par défaut" }),
    );
    await vi.waitFor(() => {
      expect(refresh).toHaveBeenCalledOnce();
    });
    // Withdrawing the designation from the one before is the server's: the page read anew shows it.
    expect(writes(client)).toEqual([
      {
        route: DEFAULT,
        path: "/reference/calendars/01926f3a-7c00-7000-8000-000000000482/default",
        body: { lock_version: 1 },
      },
    ]);
    expect(announced()).toContain("« Semaine de quatre jours » désigné calendrier par défaut.");
    const row = document.querySelector('td[data-row="0"][data-column="is_default"]');
    expect(row).toHaveTextContent("Calendrier par défaut");
  });

  it("says the refusal of a designation above the list, the row as the page read it", async () => {
    serve({ [DEFAULT]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    render(calendarList());
    await userEvent.click(
      screen.getByRole("button", {
        name: "Désigner «\u00a0Semaine de quatre jours\u00a0» par défaut",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération.",
    );
    expect(refresh).not.toHaveBeenCalled();
    expect(document.querySelector('td[data-row="0"][data-column="is_default"]')).toHaveTextContent(
      "Désigner",
    );
  });

  it("presents the deactivation of the default calendar unavailable, with its condition [WF-REF-0120-A]", async () => {
    const client = serve();
    render(calendarList());
    // La désactivation du calendrier par défaut est refusée tant qu'un autre n'a pas été désigné.
    const command = screen.getByRole("button", {
      name: "Désactiver « Semaine standard »",
    });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      "Condition non remplie : calendrier autre que celui par défaut.",
    );
    await userEvent.click(command);
    expect(client.calls).toEqual([]);
  });
});

describe("a session that may only read the settings of the resources", () => {
  it("is offered neither creation, modification nor designation, and no screen offers to delete [WF-IHM-0090-A] [WF-REF-0010-A]", () => {
    serve();
    render(
      <>
        {roleList(false)}
        {calendarList(false)}
      </>,
    );
    expect(screen.queryByRole("button", { name: /^(Nouveau|Modifier|Désigner)/ })).toBeNull();
    // Aucun écran ne propose de supprimer un objet du référentiel.
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
  });

  it("is offered no deletion either when it may write [WF-REF-0010-A]", () => {
    serve();
    render(
      <>
        {organisation(tree)}
        {roleList()}
        {calendarList()}
      </>,
    );
    expect(screen.getAllByRole("button", { name: /^Nouveau/ })).toHaveLength(3);
    expect(screen.queryByRole("button", { name: /Supprimer/ })).toBeNull();
  });
});
