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
import { DefaultStatesFilter } from "./project-list";

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

/** The six states of the table of the specification (3.3.2): code, then label in each language. */
const SPEC_STATES = [
  ["created", "Créé", "Created"],
  ["pricing", "Chiffrage", "Pricing"],
  ["in_progress", "En cours", "In progress"],
  ["completed", "Terminé", "Completed"],
  ["lost", "Perdu", "Lost"],
  ["abandoned", "Abandonné", "Abandoned"],
] as const;

/** A part of the home, in a language, under the address of the screen. */
function inLocale(locale: "fr" | "en", children: ReactNode) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
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
      query={{ sort: undefined, search: undefined, size: undefined }}
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
    expect(within(witness ?? document.body).getByRole("img", { name: "En cours" })).toBeVisible();
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
          query={{ sort: undefined, search: undefined, size: undefined }}
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

describe("the states of the list, those of the table of the specification", () => {
  it.each(["fr", "en"] as const)(
    "the state column of the list writes the six labels of the table and no other in %s [WF-CYC-0010-A]",
    (locale) => {
      const projects = SPEC_STATES.map(([state], index) =>
        listedProject({
          ...(example("project") as Schemas["Project"]),
          project_id: `id-${String(index)}`,
          label: `P${String(index)}`,
          state,
        }),
      );
      render(
        inLocale(
          locale,
          <ProjectListGrid
            projects={projects}
            page={{ limit: 50, offset: 0, total: 6 }}
            query={{ sort: undefined, search: undefined, size: undefined }}
            preferences={undefined}
          />,
        ),
      );
      const rows = within(screen.getByRole("grid")).getAllByRole("row");
      SPEC_STATES.forEach(([, fr, en], index) => {
        const row = rows.find((each) => within(each).queryByText(`P${String(index)}`) !== null);
        if (row === undefined) {
          throw new Error(`the row of P${String(index)} is missing`);
        }
        expect(within(row).getByRole("img")).toHaveAccessibleName(locale === "fr" ? fr : en);
      });
    },
  );

  it.each(["fr", "en"] as const)(
    "the filter of the home offers the six states and no other, in %s [WF-CYC-0010-A]",
    (locale) => {
      render(inLocale(locale, <ProjectStateFilter states={[]} />));
      const filter = screen.getByRole("group", {
        name: locale === "fr" ? "Filtre par état" : "Filter by state",
      });
      expect(
        within(filter)
          .getAllByRole("button")
          .map((button) => button.textContent),
      ).toEqual([
        locale === "fr" ? "Tous les états" : "Every state",
        ...SPEC_STATES.map(([, fr, en]) => (locale === "fr" ? fr : en)),
      ]);
    },
  );

  it.each(SPEC_STATES)(
    "the filter of the home writes the code %s of its state in the address, pressed from the default [WF-CYC-0010-A]",
    async (code, fr) => {
      const user = userEvent.setup();
      render(inFrench(<ProjectStateFilter states={[]} />));
      // Pressed from the default, where every state is pressed, a button retains its state alone.
      await user.click(screen.getByRole("button", { name: fr }));
      expect(await lastAddress()).toBe(`/?states=${code}`);
    },
  );
});

describe("the filter of the list by state", () => {
  it("says the states by default, Créé, Chiffrage and En cours (WF-IHM-0130)", () => {
    render(inFrench(<DefaultStatesFilter />));
    const filter = screen.getByRole("region", { name: "Filtre par défaut de la liste par état" });
    for (const state of ["Créé", "Chiffrage", "En cours"]) {
      expect(within(filter).getByText(state)).toBeVisible();
    }
    expect(within(filter).queryByText("Perdu")).toBeNull();
  });

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
    expect(within(pricing).getByRole("img", { name: "Chiffrage" })).toBeVisible();
    await user.click(pricing);
    expect(await lastAddress()).toBe("/?states=lost");
    await user.click(screen.getByRole("button", { name: "Tous les états" }));
    expect(await lastAddress()).toBe("/?states=all");
  });

  it("lifts the filter when the last state is chosen too: every state is every project", async () => {
    const user = userEvent.setup();
    page.search = "states=created%2Cpricing%2Cin_progress%2Ccompleted%2Clost&sort_by=code";
    render(
      inFrench(
        <ProjectStateFilter states={["created", "pricing", "in_progress", "completed", "lost"]} />,
      ),
    );
    await user.click(screen.getByRole("button", { name: "Abandonné" }));
    expect(await lastAddress()).toBe("/?states=all&sort_by=code");
  });

  it("goes on from the states retained when the address names none, and lifts them by « Tous les états » (WF-IHM-0130)", async () => {
    const user = userEvent.setup();
    page.search = "sort_by=code";
    render(inFrench(<ProjectStateFilter states={["created", "pricing", "in_progress"]} />));
    await user.click(screen.getByRole("button", { name: "Perdu" }));
    expect(await lastAddress()).toBe(
      "/?sort_by=code&states=created%2Cpricing%2Cin_progress%2Clost",
    );
    await user.click(screen.getByRole("button", { name: "Tous les états" }));
    expect(await lastAddress()).toBe("/?sort_by=code&states=all");
  });

  it("turns a page from a state chosen under way to the first page of the projects", async () => {
    const user = userEvent.setup();
    page.search = "offset=100";
    render(
      inFrench(
        <>
          <ProjectStateFilter states={[]} />
          <ProjectListGrid
            projects={[]}
            page={{ limit: 50, offset: 100, total: 160 }}
            query={{ sort: undefined, search: undefined, size: undefined }}
            preferences={undefined}
          />
        </>,
      ),
    );
    await user.click(screen.getByRole("button", { name: "Perdu" }));
    expect(await lastAddress()).toBe("/?states=lost");
    // The state asked and not arrived: the projects read otherwise start from their first page.
    await user.click(screen.getByRole("link", { name: /Projets précédents/ }));
    expect(await lastAddress()).toBe("/?states=lost");
  });
});
