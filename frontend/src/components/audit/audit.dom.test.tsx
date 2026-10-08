// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/generated/schema";
import { ListPages } from "@/components/costs/cost-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { type AuditFilters, readAuditFilters } from "./audit-address";
import { type AuditEvent, type AuditSort, NEWEST_FIRST } from "./audit-columns";
import { AuditFilterBar, type AuditFilterBarProps } from "./audit-filters";
import { AuditGrid } from "./audit-grid";

// The server of Next, as far as the screen needs it: the fake back, which keeps the settings of
// the grid a sort writes, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ path: "/admin/audit-log", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.path,
  useSearchParams: () => new URLSearchParams(page.search),
}));

interface Journal {
  items: AuditEvent[];
  meta: components["schemas"]["PaginationMeta"];
}

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";
const witness = example("audit_events") as Journal;
const second = example("audit_events_page") as Journal;
const NEWEST: GridQuery<AuditSort> = { sort: NEWEST_FIRST, search: undefined };
const AUTHORS: AuditFilterBarProps["users"] = [
  { id: CAMILLE, firstName: "Camille", lastName: "Martin" },
];
const PROJECTS: AuditFilterBarProps["projects"] = [
  { id: PROJECT, code: "PRJ-001", label: "Modernisation du poste de commande" },
];
const NAMED: AuditFilterBarProps["named"] = {
  user: undefined,
  project: undefined,
  object: undefined,
};

/** The filters an address asks. */
function filtersOf(search: string): AuditFilters {
  return readAuditFilters(new URLSearchParams(search));
}

/** The screen of the journal, in French, as the page composes it. */
function journal({
  shown = witness,
  query = NEWEST,
  openable = [PROJECT],
  filters = filtersOf(page.search),
  named = NAMED,
  users = AUTHORS,
}: {
  shown?: Journal;
  query?: GridQuery<AuditSort>;
  openable?: readonly string[];
  filters?: AuditFilters;
  named?: AuditFilterBarProps["named"];
  users?: AuditFilterBarProps["users"];
} = {}): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <AuditFilterBar filters={filters} users={users} projects={PROJECTS} named={named} />
        <AuditGrid
          events={shown.items}
          page={shown.meta}
          query={query}
          preferences={undefined}
          openable={openable}
        />
        <ListPages list="audit" page={shown.meta} shown={shown.items.length} />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

