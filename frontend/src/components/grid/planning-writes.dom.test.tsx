// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { findOffer } from "@/components/commands/offer";
import type { Revision } from "@/components/context/read-only";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";

import type { NodeList, NodesWritten, NodeSortColumn } from "./nodes";
import {
  type BreakdownItem,
  breakdownItems,
  type WorkBreakdownReading,
} from "./planning-attachment";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const TASK =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";
const SKELETON = "POST /projects/{project_id}/revisions/{revision_id}/skeleton";
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The revision opened today on the project created at 14:05, its main structure without a task.
const EMPTY = {
  project_id: "01926f3a-7c00-7000-8000-000000000003",
  revision_id: "01926f3a-7c00-7000-8000-000000000105",
  structure_id: "01926f3a-7c00-7000-8000-000000000207",
};
// The planning of the core of the witness, its tasks alone: « Poste de commande » bears the lot of
// the work breakdown, « Câblage des armoires » under it nothing.
const nested = example("nodes_nested") as NodeList;
// The tasks of the studies, none attached.
const studies = example("nodes_planning") as NodeList;
const empty = example("nodes_empty") as NodeList;
// The work breakdown of the witness: the lot « Lot 1 », its post « Poste 1.1 ».
const breakdown = breakdownItems(example("work_breakdown") as WorkBreakdownReading);
const POST = breakdown.find((item) => item.kind === "order_item")?.id ?? "";
const LOT = breakdown.find((item) => item.kind === "work_package")?.id ?? "";

/** The offer of the skeleton a revision of the examples lists. */
function skeletonOf(name: "revision" | "revision_without_tasks") {
  return findOffer((example(name) as Revision).available_commands, "generate_skeleton");
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(answers, { hold: () => hold });
  server.client = client;
  return client;
}

