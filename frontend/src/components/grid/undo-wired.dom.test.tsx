// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  type FakeTiming,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";

import type { NodeList, NodeSortColumn } from "./nodes";
import { PLANNING_GRID } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// Undo and redo of the grid of the planning, and the block pasted on it, wired on the history of the server (US-1450/L3,
// WF-IHM-0110): what the buttons, the menu and the keys send, and how a refusal of the server is told
// by the catalogue. The answers of the server are the examples of the contract; the contract cites
// none for a change undone, the success being played against the service (`e2e/undo.spec.ts`).
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// A change undone reads the page anew from the server action (`history.ts`).
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const UNDO = "POST /projects/{project_id}/revisions/{revision_id}/undo";
const REDO = "POST /projects/{project_id}/revisions/{revision_id}/redo";
const PREVIEW =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview";
const APPLY =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const PREFERENCES = {
  hidden_columns: [
    ...PLANNING_GRID.columns.filter((column) => column.hidden === true).map((column) => column.key),
    "gantt",
  ],
};
const planning = example("nodes_planning") as NodeList;

/** A refusal of the server for a state or a conflict: the problem an example of the contract states. */
function refused(name: string) {
  return { problem: example(name) as Problem & { readonly status: 409 } };
}

/** A refusal of the server for a token without session: the problem an example of the contract states. */
function forbidden(name: string) {
  return { problem: example(name) as Problem & { readonly status: 403 } };
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(answers, timing);
  server.client = client;
  return client;
}

/** The grid of the planning, entered, with undo and redo wired. */
function grid(locale: "fr" | "en" = "fr", structure = STRUCTURE) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PlanningGrid
        nodes={planning}
        structure={structure}
        structureVersion={1}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={PREFERENCES}
        undoable
        editable
      />
    </NextIntlClientProvider>
  );
}

/** The label of the first row, given the focus as a click on it would. */
async function focusLabel(): Promise<HTMLElement> {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>('td[data-row="0"][data-column="label"]');
  if (found === null) {
    throw new Error("no label in the first row");
  }
  await act(async () => {
    found.focus();
    await Promise.resolve();
  });
  return found;
}

