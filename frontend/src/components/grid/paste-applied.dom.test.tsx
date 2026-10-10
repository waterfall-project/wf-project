// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient, type FakeTiming } from "@/test/fixtures";
import {
  APPLY,
  BLOCK,
  bodies,
  cell,
  copied,
  FIRST,
  LINE,
  labels,
  pasteOn,
  PREVIEW,
  READ,
  renderGrid,
  ROW,
  UNKNOWN,
} from "@/test/paste-grid";

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

/**
 * Serve the fake back — by default the block whose second row names an unknown category, and its
 * confirmation, which writes the other two (`paste_applied_partial`) —, and give it back.
 */
function serve(answers: FakeAnswers = {}, timing: FakeTiming = {}): FakeClient {
  const client = fakeClient(
    {
      [PREVIEW]: "paste_plan_unknown_category",
      [APPLY]: "paste_applied_partial",
      ...answers,
    },
    timing,
  );
  server.client = client;
  return client;
}

/** Paste a block on the label of the row 4, and confirm its plan once the server answered it. */
async function pasteAndApply(block: readonly (readonly string[])[]): Promise<void> {
  await pasteOn(cell(FIRST, "label"), copied(block));
  const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
  await userEvent.click(
    await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
  );
  await vi.waitFor(() => {
    expect(screen.queryByRole("dialog")).toBeNull();
  });
}

/** The notice of a paste applied that did not write every row. */
function told(): HTMLElement {
  const notice = screen
    .getAllByRole("alert")
    .find((alert) => alert.textContent.startsWith("Collage appliqué"));
  if (notice === undefined) {
    throw new Error("no notice of a paste applied");
  }
  return notice;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
  router.refresh.mockClear();
});

describe("a paste applied", () => {
  it("whose cell names an unknown category writes the other rows once confirmed, and not that one, which it tells [WF-IHM-0050-A]", async () => {
    // Confirmé, il écrit les autres lignes et non celle-ci.
    const client = serve();
    renderGrid();
    await pasteAndApply(UNKNOWN);
    expect(bodies(client, APPLY)).toEqual([
      { paste_id: "01926f3a-7c00-7000-8000-000000000992", confirmed: true, lock_version: 1 },
    ]);
    // The first and the third rows written, the second as it was read.
    expect(labels()).toEqual([
      "Heures de câblage et repérage",
      "Heures de mise en service",
      "Matériel de câblage",
    ]);
    expect(cell(FIRST + 2, "quantity")).toHaveTextContent("24");
    // Where the block was pasted from, what was written, and the row the server did not write,
    // with its reason and its cells.
    expect(told()).toHaveTextContent(
      new RegExp(
        `^Collage appliqué à partir de la ligne ${ROW.toString()}, colonne « Libellé » : 2 lignes ont été écrites\\.1 ligne est refusée :`,
      ),
    );
    expect(within(told()).getByRole("listitem")).toHaveTextContent(
      "Ligne 2 du bloc — Catégorie de coût inconnue.",
    );
    expect(within(told()).getByText("Essais")).toBeVisible();
  });

  it("is told until dismissed, the focus given back to the cell pasted on", async () => {
    serve();
    renderGrid();
    await pasteAndApply(UNKNOWN);
    await userEvent.click(within(told()).getByRole("button", { name: "Fermer l’avis" }));
    expect(screen.queryByRole("alert")).toBeNull();
    await vi.waitFor(() => {
      expect(cell(FIRST, "label")).toHaveFocus();
    });
  });

  it("is no longer told once another block is pasted", async () => {
    serve({ [PREVIEW]: ["paste_plan_unknown_category", "paste_plan"] });
    renderGrid();
    await pasteAndApply(UNKNOWN);
    expect(told()).toBeVisible();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await within(dialog).findByText("3 lignes seront écrites.");
    expect(screen.queryByText(/^Collage appliqué/)).toBeNull();
  });

  it("tells a row the confirmation refuses that the preview accepted, read from what it answers", async () => {
    // The server judges the accepted rows again at the confirmation (EP-14/L42q). A counterfactual
    // pairing of two examples: the plan that refuses none (`paste_plan`) confirmed by the answer
    // that refuses the second row (`paste_applied_partial`), which confirms another plan — the
    // contract has no example of a refusal the confirmation alone gives (#764). The refusal is told
    // as it is answered, never from the plan.
    serve({ [PREVIEW]: "paste_plan" });
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await within(dialog).findByText("Aucune ligne n’est refusée.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(told()).toHaveTextContent("2 lignes ont été écrites.");
    expect(within(told()).getByRole("listitem")).toHaveTextContent(
      "Ligne 2 du bloc — Catégorie de coût inconnue.",
    );
    expect(within(told()).getByText("Mise en service")).toBeVisible();
  });

  it("refused for a structure changed since its preview offers to read it anew, the grid left as it was", async () => {
    serve({ [APPLY]: { problem: { code: "STALE_LOCK_VERSION", status: 412 } } });
    renderGrid();
    await pasteAndApply(UNKNOWN);
    const refusal = screen.getByRole("alert");
    expect(refusal).toHaveTextContent(/modifié cette donnée/);
    expect(labels()).toEqual(READ);
    await userEvent.click(within(refusal).getByRole("button", { name: "Recharger" }));
    expect(router.refresh).toHaveBeenCalledOnce();
  });

  it("keeps the refusal of a cell written before it on a row it did not write", async () => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const stale = { problem: { code: "STALE_LOCK_VERSION", status: 412 } } as const;
    serve({ [LINE]: stale }, { hold: (route) => (route === LINE ? held : undefined) });
    renderGrid();
    // The label of the row 5 leaves, the server yet to answer; the block then confirmed writes the
    // rows 4 and 6, not the row 5, whose refusal arrives after it.
    cell(FIRST + 1, "label").focus();
    await userEvent.keyboard("X{Enter}");
    await pasteAndApply(UNKNOWN);
    await act(async () => {
      release();
      await held;
    });
    await vi.waitFor(() => {
      expect(screen.getAllByRole("alert").map((alert) => alert.textContent)).toContainEqual(
        expect.stringMatching(/modifié cette donnée/),
      );
    });
    expect(labels()).toEqual([
      "Heures de câblage et repérage",
      "Heures de mise en service",
      "Matériel de câblage",
    ]);
  });
});
