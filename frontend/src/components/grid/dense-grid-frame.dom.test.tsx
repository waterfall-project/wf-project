// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList } from "./nodes";
import type { GridPreferences } from "./settings";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r",
  useSearchParams: () => new URLSearchParams(""),
}));

const witness = example("nodes") as NodeList;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

/** Render the grid of the estimate on the first `rows` rows of the witness. */
function renderGrid(rows: number, preferences?: GridPreferences) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={{}}
        reference={estimateReference()}
        editable
        tasksEditable
        nodes={{ ...witness, items: witness.items.slice(0, rows) }}
        structure={STRUCTURE}
        structureVersion={1}
        query={{ sort: undefined, search: undefined }}
        preferences={preferences}
      />
    </NextIntlClientProvider>,
  );
}

/** The frame that scrolls the grid, and what holds the grid and its bar. */
function frame(): { readonly scroller: HTMLElement; readonly holder: HTMLElement } {
  const scroller = screen.getByRole("treegrid", { name: "Grille de devis" }).parentElement;
  const holder = scroller?.parentElement;
  if (scroller === null || holder === null || holder === undefined) {
    throw new Error("the grid has no frame");
  }
  return { scroller, holder };
}

/** The bar above the grid. */
function bar(): HTMLElement {
  const element = screen.getByRole("search").parentElement;
  if (element === null) {
    throw new Error("the grid has no bar");
  }
  return element;
}

describe("the floor of the frame of a grid (#1041, #1033)", () => {
  it.each([
    [0, 5.75],
    [1, 5.75],
    [2, 7.5],
  ])(
    "is never taller than the content of a grid of %i rows: %f rem and the borders",
    (rows, rem) => {
      renderGrid(rows);
      expect(frame().scroller.style.minHeight).toBe(`min(10rem, calc(${String(rem)}rem + 2px))`);
    },
  );

  it("keeps no fixed class floor, and lifts the floor and the bar to what holds the grid", () => {
    renderGrid(2);
    const { scroller, holder } = frame();
    expect(scroller.className).not.toContain("min-h-40");
    // What holds the grid is as high, at least, as its frame at its floor and the bar over it, the
    // bar and the gap under it counting 2.25 rem.
    expect(holder.style.minHeight).toBe(`calc(${scroller.style.minHeight} + 2.25rem)`);
  });
});

describe("the bar of a grid follows the width of its table (#1042)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each([
    ["by the default widths", undefined],
    [
      "by the narrower widths of the account",
      {
        hidden_columns: ["hours"],
        column_widths: { label: 120 },
      } satisfies GridPreferences,
    ],
  ])(
    "is as wide as the table and its two borders until the frame is laid out, %s",
    (_, preferences) => {
      renderGrid(2, preferences);
      const table = screen.getByRole("treegrid", { name: "Grille de devis" });
      const width = Number.parseInt(table.style.width, 10);
      expect(width).toBeGreaterThan(0);
      expect(Number.parseInt(bar().style.width, 10)).toBe(width + 2);
      // The « Colonnes » menu is in the bar, so at the edge of the table.
      expect(bar()).toContainElement(screen.getByRole("button", { name: "Colonnes" }));
    },
  );

  it("is as wide as the frame once the browser has laid it out, the scroll bars it draws in", () => {
    // A frame 17 points wider than its table and borders: a bar of a system that takes a place.
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1017);
    renderGrid(2);
    expect(bar().style.width).toBe("1017px");
  });

  it("keeps on one line what the bar holds: it wraps nothing and does not go below its content", () => {
    renderGrid(2);
    expect(bar()).not.toHaveClass("flex-wrap");
    expect(bar()).toHaveClass("min-w-min", "max-w-full");
    expect(screen.getByRole("search")).toHaveClass("shrink", "min-w-24");
  });

  it("keeps a notice outside the bar, a child of what holds the grid and so on its whole width", async () => {
    server.client = fakeClient({
      "PATCH /me/preferences": { problem: { code: "SESSION_REQUIRED", status: 401 } },
    });
    renderGrid(2);
    screen.getByRole("separator", { name: "Largeur de la colonne Libellé" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    const notice = await screen.findByRole("alert");
    expect(bar()).not.toContainElement(notice);
    const { holder } = frame();
    expect(holder).toContainElement(notice);
    // No element between the notice and what holds the grid sets a width of its own.
    for (let up = notice.parentElement; up !== null && up !== holder; up = up.parentElement) {
      expect(up.style.width, up.className).toBe("");
    }
    expect(holder.style.width).toBe("");
  });
});
