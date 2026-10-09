// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it: the fake back behind serverClient, which the
// server action recording the settings calls; the router, whose address a sort or a search
// changes; and the address of the page.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r",
  useSearchParams: () => new URLSearchParams(page.search),
}));

// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

/** The grid of the estimate as the page renders it once the server answered an address. */
function estimate(search: string | undefined) {
  const query: GridQuery<NodeSortColumn> = { sort: undefined, search };
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={{}}
        reference={estimateReference()}
        editable
        tasksEditable
        nodes={example("nodes") as NodeList}
        structure={STRUCTURE}
        structureVersion={1}
        query={query}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** Render the grid at an address, and how to show it at another, as the page does. */
function renderAt(search: string) {
  page.search = search;
  const rendered = render(estimate(new URLSearchParams(search).get("search") ?? undefined));
  return (next: string) => {
    page.search = next;
    rendered.rerender(estimate(new URLSearchParams(next).get("search") ?? undefined));
  };
}

/** The search of the grid. */
function field(): HTMLElement {
  return screen.getByRole("searchbox", { name: "Rechercher un libellé" });
}

/** The query of the last address the grid navigated to. */
function lastAsked(): Record<string, string> {
  const [href] = router.push.mock.calls.at(-1) as [string];
  return Object.fromEntries(new URL(href, "http://front.invalid").searchParams);
}

beforeEach(() => {
  router.push.mockReset();
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the address a screen asked, once the history goes back over it (#557)", () => {
  it("never applies again by a sort a search « Précédent » gave up", async () => {
    const showAt = renderAt("subproject_id=unassigned");
    await userEvent.type(field(), "revue{Enter}");
    expect(lastAsked()).toEqual({ subproject_id: "unassigned", search: "revue" });
    showAt("subproject_id=unassigned&search=revue");
    // « Précédent » to the address the search was sent from, then a sort: the search given up stays.
    showAt("subproject_id=unassigned");
    await userEvent.click(
      within(screen.getByRole("columnheader", { name: /inflation/ })).getByRole("button"),
    );
    expect(lastAsked()).toEqual({
      subproject_id: "unassigned",
      sort_by: "inflated_amount",
      sort_order: "asc",
    });
  });

  it("never applies again by a sort a search given up by asking the address shown before it arrived", async () => {
    renderAt("subproject_id=unassigned");
    await userEvent.type(field(), "revue{Enter}");
    // Emptied and sent before the server answers: the address asked is the one shown, which
    // gives up the search under way, Next dropping it.
    await userEvent.clear(field());
    await userEvent.type(field(), "{Enter}");
    expect(lastAsked()).toEqual({ subproject_id: "unassigned" });
    await userEvent.click(
      within(screen.getByRole("columnheader", { name: /inflation/ })).getByRole("button"),
    );
    expect(lastAsked()).toEqual({
      subproject_id: "unassigned",
      sort_by: "inflated_amount",
      sort_order: "asc",
    });
  });

  it("keeps a search typed on while the one sent was on its way, once it arrives", async () => {
    const showAt = renderAt("");
    await userEvent.type(field(), "rev{Enter}");
    // Typed on before the server answers.
    await userEvent.type(field(), "ue");
    showAt("search=rev");
    expect(field()).toHaveValue("revue");
    expect(field()).toHaveFocus();
  });

  it("keeps a search typed on while the one sent was on its way, once a sort composed on it arrives", async () => {
    const showAt = renderAt("");
    await userEvent.type(field(), "rev{Enter}");
    await userEvent.type(field(), "ue");
    // A sort clicked before the server answers: it carries the search sent, and arrives in its
    // place, Next dropping the navigation of the search alone.
    await userEvent.click(
      within(screen.getByRole("columnheader", { name: /inflation/ })).getByRole("button"),
    );
    expect(lastAsked()).toEqual({ search: "rev", sort_by: "inflated_amount", sort_order: "asc" });
    showAt(new URLSearchParams(lastAsked()).toString());
    expect(field()).toHaveValue("revue");
  });

  it("shows a search sent on while the one before was on its way as the address writes it, once it arrives", async () => {
    const showAt = renderAt("");
    await userEvent.type(field(), "rev{Enter}");
    await userEvent.type(field(), "ue  {Enter}");
    expect(lastAsked()).toEqual({ search: "revue" });
    showAt("search=revue");
    expect(field()).toHaveValue("revue");
  });

  it("forgets a search typed on while the one sent was on its way when « Précédent » comes before it", async () => {
    const showAt = renderAt("search=old");
    await userEvent.clear(field());
    await userEvent.type(field(), "rev{Enter}");
    await userEvent.type(field(), "ue");
    // « Précédent » before the server answers, to an address of no search: the entry made over the
    // address left is given up.
    showAt("");
    expect(field()).toHaveValue("");
  });

  it("never brings back by « Suivant » a search typed over the address « Précédent » came back to", async () => {
    const showAt = renderAt("");
    await userEvent.type(field(), "rev{Enter}");
    showAt("search=rev");
    // « Précédent », a search typed and given up, then « Suivant » to the address the search sent
    // brought: it shows its own search.
    showAt("");
    await userEvent.type(field(), "zzz");
    showAt("search=rev");
    expect(field()).toHaveValue("rev");
  });
});
