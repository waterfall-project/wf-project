// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { SHOWN } from "@/test/grid-preferences";
import { spokenText } from "@/test/menu";
import { APPLY, bodies, copied, PREVIEW, STRUCTURE } from "@/test/paste-grid";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";

// What a comparison leaves of the entry of a grid (WF-IHM-0150, US-2340): the line a comparison
// removes is read in its place, and no gesture of structure acts on it nor, where it would reach it,
// around it; a block pasted on it is for the server to refuse, whole, with its reason. The server
// of Next, as far as the grid needs it, as for the other tests.
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
const NODES = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const WRITES: readonly string[] = [
  `POST ${NODES}`,
  `DELETE ${NODES}/{node_id}`,
  `POST ${NODES}/move`,
];

// The current revision of the witness compared to its reference: the line of the provision, its last
// row, is removed (« Mise en service sur site » is the line before it, « Mise en service » its task).
const comparison = example("comparison_current") as NodeList;
const REMOVED = comparison.items.findIndex((node) => node.difference === "removed");
const BEFORE = REMOVED - 1;
const TASK = comparison.items.findIndex((node) => node.task?.label === "Mise en service");
const SIBLING = comparison.items.findIndex(
  (node) => node.task?.label === "Montage des armoires sur site",
);
// The same comparison, the task above « Mise en service » removed: the one it would be indented under.
const withTaskRemoved: NodeList = {
  ...comparison,
  items: comparison.items.map((node, index) =>
    index === SIBLING ? { ...node, difference: "removed" } : node,
  ),
};

/** Serve the fake back, and give it back to read its calls. */
function serve(
  preview:
    | "paste_plan_amendment_skipping"
    | "paste_plan_amendment_target_removed" = "paste_plan_amendment_skipping",
): FakeClient {
  const client = fakeClient({
    [PREVIEW]: preview,
    [APPLY]: "paste_applied_amendment_skipping",
  });
  server.client = client;
  return client;
}

/** The grid of the estimate on a comparison, entered. */
function comparedGrid(nodes: NodeList) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable
        tasksEditable
        query={NO_QUERY}
        filters={{}}
        preferences={SHOWN}
        comparing
      />
    </NextIntlClientProvider>
  );
}

/** The cell of the label of the row at an index. */
function labelAt(row: number): HTMLElement {
  const found = screen
    .getByRole("treegrid", { hidden: true })
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="label"]`);
  if (found === null) {
    throw new Error(`no label for the row ${row.toString()}`);
  }
  return found;
}

/** Make a row the active one, as a click on its label does. */
async function activate(row: number): Promise<void> {
  await act(async () => {
    labelAt(row).focus();
    await Promise.resolve();
  });
}

/** The gestures of structure the menu of a row offers, by name; the menu is closed after. */
async function gestures(row: number): Promise<{ names: string[]; disabled: string[] }> {
  fireEvent.contextMenu(labelAt(row), { clientX: 300, clientY: 200 });
  const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
  const items = within(menu)
    .queryAllByRole("menuitem")
    .filter((item) =>
      /Insérer|Supprimer|Monter|Descendre|Indenter|Désindenter/.test(spokenText(item)),
    );
  const names = items.map((item) => spokenText(item).trim());
  const disabled = items
    .filter((item) => item.getAttribute("aria-disabled") === "true")
    .map((item) => spokenText(item).trim());
  await userEvent.keyboard("{Escape}");
  return { names, disabled };
}

/** What the fake back was asked to write: a creation, a deletion, a move. */
function written(client: FakeClient): string[] {
  return client.calls.map((call) => call.route).filter((route) => WRITES.includes(route));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("a block pasted on a comparison", () => {
  it("asks the plan of a block pasted on the line removed, and presents the refusal of the server, whole, with its reason [WF-IHM-0150-A]", async () => {
    const client = serve("paste_plan_amendment_target_removed");
    render(comparedGrid(comparison));
    const block = [["Provision revue"]];
    labelAt(REMOVED).focus();
    await userEvent.paste(copied(block));
    // The refusal (PASTE_TARGET_REMOVED, whole) is the server's, as the contract exemplifies it: the
    // grid asks the plan and presents it, the reason and nothing accepted.
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(dialog).toBeVisible();
    expect(dialog).toHaveTextContent("La cible du collage a disparu entre-temps");
    expect(dialog).toHaveTextContent("Ligne 1 du bloc");
    // Whole refusal: nothing accepted, so the dialog says no line will be written and offers no way
    // to apply (the button is not rendered when plan.accepted is 0).
    expect(dialog).toHaveTextContent("Aucune ligne ne sera écrite.");
    expect(within(dialog).queryByRole("button", { name: "Appliquer le collage" })).toBeNull();
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: comparison.items[REMOVED]?.node_id, target_column: "label", rows: block },
    ]);
    expect(bodies(client, APPLY)).toEqual([]);
  });

  it("is pasted on the line before it, the removed line skipped as on a differential: the plan is asked from that line [WF-IHM-0150-A]", async () => {
    const client = serve();
    render(comparedGrid(comparison));
    const block = [["Mise en service revue"], ["Provision revue"]];
    labelAt(BEFORE).focus();
    await userEvent.paste(copied(block));
    expect(await screen.findByRole("dialog", { name: "Coller depuis un tableur" })).toBeVisible();
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: comparison.items[BEFORE]?.node_id, target_column: "label", rows: block },
    ]);
    // Nothing is applied before the confirmation, and the removed line is not a target of it.
    expect(bodies(client, APPLY)).toEqual([]);
  });
});

describe("the gestures of structure on a comparison", () => {
  it("offers none on the line removed, and takes no key of structure on it [WF-IHM-0150-A]", async () => {
    const client = serve();
    render(comparedGrid(comparison));
    expect((await gestures(REMOVED)).names).toEqual([]);
    await activate(REMOVED);
    await userEvent.keyboard(
      "{Insert}{Alt>}{Insert}{/Alt}{Control>}{Insert}{Delete}{/Control}" +
        "{Alt>}{Shift>}{ArrowRight}{ArrowLeft}{ArrowUp}{ArrowDown}{/Shift}{/Alt}",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(written(client)).toEqual([]);
  });

  it("offers the line before it its own gestures, but not to move down onto the line removed [WF-IHM-0150-A]", async () => {
    const client = serve();
    render(comparedGrid(comparison));
    const { names, disabled } = await gestures(BEFORE);
    expect(names).toContain("Supprimer");
    expect(names.some((name) => name.startsWith("Insérer"))).toBe(true);
    // The line removed is no sibling to take its place: moving down onto it is not offered.
    expect(names.filter((name) => !disabled.includes(name))).not.toContain("Descendre");
    await activate(BEFORE);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowDown}{/Shift}{/Alt}");
    expect(written(client)).toEqual([]);
  });

  it("does not indent, nor move up, a task under or onto a task removed [WF-IHM-0150-A]", async () => {
    const client = serve();
    render(comparedGrid(withTaskRemoved));
    // The task removed offers nothing, and the task after it is neither indented under it nor moved
    // up over it; it may still be given a sibling below.
    expect((await gestures(SIBLING)).names).toEqual([]);
    const { names, disabled } = await gestures(TASK);
    const usable = names.filter((name) => !disabled.includes(name));
    expect(usable).not.toContain("Indenter");
    expect(usable).not.toContain("Monter");
    expect(usable.some((name) => name.startsWith("Insérer"))).toBe(true);
    await activate(TASK);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(written(client)).toEqual([]);
  });
});
