// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grids and the gestures shared by the tests of the submenus « Chronologies » and « Sous-projet »
 * of the menu of a cell (US-0480): the planning, the estimate and the remaining to commit rendered
 * on the examples, their variants, and how a test opens a menu and selects rows. Each test file
 * mocks the server of Next itself, on the holders exported here, and serves its own fake back.
 */
import { act, fireEvent, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import { EstimateGrid } from "@/components/grid/estimate-grid";
import type { NodeList, NodeSortColumn } from "@/components/grid/nodes";
import { PlanningGrid } from "@/components/grid/planning-grid";
import type { GridQuery } from "@/components/grid/query";
import { RemainingGrid } from "@/components/grid/remaining-grid";
import type { ChoiceOption } from "@/components/grid/row-choices";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";

import {
  example,
  type FakeAnswers,
  type FakeClient,
  type FakeTiming,
  fakeClient,
} from "./fixtures";
import { SHOWN } from "./grid-preferences";
import { estimateReference } from "./reference";

export { SHOWN };

/** What the mocks of `@/api/server` and `next/navigation` of a test file read. */
export const server: { client: ApiClient | undefined } = { client: undefined };
export const router = { push: vi.fn(), refresh: vi.fn() };

export type Timeline = components["schemas"]["Timeline"];
export type Subproject = components["schemas"]["Subproject"];
export type NodesWritten = components["schemas"]["NodesWritten"];

export const NO_QUERY: GridQuery<NodeSortColumn> = {
  sort: undefined,
  search: undefined,
  size: undefined,
};
export const NODES =
  "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
export const TRACKING = `PUT ${NODES}/{node_id}/tracking` as const;
export const LINE = `PATCH ${NODES}/{node_id}/estimate-line` as const;
export const TIMELINES = "POST /projects/{project_id}/timelines" as const;
export const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
export const STEERING = "01926f3a-7c00-7000-8000-000000001000";
export const CUSTOMER = "01926f3a-7c00-7000-8000-000000001001";
export const COMMAND = "01926f3a-7c00-7000-8000-000000000801";
export const TESTS = "01926f3a-7c00-7000-8000-000000000802";

export const planning = example("nodes_planning") as NodeList;
export const estimate = example("nodes_estimate") as NodeList;
export const timelines: readonly ChoiceOption[] = (example("timelines") as Timeline[]).map(
  (each) => ({
    id: each.timeline_id,
    label: each.label,
  }),
);
export const subprojects = (example("subprojects") as Subproject[]).map((each) => ({
  id: each.subproject_id,
  label: each.label,
  code: each.code,
}));

/** The index of a row of an answer, by its label (#400). */
export function indexOf(nodes: NodeList, label: string): number {
  return nodes.items.findIndex((each) => (each.task?.label ?? each.estimate_line?.label) === label);
}

/** What the project lists of `manage_timelines` when the caller may create a timeline. */
export const AVAILABLE: CommandOffer = { is_available: true, missing_conditions: [] };

export const [STUDIES, DETAIL, , REVIEW, MILESTONE] = [0, 1, 2, 3, 4];
export const LABOUR = indexOf(estimate, "Raccordement des borniers");
export const PROVISION = indexOf(estimate, "Provision — risque de reprise du câblage");
export const REMINDER = indexOf(estimate, "Frais de relance");
export const FREIGHT = indexOf(estimate, "Affrètement");
export const THREE = [LABOUR, indexOf(estimate, "Borniers"), REMINDER] as const;

/**
 * The estimate with three lines that name their sub-project (a variant, never served as an answer):
 * the labour and the terminals, which are made to name it, and the reminder, which names it already;
 * the first two bear « Poste de commande », the third none.
 */
export function threeLines(): NodeList {
  const read = structuredClone(estimate);
  // The provision is a computed line: it never names its sub-project, and the selection leaves it aside.
  for (const index of [THREE[0], THREE[1]]) {
    read.items[index]?.editable_fields.push("estimate_line.subproject_id");
  }
  const third = read.items[THREE[2]]?.estimate_line;
  if (third === undefined || third === null) {
    throw new Error("the example holds no such line");
  }
  third.subproject_id = null;
  return read;
}

/** Serve the fake back, and give it back to read its calls. */
export function serve(answers: FakeAnswers = {}, timing?: FakeTiming): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

export const intl = (children: React.ReactNode) => (
  <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
    {children}
  </NextIntlClientProvider>
);

/** The grid of the planning, entered, its timelines given or refused. */
export function planningGrid(
  nodes: NodeList = planning,
  {
    named = timelines,
    editable = true,
    creation = AVAILABLE,
  }: {
    named?: readonly ChoiceOption[] | null;
    editable?: boolean;
    creation?: CommandOffer | null;
  } = {},
) {
  return intl(
    <PlanningGrid
      nodes={nodes}
      structure={STRUCTURE}
      structureVersion={1}
      filters={{ kinds: ["task"] }}
      query={NO_QUERY}
      preferences={SHOWN}
      undoable={editable}
      editable={editable}
      timelines={named ?? undefined}
      timelineCreation={creation ?? undefined}
    />,
  );
}

/** The grid of the estimate, entered or not. */
export function estimateGrid(
  nodes: NodeList = estimate,
  editable = true,
  preferences: GridPreferences | null = SHOWN,
) {
  return intl(
    <EstimateGrid
      nodes={nodes}
      structure={STRUCTURE}
      structureVersion={1}
      reference={estimateReference()}
      editable={editable}
      tasksEditable={editable}
      query={NO_QUERY}
      filters={{}}
      preferences={preferences ?? undefined}
    />,
  );
}

/** The grid of the remaining to commit, its sub-projects given or not. */
export function remainingGrid(offered: readonly ChoiceOption[] | null = subprojects) {
  return intl(
    <RemainingGrid
      nodes={estimate}
      structure={STRUCTURE}
      structureVersion={1}
      filters={{ progress: ["started"] }}
      editable
      subprojects={offered ?? undefined}
      query={NO_QUERY}
      preferences={SHOWN}
    />,
  );
}

/** A cell of the row at an index, by its column. */
export function cellAt(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** Open the menu of the cell of a row's label, by a right click. */
export async function openMenu(row: number): Promise<HTMLElement> {
  fireEvent.contextMenu(cellAt(row, "label"), { clientX: 300, clientY: 200 });
  return screen.findByRole("menu", { name: "Menu de la cellule" });
}

/** Open a submenu of the menu of a row. */
export async function openSubmenu(row: number, name: string): Promise<HTMLElement> {
  const menu = await openMenu(row);
  await userEvent.click(within(menu).getByRole("menuitem", { name }));
  return screen.findByRole("menu", { name });
}

/** Select the rows from one to another by their handles. */
export async function select(from: number, to: number) {
  fireEvent.click(cellAt(from, "row_number"));
  fireEvent.click(cellAt(to, "row_number"), { shiftKey: true });
  await act(async () => {
    await Promise.resolve();
  });
}

/** The bodies sent on a route, in order. */
export function sent(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

/** Start each test of a file on a clean session, with a grid the size of a screen. */
export function prepareMenuTests(forgetMessages: () => void): void {
  beforeEach(() => {
    window.sessionStorage.clear();
    forgetMessages();
    router.refresh.mockReset();
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
}