/** The grid of the journal. */
function grid() {
  return screen.getByRole("grid", { name: "Journal d’audit" });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  page.search = "";
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

describe("the grid of the journal", () => {
  it("presents each inscription by the names it keeps, and says in its totals how many the server retained", () => {
    render(journal());
    const row = within(grid()).getAllByRole("row")[1];
    expect(row?.textContent).toMatch(
      /^.+Camille MartinApplication d’un importImportcouts-reels-2026-05\.xlsxPRJ-001 · Modernisation du poste de commande01926f3a-7c00-7000-8000-000800000034$/,
    );
    expect(grid().querySelector("tfoot tr")?.textContent).toBe("36 inscriptions");
    // The header of every column is grey, as that of every table (#508).
    expect(grid().querySelector("thead th")?.className).toContain("bg-muted");
  });

  it("asks the server for the dates both ways, never lifting the sort, back to the first page [WF-IHM-0060-A]", async () => {
    page.search = "offset=50";
    const { rerender } = render(journal());
    const header = () => within(grid()).getByRole("columnheader", { name: /^Date/ });
    expect(header()).toHaveAttribute("aria-sort", "descending");
    await userEvent.click(within(header()).getByRole("button"));
    const ascending = "/admin/audit-log?sort_by=occurred_at&sort_order=asc";
    expect(lastAddress()).toBe(ascending);
    page.search = ascending.split("?")[1] ?? "";
    rerender(journal({ query: { sort: { ...NEWEST_FIRST, order: "asc" }, search: undefined } }));
    expect(header()).toHaveAttribute("aria-sort", "ascending");
    await userEvent.click(within(header()).getByRole("button"));
    expect(lastAddress()).toBe("/admin/audit-log?sort_by=occurred_at&sort_order=desc");
  });

  it("sorts no other column: the contract sorts the journal by its dates alone (#550)", () => {
    render(journal());
    for (const name of [
      "Auteur",
      "Action",
      "Nature de l’objet",
      "Objet",
      "Projet",
      "Corrélation",
    ]) {
      expect(
        within(within(grid()).getByRole("columnheader", { name })).queryByRole("button"),
      ).toBeNull();
    }
  });

  it("names a backup, which has no label, by its nature, never by its identifier", () => {
    render(journal());
    // The scheduled backup of 3 June, by the correlation of its inscription.
    const backup = within(grid()).getByRole("row", {
      name: /01926f3a-7c00-7000-8000-000800000033$/,
    });
    expect(backup).toHaveTextContent(/La plateformeSauvegardeSauvegardeSauvegardeHors projet/);
    expect(backup).not.toHaveTextContent("01926f3a-7c00-7000-8000-000000000907");
    expect(
      within(backup).getByRole("link", {
        name: "Histoire de «\u00a0Sauvegarde\u00a0»",
      }),
    ).toBeInTheDocument();
  });

  it("links the object and the project the session may open, and names them alone otherwise", () => {
    const { rerender } = render(journal());
    const revision = within(grid()).getAllByRole("link", { name: "Référence" })[0];
    expect(revision).toHaveAttribute(
      "href",
      `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000101`,
    );
    expect(
      within(grid()).getAllByRole("link", {
        name: "PRJ-001 · Modernisation du poste de commande",
      })[0],
    ).toHaveAttribute("href", `/projects/${PROJECT}`);
    // An import is addressed in a revision the inscription does not name: its name alone.
    expect(within(grid()).queryByRole("link", { name: "couts-reels-2026-05.xlsx" })).toBeNull();
    rerender(journal({ openable: [] }));
    expect(within(grid()).queryByRole("link", { name: "Référence" })).toBeNull();
    expect(
      within(grid()).queryByRole("link", { name: "PRJ-001 · Modernisation du poste de commande" }),
    ).toBeNull();
    // The twelve inscriptions of the project still name it, by its code and its label.
    expect(
      within(grid()).getAllByText("PRJ-001 · Modernisation du poste de commande"),
    ).toHaveLength(12);
  });

  it("leads to the whole history of an object, every other filter lifted, its sort kept, back to the first page", async () => {
    page.search = `sort_by=occurred_at&sort_order=asc&from=2026-01-01T00%3A00%3A00Z&to=2026-06-01T00%3A00%3A00Z&user_id=${CAMILLE}&actor_kind=user&actions=import_apply&project_id=${PROJECT}&offset=10`;
    render(journal({ shown: second }));
    const history = within(grid()).getByRole("link", {
      name: "Histoire de «\u00a0couts-reels-2026-04.xlsx\u00a0»",
    });
    const address =
      "/admin/audit-log?sort_by=occurred_at&sort_order=asc&object_kind=import&object_id=01926f3a-7c00-7000-8000-000000000a07";
    expect(history).toHaveAttribute("href", address);
    await userEvent.click(history);
    expect(lastAddress()).toBe(address);
  });

  it("leads to the pages before and after the one shown, its filters and its sort kept, and breaks no rule of accessibility", async () => {
    page.search = "actions=backup&sort_by=occurred_at&sort_order=asc&offset=10";
    const { container } = render(journal({ shown: second }));
    const pages = screen.getByRole("navigation", { name: "Pages de la liste" });
    expect(within(pages).getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/admin/audit-log?actions=backup&sort_by=occurred_at&sort_order=asc",
    );
    expect(within(pages).getByRole("link", { name: /Page suivante/ })).toHaveAttribute(
      "href",
      "/admin/audit-log?actions=backup&sort_by=occurred_at&sort_order=asc&offset=20",
    );
    await expectAccessible(container);
  });

  it("keeps its grid when the filters retain no inscription", () => {
    const none = { items: [], meta: { limit: 50, offset: 0, total: 0 } };
    page.search = "actions=restore";
    render(journal({ shown: none }));
    expect(grid()).toHaveTextContent("Aucune ligne ne répond à la demande.");
    expect(grid().querySelector("tfoot tr")?.textContent).toBe("Aucune inscription");
  });
});

describe("the filters of the journal", () => {
  describe("by period, in the local time of the workstation", () => {
    const original = process.env.TZ;

    beforeEach(() => {
      process.env.TZ = "Europe/Paris";
    });

    afterEach(() => {
      process.env.TZ = original;
    });

    /** Enter a start of the period, and apply it. */
    async function enterFrom(local: string) {
      const period = screen.getByRole("form", { name: "Période" });
      await userEvent.type(within(period).getByLabelText("Depuis le"), local);
      await userEvent.click(within(period).getByRole("button", { name: "Appliquer" }));
    }

    it("sends an instant entered in summer in universal time, two hours earlier, back to the first page", async () => {
      page.search = "sort_by=occurred_at&sort_order=asc&offset=50";
      render(journal());
      await enterFrom("2026-05-01T08:00");
      expect(lastAddress()).toBe(
        "/admin/audit-log?sort_by=occurred_at&sort_order=asc&from=2026-05-01T06%3A00%3A00.000Z",
      );
    });

    it("sends an instant entered in winter an hour earlier", async () => {
      render(journal());
      await enterFrom("2026-01-15T08:00");
      expect(lastAddress()).toBe("/admin/audit-log?from=2026-01-15T07%3A00%3A00.000Z");
    });

    it("sends the hour that comes twice on the day the clocks go back as its first time", async () => {
      render(journal());
      await enterFrom("2026-10-25T02:30");
      expect(lastAddress()).toBe("/admin/audit-log?from=2026-10-25T00%3A30%3A00.000Z");
    });

    it("shows the instants of the address in the local time once hydrated, and lifts a bound emptied", async () => {
      page.search = "from=2026-05-01T06%3A00%3A00Z&offset=50";
      render(journal());
      const field = screen.getByLabelText("Depuis le");
      expect(field).toHaveValue("2026-05-01T08:00");
      expect(screen.getByLabelText("Avant le")).toHaveAttribute("min", "2026-05-01T08:00");
      await userEvent.clear(field);
      await userEvent.click(screen.getByRole("button", { name: "Appliquer" }));
      expect(lastAddress()).toBe("/admin/audit-log");
    });

    it("sends a bound left untouched as the address names it, never through its field", async () => {
      page.search = "from=2026-05-01T06%3A00%3A30.250Z";
      render(journal({ filters: filtersOf(page.search) }));
      const period = screen.getByRole("form", { name: "Période" });
      await userEvent.type(within(period).getByLabelText("Avant le"), "2026-06-01T00:00");
      await userEvent.click(within(period).getByRole("button", { name: "Appliquer" }));
      expect(lastAddress()).toBe(
        "/admin/audit-log?from=2026-05-01T06%3A00%3A30.250Z&to=2026-05-31T22%3A00%3A00.000Z",
      );
    });

    it("shows anew a period the address changes, the form kept and the focus with it", async () => {
      page.search = "from=2026-05-01T06%3A00%3A00Z";
      const { rerender } = render(journal());
      const field = screen.getByLabelText("Depuis le");
      await userEvent.clear(field);
      await userEvent.type(field, "2026-02-01T10:00");
      expect(field).toHaveFocus();
      // Back in the history: the address names another period, which the field shows.
      page.search = "from=2026-03-01T06%3A00%3A00Z";
      rerender(journal());
      expect(screen.getByLabelText("Depuis le")).toBe(field);
      expect(field).toHaveValue("2026-03-01T07:00");
      expect(field).toHaveFocus();
      // Forward again, to the period the entry was made over: it shows that period, the entry
      // given up.
      page.search = "from=2026-05-01T06%3A00%3A00Z";
      rerender(journal());
      expect(field).toHaveValue("2026-05-01T08:00");
    });
  });

  it("filter by kind of author under the name of the contract, back to the first page", async () => {
    page.search = "offset=50";
    render(journal());
    const kinds = screen.getByRole("group", { name: "Filtrer par nature d’auteur" });
    expect(within(kinds).getByRole("button", { name: "Tous les auteurs" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(kinds).getByRole("button", { name: "La plateforme" }));
    expect(lastAddress()).toBe("/admin/audit-log?actor_kind=platform");
  });

  it("filter by author, an account the session may read, back to the first page", async () => {
    page.search = "offset=50";
    render(journal());
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Auteur" }), CAMILLE);
    expect(lastAddress()).toBe(`/admin/audit-log?user_id=${CAMILLE}`);
  });

  it("keep an author no choice offers under the name the inscriptions give, to be cleared", async () => {
    page.search = `user_id=${CAMILLE}&offset=50`;
    render(journal({ users: [], named: { ...NAMED, user: "Camille Martin" } }));
    const author = screen.getByRole("combobox", { name: "Auteur" });
    expect(author).toHaveValue(CAMILLE);
    expect(within(author).getByRole("option", { selected: true })).toHaveTextContent(
      "Camille Martin",
    );
    await userEvent.selectOptions(author, "");
    expect(lastAddress()).toBe("/admin/audit-log");
  });

  it("filter by actions, checked in a menu in the order of the contract, back to the first page", async () => {
    page.search = "actions=backup&offset=50";
    render(journal());
    const opener = screen.getByRole("button", { name: "Filtrer par action\u00a0: 1 action" });
    await userEvent.click(opener);
    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitemcheckbox", { name: "Sauvegarde" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await userEvent.click(
      within(menu).getByRole("menuitemcheckbox", { name: "Marquage d’une révision" }),
    );
    expect(lastAddress()).toBe("/admin/audit-log?actions=revision_mark%2Cbackup");
    // The menu stays open while actions are checked; one lifts them all.
    await userEvent.click(
      within(screen.getByRole("menu")).getByRole("menuitem", { name: "Toutes les actions" }),
    );
    expect(lastAddress()).toBe("/admin/audit-log");
  });

  it("filter by project, one the session may open, back to the first page", async () => {
    page.search = "offset=50";
    render(journal());
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Projet" }), PROJECT);
    expect(lastAddress()).toBe(`/admin/audit-log?project_id=${PROJECT}`);
  });

  it("filter by kind of object, back to the first page", async () => {
    page.search = "offset=50";
    render(journal());
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Nature de l’objet" }),
      "revision",
    );
    expect(lastAddress()).toBe("/admin/audit-log?object_kind=revision");
  });

  it("name the object whose history the address asks, and lift it, its kind kept, the focus given to the filter of the kind", async () => {
    const object = "01926f3a-7c00-7000-8000-000000000101";
    page.search = `object_kind=revision&object_id=${object}&offset=50`;
    render(journal({ named: { ...NAMED, object: { label: "Référence", kind: "revision" } } }));
    const lift = screen.getByRole("link", {
      name: "Lever le filtre sur «\u00a0Référence\u00a0»",
    });
    expect(lift).toHaveAttribute("href", "/admin/audit-log?object_kind=revision");
    await userEvent.click(lift);
    expect(lastAddress()).toBe("/admin/audit-log?object_kind=revision");
    expect(screen.getByRole("combobox", { name: "Nature de l’objet" })).toHaveFocus();
  });

  it("leave the focus where it is when the lifting opens in a tab, the browser's to follow", async () => {
    page.search = "object_kind=revision&object_id=01926f3a-7c00-7000-8000-000000000101";
    render(journal({ named: { ...NAMED, object: { label: "Référence", kind: "revision" } } }));
    const lift = screen.getByRole("link", {
      name: "Lever le filtre sur «\u00a0Référence\u00a0»",
    });
    // The page lets the browser follow a click with Ctrl: no navigation of its own, no focus moved.
    const user = userEvent.setup();
    await user.keyboard("{Control>}");
    await user.click(lift);
    await user.keyboard("{/Control}");
    expect(router.push).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox", { name: "Nature de l’objet" })).not.toHaveFocus();
  });

  it("name a backup whose history the address asks by its nature", () => {
    page.search = "object_kind=backup&object_id=01926f3a-7c00-7000-8000-000000000907";
    render(journal({ named: { ...NAMED, object: { label: null, kind: "backup" } } }));
    expect(
      screen.getByRole("link", { name: "Lever le filtre sur «\u00a0Sauvegarde\u00a0»" }),
    ).toBeInTheDocument();
  });

  it("offer no filter of authors when no account may be chosen and none is", () => {
    render(journal({ users: [] }));
    expect(screen.queryByRole("combobox", { name: "Auteur" })).toBeNull();
  });
});
