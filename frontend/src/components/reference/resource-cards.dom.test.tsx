// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources in their cards (EP-25, US-2110/L1): the creation of a node, of a
 * role and of a calendar filled at the right of the title of its card, the one filled command of
 * the card, offered on an empty list too; the modification of the units of duration outlined at the
 * right of the title of its card; the bar of the tree in the order of every grid.
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import { expectCommandRule } from "@/test/command-rule";
import { example, fakeClient } from "@/test/fixtures";

import type { Calendar, OrgNode, ResourceRole } from "./resource-grids";
import {
  CalendarList,
  DurationUnitFacts,
  type NodeOffered,
  OrgNodeList,
  ResourceRoleList,
} from "./resource-lists";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY = { sort: undefined, search: undefined, size: undefined };
const NO_BOUNDS = { min: undefined, max: undefined };
const nodeRows = example("org_nodes") as OrgNode[];
const roles = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };
const calendars = example("calendars") as { items: Calendar[]; meta: ListPage };
const units = example("duration_units") as components["schemas"]["DurationUnits"];

const NODES: NodeOffered[] = nodeRows.map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
  active: node.is_active,
}));
const LABOUR = [{ id: "labour", code: "MO", label: "Main-d’œuvre", active: true }];
const CREATIONS = [
  ["Arbre d’organisation", "Nouveau nœud"],
  ["Rôles de ressources", "Nouveau rôle"],
  ["Calendriers", "Nouveau calendrier"],
] as const;

/** The empty page of a list the server pages. */
const NONE: ListPage = { ...roles.meta, offset: 0, total: 0 };

/** The four sections of the screen, in French, for a session that writes or reads, empty or not. */
function screenOf({ empty = false, editable = true } = {}) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <OrgNodeList
          rows={empty ? [] : nodeRows.filter((node) => node.is_active)}
          query={NO_QUERY}
          preferences={undefined}
          editable={editable}
          filters={{ code: undefined, level: undefined, state: undefined, levels: NO_BOUNDS }}
          levels={[1, 2, 3]}
          nodes={NODES}
        />
        <ResourceRoleList
          rows={empty ? [] : roles.items}
          page={empty ? NONE : roles.meta}
          query={NO_QUERY}
          preferences={undefined}
          editable={editable}
          nodes={NODES}
          categories={LABOUR}
          labour={LABOUR}
          calendars={[]}
          filters={{
            code: undefined,
            orgNode: undefined,
            category: undefined,
            calendar: undefined,
            state: undefined,
            monthlyHours: NO_BOUNDS,
            headcount: NO_BOUNDS,
          }}
        />
        <CalendarList
          rows={empty ? [] : calendars.items}
          page={empty ? NONE : calendars.meta}
          query={NO_QUERY}
          preferences={undefined}
          editable={editable}
          state={undefined}
        />
        <DurationUnitFacts units={units} editable={editable} />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The card of a section, by its title. */
function card(title: string): HTMLElement {
  return screen.getByRole("region", { name: title });
}

/** Whether a button is drawn filled. */
function filled(button: HTMLElement): boolean {
  return button.className === cn(buttonVariants({ variant: "default", size: "sm" }));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the cards of the settings of the resources", () => {
  it.each(CREATIONS)(
    "sets the creation of « %s » at the right of the title of its card, filled, before its table [WF-IHM-0100-A]",
    (title, creation) => {
      render(screenOf());
      const section = card(title);
      expect(section).toHaveAttribute("data-slot", "section-card");
      const button = within(section).getByRole("button", { name: creation });
      expect(filled(button)).toBe(true);
      const header = section.querySelector('[data-slot="card-header"]');
      expect(header?.contains(button)).toBe(true);
      expect(header?.contains(within(section).getByRole("heading", { level: 2 }))).toBe(true);
      expect(button.closest("[data-grid-toolbar]")).toBeNull();
      const table = section.querySelector('[role="grid"], [role="treegrid"]');
      expect(table).not.toBeNull();
      expect(
        button.compareDocumentPosition(table ?? button) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    },
  );

  it("sets « Modifier les unités de durée » at the right of the title of its card, outlined [WF-IHM-0100-A]", () => {
    render(screenOf());
    const section = card("Unités de durée");
    const button = within(section).getByRole("button", { name: "Modifier les unités de durée" });
    expect(filled(button)).toBe(false);
    expect(button.className).toContain("border");
    const header = section.querySelector('[data-slot="card-header"]');
    expect(header?.contains(button)).toBe(true);
    expect(header?.contains(within(section).getByRole("heading", { level: 2 }))).toBe(true);
    expect(button.closest('[data-slot="section-card-principal"]')).toHaveAttribute(
      "data-does",
      "modify",
    );
  });

  it("keeps the rule of the commands: one filled creation in each list, nothing filled in the units [WF-IHM-0100-A]", () => {
    const { container } = render(screenOf());
    expectCommandRule(container);
    for (const [title] of CREATIONS) {
      const commands = within(card(title))
        .getAllByRole("button")
        .filter((button) => button.className.includes("bg-primary"));
      expect(commands).toHaveLength(1);
    }
    expect(
      within(card("Unités de durée"))
        .getAllByRole("button")
        .filter((button) => button.className.includes("bg-primary")),
    ).toHaveLength(0);
  });

  it("keeps the creation of an empty list at the right of its title, in its card [WF-IHM-0100-A]", () => {
    const { container } = render(screenOf({ empty: true }));
    for (const [title, creation] of CREATIONS) {
      const section = card(title);
      expect(section.querySelector('[role="grid"], [role="treegrid"]')).toBeNull();
      const button = within(section).getByRole("button", { name: creation });
      expect(section.querySelector('[data-slot="card-header"]')?.contains(button)).toBe(true);
    }
    expectCommandRule(container);
  });

  it("offers a session that only reads no command, and shows the units as figures [WF-IHM-0100-A]", () => {
    const { container } = render(screenOf({ editable: false }));
    expect(container.querySelector('[data-slot="section-card-principal"]')).toBeNull();
    expect(screen.queryByRole("button", { name: "Modifier les unités de durée" })).toBeNull();
    expect(within(card("Unités de durée")).getByText("Heures par jour")).toBeVisible();
    expectCommandRule(container);
  });

  it("puts the bar of the tree in the order of every grid: the filters, the columns, then the tree [WF-IHM-0100-A]", () => {
    render(screenOf());
    const columns = within(card("Arbre d’organisation")).getByRole("button", {
      name: /^Colonnes/,
    });
    const bar = columns.closest("[data-grid-toolbar]");
    const controls = Array.from(bar?.querySelectorAll("button") ?? []);
    const at = (pattern: RegExp) =>
      controls.findIndex((control) => pattern.test(control.textContent));
    expect(at(/Filtres/)).toBeGreaterThanOrEqual(0);
    expect(at(/Colonnes/)).toBeGreaterThan(at(/Filtres/));
    expect(at(/Arbre/)).toBeGreaterThan(at(/Colonnes/));
  });

  it("breaks no rule of accessibility [WF-IHM-0100-A]", async () => {
    const { container } = render(screenOf());
    await expectAccessible(container);
  });
});
