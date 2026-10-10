// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the estimate a block is pasted on, for the tests of the paste (WF-IHM-0050): twelve
 * rows of the structure the fake back serves, the block of the examples, and how a test pastes it
 * and reads the grid back. Each test file mocks the server of Next itself and serves its own fake
 * back: what is shared here is data and gestures.
 */
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";

import { EstimateGrid } from "@/components/grid/estimate-grid";
import type { NodeList, NodeSortColumn, NodesWritten } from "@/components/grid/nodes";
import type { GridSort } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { CATALOGUES } from "@/i18n/catalogues";

import { example, type FakeClient } from "./fixtures";
import { estimateReference } from "./reference";

export const PREVIEW =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview";
export const APPLY =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste";
export const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
// The main structure of the current revision of the witness project, and its version, as
// `listCostStructures` gives them.
export const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
export const STRUCTURE_VERSION = 1;
export const NODES = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/structures/${STRUCTURE.structure_id}/nodes`;

// Twelve rows of the structure the fake back serves, from the first phase drawn after the core:
// the phase, its lot, its first task, then its lines « Heures d'ingénierie », « Heures de mise en
// service » and « Matériel », on which the rows applied of the examples land (`paste_applied`),
// found by their identifiers in the examples, never by a number written here (#400).
const volume = example("volume/nodes_thousand") as NodeList;
export const LINE_4 = (example("paste_applied") as NodesWritten).nodes[0]?.node_id ?? "";
export const FIRST = 3;
const START = volume.items.findIndex((node) => node.node_id === LINE_4) - FIRST;
export const nodes: NodeList = { ...volume, items: volume.items.slice(START, START + 12) };
// The number of the first line written, as the structure numbers it.
export const ROW = nodes.items[FIRST]?.row_number ?? 0;

// A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
// copies it; the same, its second row naming a category the reference does not know.
export const BLOCK = [
  ["Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"],
  ["Heures d'essais", "Mise en service", "Technicien de mise en service", "1"],
  ["Matériel de câblage", "Matériel électrique", "", "24"],
];
export const UNKNOWN = [BLOCK[0] ?? [], ["Heures d'essais", "Essais", "", "1"], BLOCK[2] ?? []];

/** The labels of the rows 4 to 6, as the grid reads them before any paste. */
export const READ = ["Heures d'ingénierie", "Heures de mise en service", "Matériel"];

/** A block as the clipboard holds it: tab-separated values, each row ended. */
export function copied(block: readonly (readonly string[])[]): string {
  return block.map((row) => `${row.join("\t")}\n`).join("");
}

/** What a reading asked besides the rows, and the rows it answered. */
export interface Reading {
  readonly nodes: NodeList;
  readonly search?: string;
  readonly sort?: GridSort<NodeSortColumn>;
}

/**
 * The grid of the estimate on the rows, open to entry or not, with the settings kept if any — or on
 * the rows a reading answered, searched or sorted.
 */
export function renderGrid(editable = true, preferences?: GridPreferences, reading?: Reading) {
  const search = reading?.search;
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={search === undefined ? {} : { search }}
        nodes={reading?.nodes ?? nodes}
        structure={STRUCTURE}
        structureVersion={STRUCTURE_VERSION}
        reference={estimateReference()}
        editable={editable}
        tasksEditable
        query={{ sort: reading?.sort, search }}
        preferences={preferences}
      />
    </NextIntlClientProvider>,
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
export function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid", { hidden: true })
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The labels of the rows 4 to 6. */
export function labels(): string[] {
  return [0, 1, 2].map((offset) => cell(FIRST + offset, "label").textContent);
}

/** Paste a block on a cell, as the browser hands it at the event `paste`. */
export async function pasteOn(target: HTMLElement, text: string): Promise<void> {
  target.focus();
  await userEvent.paste(text);
}

/** The bodies a route was called with. */
export function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}
