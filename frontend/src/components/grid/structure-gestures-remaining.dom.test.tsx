// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient, type Problem } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { RemainingGrid } from "./remaining-grid";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const DELETE =
  "DELETE /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}" as const;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;
const REMAINING_LINK = { name: "Mettre son reste à engager à zéro" };
const REMAINING = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/remaining`;

/** Each grid, with a task started, a summary refused for a subordinate started, a task completed. */
const GRIDS = [
  ["estimate", "Câblage des armoires", "Poste de commande", "Relance du fournisseur"],
  ["remaining to commit", "Câblage des armoires", "Poste de commande", "Relance du fournisseur"],
  ["planning", "Pupitres opérateurs", "Études", "Revue de conception"],
] as const;

function grid(name: (typeof GRIDS)[number][0]) {
  const common = {
    structure: STRUCTURE,
    structureVersion: 1,
    query: NO_QUERY,
    preferences: undefined,
  };
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {name === "estimate" ? (
        <EstimateGrid
          {...common}
          nodes={estimate}
          reference={estimateReference()}
          editable
          tasksEditable
          filters={{}}
        />
      ) : name === "planning" ? (
        <PlanningGrid
          {...common}
          nodes={planning}
          filters={{ kinds: ["task"] }}
          undoable
          editable
        />
      ) : (
        <RemainingGrid
          {...common}
          nodes={estimate}
          filters={{ progress: ["started"] }}
          editable
          categories={estimateReference().categories ?? []}
        />
      )}
    </NextIntlClientProvider>
  );
}

/** Ask the deletion of a task by its label, refused as started, and give the alert that tells it. */
async function refused(name: (typeof GRIDS)[number][0], label: string): Promise<HTMLElement> {
  server.client = fakeClient({
    [DELETE]: { problem: example("node_delete_started_refused") as Problem & { status: 409 } },
  });
  render(grid(name));
  const nodes = name === "planning" ? planning : estimate;
  const row = nodes.items.findIndex((item) => item.task?.label === label);
  const cell = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="label"]`);
  if (cell === null) {
    throw new Error(`no label for ${label}`);
  }
  fireEvent.contextMenu(cell, { clientX: 300, clientY: 200 });
  const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
  await userEvent.click(within(menu).getByRole("menuitem", { name: "Supprimer" }));
  // A summary asks its confirmation first.
  const dialog = screen.queryByRole("dialog");
  if (dialog !== null) {
    await userEvent.click(within(dialog).getByRole("button", { name: "Supprimer" }));
  }
  return screen.findByRole("alert");
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

// La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers la mise à zéro
// de son reste à engager: the refusal `task_not_started` leads to a line that can be zeroed.
describe("the refusal to delete a task started, in the grids of the structure [WF-PLA-0070-A]", () => {
  it.each(GRIDS)(
    "refers a task started of the grid of the %s to its line in the remaining to commit",
    async (name, started) => {
      const alert = await refused(name, started);
      expect(within(alert).getByRole("link", REMAINING_LINK)).toHaveAttribute(
        "href",
        `${REMAINING}?${new URLSearchParams({ search: started }).toString()}`,
      );
    },
  );

  it.each(GRIDS)(
    "refers a summary task of the grid of the %s to the tasks started and completed, none searched, whichever subordinate caused the refusal",
    async (name, _, summary) => {
      const alert = await refused(name, summary);
      expect(within(alert).getByRole("link", REMAINING_LINK)).toHaveAttribute(
        "href",
        `${REMAINING}?${new URLSearchParams({ progress: "started,completed" }).toString()}`,
      );
    },
  );

  it.each(GRIDS)(
    "refers a task completed of the grid of the %s to no line: it is not re-estimated",
    async (name, _, __, completed) => {
      const alert = await refused(name, completed);
      expect(alert).toHaveTextContent("Condition non remplie");
      expect(within(alert).queryByRole("link", REMAINING_LINK)).toBeNull();
    },
  );
});
