// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { listedProject } from "./project-list-grid";
import { ProjectListGrid, ProjectStateFilter } from "./project-list-view";

// The server of Next, as far as the screen needs it: the preferences it writes, the address it
// reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

/** The projects the fake back lists: the witness in progress, an offer in pricing. */
const LIST = example("projects") as {
  items: Schemas["Project"][];
  meta: Schemas["PaginationMeta"];
};

/** A part of the home, in French, under the address of the screen. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the list, as the page hands it the projects of the example. */
function listGrid() {
  return inFrench(
    <ProjectListGrid
      projects={LIST.items.map(listedProject)}
      page={LIST.meta}
      query={{ sort: undefined, search: undefined }}
      preferences={undefined}
    />,
  );
}

/** The grid of the list. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Liste des projets" });
}

/** The address the last navigation asked for. */
async function lastAddress(): Promise<string> {
  await waitFor(() => {
    expect(router.push).toHaveBeenCalled();
  });
  return String(router.push.mock.lastCall?.[0]);
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the grid of the list of projects", () => {
  it("presents each project with its code, its state by its badge and when it was modified", () => {
    render(listGrid());
    const headers = within(grid()).getAllByRole("columnheader");
    expect(headers.map((header) => header.textContent)).toEqual([
      "Libellé",
      "Code",
      "État",
      "Modifié le",
    ]);
    const witness = within(grid())
      .getAllByRole("row")
      .find((row) => row.textContent.includes("PRJ-001"));
    expect(witness).toHaveTextContent("En cours");
    expect(within(witness ?? document.body).getByText("En cours").parentElement).toHaveClass(
      "bg-state-in-progress",
    );
    expect(within(witness ?? document.body).getByText(/2026/)).toHaveAttribute(
      "datetime",
      "2026-02-02T09:00:00Z",
    );
  });

  it("opens each project from its label", () => {
    render(listGrid());
    expect(
      within(grid()).getByRole("link", { name: "Modernisation du poste de commande" }),
    ).toHaveAttribute("href", "/projects/01926f3a-7c00-7000-8000-000000000001");
  });

  it("says in its totals row how many projects the server retained, and is accessible", async () => {
    const { container } = render(listGrid());
    expect(within(grid()).getAllByRole("row").at(-1)).toHaveTextContent("2 projets");
    await expectAccessible(container);
  });

  it.each([
    ["Libellé", "label"],
    ["Code", "code"],
    ["État", "state"],
    ["Modifié le", "updated_at"],
  ])("asks the server to sort by the column %s, from the address", async (heading, column) => {
    const user = userEvent.setup();
    render(listGrid());
    const header = within(grid()).getByRole("columnheader", { name: heading });
    await user.click(within(header).getByRole("button"));
    expect(await lastAddress()).toBe(`/?sort_by=${column}&sort_order=asc`);
  });

  it("asks the server to search, back to the first page", async () => {
    const user = userEvent.setup();
    page.search = "offset=50";
    render(listGrid());
    await user.type(screen.getByRole("searchbox"), "poste{Enter}");
    expect(await lastAddress()).toBe("/?search=poste");
  });

  it("says a page asked beyond the end of the list, and leads back to its last page, the filter lifted kept", () => {
    // Sixty projects, the page of the third fifty asked.
    page.search = "is_contributor=false&offset=100";
    render(
      inFrench(
        <ProjectListGrid
          projects={[]}
          page={{ limit: 50, offset: 100, total: 60 }}
          query={{ sort: undefined, search: undefined }}
          preferences={undefined}
        />,
      ),
    );
    expect(screen.getByText("La page demandée est au-delà de la fin de la liste.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Projets précédents/ })).toHaveAttribute(
      "href",
      "/?is_contributor=false&offset=50",
    );
  });
});

describe("the filter of the list by state", () => {
  it("presses every state when the address names none, and retains a state chosen, back to the first page", async () => {
    const user = userEvent.setup();
    page.search = "offset=50&sort_by=code";
    render(inFrench(<ProjectStateFilter states={[]} />));
    const filter = screen.getByRole("group", { name: "Filtre par état" });
    expect(within(filter).getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(within(filter).getByRole("button", { name: "Perdu" }));
    expect(await lastAddress()).toBe("/?sort_by=code&states=lost");
  });

  it("names each state by its badge, and releases a state pressed", async () => {
    const user = userEvent.setup();
    page.search = "states=pricing,lost";
    render(inFrench(<ProjectStateFilter states={["pricing", "lost"]} />));
    const pricing = screen.getByRole("button", { name: "Chiffrage" });
    expect(pricing).toHaveAttribute("aria-pressed", "true");
    expect(within(pricing).getByText("Chiffrage").parentElement).toHaveClass("bg-state-pricing");
    await user.click(pricing);
    expect(await lastAddress()).toBe("/?states=lost");
    await user.click(screen.getByRole("button", { name: "Tous les états" }));
    expect(await lastAddress()).toBe("/");
  });
});
