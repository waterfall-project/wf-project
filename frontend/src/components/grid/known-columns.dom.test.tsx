// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { keysOf, PREFERENCES } from "@/test/grid-preferences";
import { estimateReference } from "@/test/reference";

import { ESTIMATE_GRID } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import type { NodeList } from "./nodes";
import type { GridPreferences } from "./settings";

// The columns a grid knows, which it records with its settings (US-0650): a column hidden by default
// that the grid did not know stays hidden for an account that set the grid, and one the account
// chose to show stays shown. The server of Next, as far as the grid needs it: the fake back behind
// serverClient, which the server action recording the settings calls; the router and the address.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

// The grid of the estimate Camille Martin set before the grid offered the sub-project.
const kept = (
  example("me_grid_settings") as {
    readonly display_preferences: { readonly grids: { readonly estimate: GridPreferences } };
  }
).display_preferences.grids.estimate;

/** The grid of the estimate over a window of the witness's rows, under the preferences given. */
function grid(preferences: GridPreferences) {
  const nodes = example("nodes") as NodeList;
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={{}}
        reference={estimateReference()}
        editable
        tasksEditable
        nodes={{ ...nodes, items: nodes.items.slice(0, 4) }}
        structure={STRUCTURE}
        structureVersion={1}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={preferences}
      />
    </NextIntlClientProvider>
  );
}

/** Whether the grid shows the column of the sub-project. */
function subprojectShown(): boolean {
  return screen.queryByRole("columnheader", { name: /Sous-projet/ }) !== null;
}

// aucune exigence : propre à l'US (US-0650, une colonne masquée par défaut, nouvelle pour la grille).
describe("a column hidden by default that a grid set by the account did not know", () => {
  it("stays hidden; shown by the account, it is recorded with every column the grid offers as known, and stays shown", async () => {
    const client = fakeClient({ [PREFERENCES]: "preferences" });
    server.client = client;
    expect(kept.hidden_columns).not.toContain("subproject");
    expect(kept.known_columns).not.toContain("subproject");
    const { unmount } = render(grid(kept));
    expect(subprojectShown()).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Colonnes" }));
    await userEvent.click(
      within(screen.getByRole("menu")).getByRole("menuitemcheckbox", { name: "Sous-projet" }),
    );
    await userEvent.keyboard("{Escape}");
    expect(subprojectShown()).toBe(true);
    // Recorded once the user pauses: the columns the grid offers, computed from them, as known.
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === PREFERENCES)).toHaveLength(1);
    });
    const [call] = client.calls;
    const recorded = (call?.body as { grids: { estimate: GridPreferences } }).grids.estimate;
    expect(recorded.known_columns).toEqual(keysOf(ESTIMATE_GRID.columns));
    expect(recorded.known_columns).toContain("subproject");
    expect(recorded.hidden_columns).toEqual(kept.hidden_columns);
    unmount();

    // The grid read again with what it recorded: the sub-project the account chose stays shown.
    render(grid(recorded));
    expect(subprojectShown()).toBe(true);
  });
});