/** The calls of the history the grid sent, by route. */
function sent(client: FakeClient, route: string) {
  return client.calls.filter((call) => call.route === route).map((call) => call.path);
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("undo and redo of the grid of the planning, wired on the server's history", () => {
  it("offers Undo and Redo available, with no reason to wait, and sends the undo of the revision when Undo is pressed [WF-IHM-0110-A]", async () => {
    const client = serve({ [UNDO]: refused("undo_history_empty") });
    render(grid());
    const undo = screen.getByRole("button", { name: "Annuler" });
    const redo = screen.getByRole("button", { name: "Rétablir" });
    expect(undo).not.toHaveAttribute("aria-disabled");
    expect(redo).not.toHaveAttribute("aria-disabled");
    expect(screen.queryByText(/Indisponibles tant que/)).toBeNull();
    await userEvent.click(undo);
    await waitFor(() => {
      expect(sent(client, UNDO)).toEqual([
        `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/undo`,
      ]);
    });
    expect(sent(client, REDO)).toEqual([]);
  });

  it("announces an undo done, and a redo done, with how many changes remain [WF-IHM-0110-A]", async () => {
    serve({ [UNDO]: "undo_task_renamed", [REDO]: "redo_task_renamed" });
    render(grid());
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(
      await screen.findByText("Modification annulée. Aucune autre modification à annuler."),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Rétablir" }));
    expect(
      await screen.findByText("Modification rétablie. Aucune autre modification à rétablir."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("tells the refusal of an undo by the catalogue, naming the object a later change took up [WF-IHM-0110-A]", async () => {
    serve({ [UNDO]: refused("undo_later_change") });
    render(grid());
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Impossible d’annuler : la donnée a été modifiée depuis.");
    expect(alert).toHaveTextContent("Objet repris depuis : « Raccordement des borniers ».");
  });

  it("tells the refusal of a redo whose later change took up the object, and Ctrl+Shift+Z asks the redo [WF-IHM-0110-A]", async () => {
    const client = serve({ [REDO]: refused("redo_later_change") });
    render(grid());
    await focusLabel();
    await userEvent.keyboard("{Control>}{Shift>}z{/Shift}{/Control}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Objet repris depuis");
    expect(sent(client, REDO)).toHaveLength(1);
    expect(sent(client, UNDO)).toEqual([]);
  });

  it("asks the undo on Ctrl+Z in the grid, and tells a history with nothing to undo by its condition [WF-IHM-0110-A]", async () => {
    const client = serve({ [UNDO]: refused("undo_history_empty") });
    render(grid());
    await focusLabel();
    await userEvent.keyboard("{Control>}z{/Control}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/historique d’annulation non vide/);
    expect(sent(client, UNDO)).toHaveLength(1);
    // The refusal is dismissed, and told no more.
    await userEvent.click(within(alert).getByRole("button"));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("tells a token that carries no session of sign-in, for which nothing can be undone [WF-IHM-0110-A]", async () => {
    serve({ [UNDO]: forbidden("undo_session_id_missing") });
    render(grid());
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Votre jeton de session ne porte pas d’identifiant de session",
    );
  });

  it("asks the redo from the menu of a cell, wired and with no reason to wait [WF-IHM-0110-A]", async () => {
    const client = serve({ [REDO]: refused("redo_history_empty") });
    render(grid());
    await focusLabel();
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    const redo = within(menu).getByRole("menuitem", { name: /^Rétablir/ });
    expect(redo).not.toHaveAttribute("aria-disabled");
    await userEvent.click(redo);
    await waitFor(() => {
      expect(sent(client, REDO)).toHaveLength(1);
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /historique de rétablissement non vide/,
    );
  });

  it("places them in English too, and tells the refusal in English [WF-IHM-0110-A]", async () => {
    serve({ [UNDO]: refused("undo_later_change") });
    render(grid("en"));
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Object changed since");
  });
});

describe("undo while its request is under way", () => {
  it("marks Undo and Redo inactive while the request is held, and a second press, by the button or Ctrl+Z, sends nothing [WF-IHM-0110-A]", async () => {
    const hold = held();
    const client = serve({ [UNDO]: refused("undo_history_empty") }, hold.timing);
    render(grid());
    const undo = screen.getByRole("button", { name: "Annuler" });
    const redo = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.click(undo);
    await waitFor(() => {
      expect(undo).toHaveAttribute("aria-disabled", "true");
    });
    expect(redo).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(undo);
    await userEvent.click(redo);
    await focusLabel();
    await userEvent.keyboard("{Control>}z{/Control}");
    expect(sent(client, UNDO)).toHaveLength(1);
    expect(sent(client, REDO)).toEqual([]);
    await act(async () => {
      hold.release();
      await hold.until;
    });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => {
      expect(undo).not.toHaveAttribute("aria-disabled");
    });
    expect(redo).not.toHaveAttribute("aria-disabled");
  });

  it("does not tell the refusal on another structure when the structure changed while the request was held [WF-IHM-0110-A]", async () => {
    const hold = held();
    serve({ [UNDO]: refused("undo_later_change") }, hold.timing);
    const { rerender } = render(grid());
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    rerender(grid("fr", { ...STRUCTURE, structure_id: "01926f3a-7c00-7000-8000-000000000202" }));
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Annuler" })).not.toHaveAttribute("aria-disabled");
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("a block pasted on the grid of the planning, judged by the server", () => {
  it("is asked of the preview from the node of the active cell and its column, shown before it writes, then applied with the version of the structure read [WF-IHM-0050-A]", async () => {
    const client = serve({ [PREVIEW]: "paste_plan", [APPLY]: "paste_applied" });
    render(grid());
    const first = planning.items[0];
    await focusLabel();
    await userEvent.paste("Étude préliminaire\nRevue de câblage\n");
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(dialog).toHaveTextContent("3 lignes seront écrites.");
    // The block as copied; the front judges nothing of it. Nothing is written before the confirmation.
    expect(client.calls.filter((call) => call.route === PREVIEW).map((call) => call.body)).toEqual([
      {
        target_node_id: first?.node_id,
        target_column: "label",
        rows: [["Étude préliminaire"], ["Revue de câblage"]],
      },
    ]);
    expect(client.calls.filter((call) => call.route === APPLY)).toEqual([]);
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === APPLY).map((call) => call.body)).toEqual([
        { paste_id: "01926f3a-7c00-7000-8000-000000000991", confirmed: true, lock_version: 1 },
      ]);
    });
  });

  it("reads the page anew when the plan applied creates tasks, which the answer carries [WF-IHM-0050-A]", async () => {
    serve({ [PREVIEW]: "paste_plan_creating", [APPLY]: "paste_applied_creating" });
    router.refresh.mockClear();
    render(grid());
    await focusLabel();
    await userEvent.paste("Étude\nEssais\nRecette\n");
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(dialog).toHaveTextContent("tâches seront créées");
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
  });

  it("does not read the page anew when the plan applied creates no task [WF-IHM-0050-A]", async () => {
    const client = serve({ [PREVIEW]: "paste_plan", [APPLY]: "paste_applied" });
    router.refresh.mockClear();
    render(grid());
    await focusLabel();
    await userEvent.paste("Étude préliminaire\nRevue de câblage\n");
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === APPLY)).toHaveLength(1);
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Coller depuis un tableur" })).toBeNull();
    });
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("keeps the grid busy until the page read anew arrives, so that no gesture starts from the rows of before [WF-IHM-0050-A]", async () => {
    serve({ [PREVIEW]: "paste_plan_creating", [APPLY]: "paste_applied_creating" });
    router.refresh.mockClear();
    holdReading(router.refresh);
    render(grid(), { wrapper: Reading });
    await focusLabel();
    await userEvent.paste("Étude\nEssais\nRecette\n");
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    await waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-busy", "true");
    act(() => {
      releaseReading();
    });
    await waitFor(() => {
      expect(screen.getByRole("treegrid")).not.toHaveAttribute("aria-busy", "true");
    });
  });
});