/** The grid of the planning on an answer, entered; the attachment, when the work breakdown is given. */
function grid(
  nodes: NodeList,
  {
    structure = STRUCTURE,
    version = 1,
    items = breakdown,
    skeleton,
  }: {
    readonly structure?: typeof STRUCTURE;
    readonly version?: number;
    /** The lots and the posts read; `null` for none, the work breakdown not read. */
    readonly items?: readonly BreakdownItem[] | null;
    readonly skeleton?: ReturnType<typeof skeletonOf>;
  } = {},
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={structure}
        structureVersion={version}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable
        editable
        breakdown={items ?? undefined}
        skeleton={skeleton}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of the attachment of the row at a position. */
function attachmentAt(row: number): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="work_breakdown"]`);
  if (found === null) {
    throw new Error(`no attachment for the row ${row.toString()}`);
  }
  return found;
}

/** The cell of the attachment of the first row of a label. */
function attachmentOf(nodes: NodeList, label: string): HTMLElement {
  return attachmentAt(nodes.items.findIndex((node) => node.task?.label === label));
}

/** Choose an item of the list of a cell — none for an empty identifier —, and validate it. */
async function choose(cell: HTMLElement, id: string) {
  cell.focus();
  await userEvent.keyboard("{Enter}");
  fireEvent.change(screen.getByRole("combobox", { name: "Rattachement" }), {
    target: { value: id },
  });
  await userEvent.keyboard("{Enter}");
}

/** The bodies of the writes of a task the grid sent, with their node. */
function written(client: FakeClient) {
  return client.calls
    .filter((call) => call.route === TASK)
    .map((call) => ({ node: call.path.split("/").at(-2), body: call.body }));
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  forgetMessages();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the attachment of a task in the grid of the planning", () => {
  it("shows the lot or the post a task bears by the label the server resolves, and offers the lots and the posts read, or none", async () => {
    serve({});
    render(grid(nested));
    const lot = attachmentOf(nested, "Poste de commande");
    expect(lot).toHaveTextContent("Lot 1");
    expect(attachmentOf(nested, "Câblage des armoires")).toHaveTextContent(/^$/);
    lot.focus();
    await userEvent.keyboard("{Enter}");
    const list = screen.getByRole("combobox", { name: "Rattachement" });
    expect(list).toHaveValue(LOT);
    expect(
      within(list)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Aucun", "Lot — Lot 1", "Poste — Poste 1.1"]);
  });

  it("attaches a leaf to a post, the order item alone written with the version read [WF-PLA-0170-A]", async () => {
    // Une feuille peut être rattachée à un poste: typed, the first letter finds the post.
    const client = serve({ [TASK]: "task_renamed" });
    render(grid(nested));
    attachmentOf(nested, "Câblage des armoires").focus();
    await userEvent.keyboard("P{Enter}");
    expect(written(client)).toEqual([
      {
        node: nested.items.find((node) => node.task?.label === "Câblage des armoires")?.node_id,
        body: { order_item_id: POST, lock_version: 1 },
      },
    ]);
    // The row the server answered takes the place of the row read.
    expect(await screen.findByText("Câblage et repérage des armoires")).toBeInTheDocument();
  });

  // The tasks the skeleton of the default work breakdown answers: the summary of the lot bears the
  // lot, as a task the skeleton attached does; the example is read as the contract gives it.
  const generated = example("skeleton_generated") as NodesWritten;
  const bearing: NodeList = { ...empty, items: generated.nodes };
  const DEFAULT = breakdownItems(example("work_breakdown_default") as WorkBreakdownReading);
  const DEFAULT_LOT = DEFAULT.find((item) => item.kind === "work_package")?.id ?? "";
  const DEFAULT_POST = DEFAULT.find((item) => item.kind === "order_item")?.id ?? "";

  it.each([
    {
      chosen: "the post, the lot taken off in the same write",
      id: DEFAULT_POST,
      sent: { order_item_id: DEFAULT_POST, work_package_id: null },
    },
    { chosen: "none, the lot taken off", id: "", sent: { work_package_id: null } },
  ])(
    "writes $chosen for a task that bears a lot, never both [WF-PLA-0170-A]",
    async ({ id, sent }) => {
      const client = serve({ [TASK]: "task_renamed" });
      render(grid(bearing, { items: DEFAULT }));
      const lot = generated.nodes[0]?.task;
      expect(lot?.work_package_id).toBe(DEFAULT_LOT);
      await choose(attachmentOf(bearing, lot?.label ?? ""), id);
      expect(written(client).map(({ body }) => body)).toEqual([{ ...sent, lock_version: 1 }]);
    },
  );

  it.each([
    {
      chosen: "the lot, the post taken off in the same write",
      id: DEFAULT_LOT,
      sent: { work_package_id: DEFAULT_LOT, order_item_id: null },
    },
    { chosen: "none, the post taken off", id: "", sent: { order_item_id: null } },
  ])(
    "writes $chosen for a task that bears a post, never both [WF-PLA-0170-A]",
    async ({ id, sent }) => {
      const client = serve({ [TASK]: "task_renamed" });
      render(grid(bearing, { items: DEFAULT }));
      // The summary of the post, the second node the skeleton answers: it bears the post alone.
      const post = generated.nodes[1]?.task;
      expect(post?.order_item_id).toBe(DEFAULT_POST);
      expect(post?.work_package_id ?? null).toBeNull();
      await choose(attachmentAt(1), id);
      expect(written(client).map(({ body }) => body)).toEqual([{ ...sent, lock_version: 1 }]);
    },
  );

  it.each([
    {
      name: "task_attach_refused",
      title: "a lot another task bears, naming that task [WF-PLA-0170-A]",
      id: LOT,
      said: [
        "Ce lot ou ce poste est déjà porté par une autre tâche.",
        "Objet en conflit : Poste de commande.",
      ],
      described:
        /^Ce lot ou ce poste est déjà porté par une autre tâche\.\s+Objet en conflit\s:\sPoste de commande\.$/,
    },
    {
      name: "task_attach_exclusive",
      title: "a lot and a post at once [WF-PLA-0170-A]",
      id: POST,
      said: ["Une tâche porte un lot ou un poste, jamais les deux."],
      described: /^Une tâche porte un lot ou un poste, jamais les deux\.$/,
    },
    {
      name: "task_attach_exclusive_attached",
      title: "a lot and a post at once, the lot being borne by another task [WF-PLA-0170-A]",
      id: LOT,
      said: [
        "Une tâche porte un lot ou un poste, jamais les deux.",
        "Ce lot ou ce poste est déjà porté par une autre tâche.",
        "Objet en conflit : Poste de commande.",
      ],
      described:
        /^Une tâche porte un lot ou un poste, jamais les deux\.\s+Ce lot ou ce poste est déjà porté par une autre tâche\.\s+Objet en conflit\s:\sPoste de commande\.$/,
    },
    {
      name: "task_attach_main_structure_only",
      title: "a task out of the main structure",
      id: POST,
      said: ["Seule une tâche de la structure principale porte un lot ou un poste."],
      described: /^Seule une tâche de la structure principale porte un lot ou un poste\.$/,
    },
    {
      name: "task_attach_outside_work_package",
      title: "a post out of the subtree of its lot, naming its tasks [WF-PLA-0170-A]",
      id: POST,
      said: [
        "La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot. Tâche du lot : « Poste de commande ». Tâche du poste en cause : « Études ».",
      ],
      described:
        /^La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot\. Tâche du lot\s:\s«\sPoste de commande\s»\. Tâche du poste en cause\s:\s«\sÉtudes\s»\.$/,
    },
  ] as const)("says at its cell the refusal of $title", async ({ name, id, said, described }) => {
    const problem = example(name) as Problem & { readonly status: 422 };
    serve({ [TASK]: { problem } });
    render(grid(studies));
    const cell = attachmentOf(studies, "Études");
    await choose(cell, id);
    const alert = await screen.findByRole("alert");
    for (const sentence of said) {
      expect(alert).toHaveTextContent(sentence);
    }
    // The cell is marked, and described by the refusal, the task in conflict named; it keeps what
    // the server read.
    expect(cell).toHaveAttribute("aria-invalid", "true");
    expect(cell).toHaveAccessibleDescription(described);
    expect(cell).toHaveTextContent(/^$/);
  });

  it("no longer marks the cell once written after its refusal, the notice told until dismissed", async () => {
    const problem = example("task_attach_refused") as Problem & { readonly status: 422 };
    serve({ [TASK]: [{ problem }, "task_renamed"] });
    render(grid(nested));
    const cell = attachmentOf(nested, "Câblage des armoires");
    await choose(cell, LOT);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(cell).toHaveAttribute("aria-invalid", "true");
    await choose(cell, POST);
    expect(await screen.findByText("Câblage et repérage des armoires")).toBeInTheDocument();
    expect(cell).not.toHaveAttribute("aria-invalid");
    expect(cell).not.toHaveAttribute("aria-describedby");
    expect(screen.getByRole("alert")).toHaveTextContent("Objet en conflit");
  });

  it("enters no attachment without the work breakdown read, nor on a task whose item the work breakdown does not know", () => {
    serve({});
    const { rerender } = render(grid(nested, { items: null }));
    expect(attachmentOf(nested, "Câblage des armoires")).toHaveAttribute("aria-readonly", "true");
    // The post alone read: the task that bears the lot is not entered.
    rerender(grid(nested, { items: breakdown.filter((item) => item.id === POST) }));
    expect(attachmentOf(nested, "Poste de commande")).toHaveAttribute("aria-readonly", "true");
    expect(attachmentOf(nested, "Câblage des armoires")).not.toHaveAttribute("aria-readonly");
  });
});

describe("the skeleton of the planning", () => {
  it("is offered in the empty grid as the revision lists it, and fills the grid with the tasks it answers, the focus on what the screen says", async () => {
    const client = serve({ [SKELETON]: { example: "skeleton_generated", status: 201 } });
    render(
      grid(empty, { structure: EMPTY, version: 0, skeleton: skeletonOf("revision_without_tasks") }),
    );
    expect(
      screen.getByRole("row", { name: "Aucune ligne ne répond à la demande." }),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Engendrer le squelette de planning" }),
    );
    const told = await screen.findByText(
      "Squelette de planning engendré : 4 tâches dans la grille.",
    );
    expect(told).toHaveAttribute("role", "status");
    expect(told).toHaveFocus();
    // Noted once in the history of the messages, as the screen says it.
    expect(readMessages().messages).toEqual([
      expect.objectContaining({ tone: "success", sentence: told.textContent }),
    ]);
    expect(client.calls.map((call) => call.path)).toEqual([
      `/projects/${EMPTY.project_id}/revisions/${EMPTY.revision_id}/skeleton`,
    ]);
    // The summaries of the post and of its lot, each attached to its own, and their two milestones.
    const filled = screen.getByRole("treegrid", { name: "Grille de planning" });
    expect(within(filled).getAllByRole("row")).toHaveLength(6);
    expect(within(filled).getAllByText("Rénovation du poste de livraison")).toHaveLength(4);
    expect(within(filled).getAllByText("Fin de « Rénovation du poste de livraison »")).toHaveLength(
      2,
    );
    expect(within(filled).getByText("Total — 4 tâches")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Engendrer le squelette de planning" })).toBeNull();
  });

  it("is no longer offered once the main structure bears a task: unavailable with its condition in an empty reading, absent beside tasks [WF-PRJ-0030-A]", async () => {
    // Elle n'est plus proposée dès que la structure principale comporte une tâche: the witness,
    // read by a search that retains nothing, then whole.
    const client = serve({});
    const { rerender } = render(grid(empty, { skeleton: skeletonOf("revision") }));
    const command = screen.getByRole("button", { name: "Engendrer le squelette de planning" });
    expect(command).toHaveAttribute("aria-disabled", "true");
    expect(command).toHaveAccessibleDescription(
      "Condition non remplie\u00a0: structure principale sans aucune tâche.",
    );
    await userEvent.click(command);
    expect(client.calls).toEqual([]);
    rerender(grid(studies, { skeleton: skeletonOf("revision") }));
    expect(screen.queryByRole("button", { name: "Engendrer le squelette de planning" })).toBeNull();
  });

  it("says its refusal naming the first condition it lacks, the grid left empty", async () => {
    const problem = example("skeleton_structure_not_empty") as Problem & { readonly status: 409 };
    serve({ [SKELETON]: { problem } });
    render(
      grid(empty, { structure: EMPTY, version: 0, skeleton: skeletonOf("revision_without_tasks") }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Engendrer le squelette de planning" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’état actuel ne permet pas cette opération. Condition non remplie : structure principale sans aucune tâche.",
    );
    expect(screen.getByText("Total — aucune tâche")).toBeInTheDocument();
  });

  it("never fills the grid of another structure, keeps its tasks over the same reading anew, and gives way to a more recent one", async () => {
    const hold = held();
    serve({ [SKELETON]: { example: "skeleton_generated", status: 201 } }, hold.until);
    const offer = skeletonOf("revision_without_tasks");
    const { rerender } = render(grid(empty, { structure: EMPTY, version: 0, skeleton: offer }));
    await userEvent.click(
      screen.getByRole("button", { name: "Engendrer le squelette de planning" }),
    );
    // Another revision shown while the skeleton is generated: its answer fills nothing there.
    rerender(grid(empty, { version: 0, skeleton: offer }));
    await act(async () => {
      hold.release();
      await hold.until;
    });
    expect(screen.getByText("Total — aucune tâche")).toBeInTheDocument();
    expect(screen.queryByText(/^Squelette de planning engendré/)).toBeNull();
    // Back on the structure it was generated on, the tasks answered show; the same reading read
    // anew keeps them…
    rerender(grid(empty, { structure: EMPTY, version: 0, skeleton: offer }));
    expect(screen.getByText("Total — 4 tâches")).toBeInTheDocument();
    rerender(grid({ ...empty }, { structure: EMPTY, version: 0, skeleton: offer }));
    expect(screen.getByText("Total — 4 tâches")).toBeInTheDocument();
    // …and a reading at the version the skeleton moved the structure on to prevails.
    rerender(grid(studies, { structure: EMPTY, version: 1, skeleton: offer }));
    expect(screen.getByText("Total — 6 tâches")).toBeInTheDocument();
  });
});
