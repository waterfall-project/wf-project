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
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { readCostFilters } from "./address";
import { CostFilterBar, type SubprojectChoice } from "./cost-filters";
import { costRow, type CostRows, type CostSortColumn, type ListPage } from "./cost-grid";
import { ListPages } from "./cost-pages";
import { CostSummary } from "./cost-totals";
import { CostsGrid } from "./costs-grid";
import { type CostImport, ImportJournal } from "./import-journal";

// The server of Next, as far as the screen needs it: the preferences it writes, the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/projects/p/revisions/r/actual-costs";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** What the server answers of the actual costs, as an example of the contract gives it. */
interface CostList {
  readonly items: components["schemas"]["ActualCostLine"][];
  readonly totals: CostRows["totals"];
  readonly last_import_at: string | null;
  readonly meta: ListPage;
}

const NO_QUERY: GridQuery<CostSortColumn> = { sort: undefined, search: undefined };
// The spaces of the French formats: between thousands.
const NARROW = " ";
const COMMAND = "01926f3a-7c00-7000-8000-000000000801";
const SUBPROJECTS: readonly SubprojectChoice[] = [
  { id: COMMAND, code: "SP-CMD", label: "Poste de commande" },
];

/** An example of the actual costs, as the contract gives it. */
function listOf(name: "actual_costs" | "actual_costs_page" | "actual_costs_subproject") {
  return example(name) as CostList;
}

/** The lines of an example, as the page hands them to the grid. */
function costsOf(name: Parameters<typeof listOf>[0]): CostRows {
  const list = listOf(name);
  return { items: list.items.map(costRow), totals: list.totals };
}

/** A part of the screen, in a language. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** The grid of the actual costs on an example, as the address asked it. */
function costsGrid(costs: CostRows, query: GridQuery<CostSortColumn> = NO_QUERY) {
  return inLanguage(<CostsGrid costs={costs} query={query} preferences={undefined} />);
}

/** The grid of the actual costs. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Coûts réels" });
}

/** The cells of the row of a document, by its number. */
function cellsOf(number: string): HTMLElement[] {
  const row = within(grid())
    .getAllByRole("row")
    .find((candidate) => candidate.querySelector("td")?.textContent === number);
  return [...(row?.querySelectorAll("td") ?? [])];
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the grid of the actual costs", () => {
  it("presents the four attributes of each line, and the columns of the file kept, as imported [WF-CRE-0010-A]", async () => {
    const { container } = render(costsGrid(costsOf("actual_costs")));
    expect(
      within(grid())
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual([
      "N° de pièce",
      "Date de pièce",
      "Montant",
      "Sous-projet",
      "Périmètre suivi",
      "Motif de l’exclusion",
      "Colonnes conservées du fichier",
    ]);
    const cells = cellsOf("FA-2026-0412");
    expect(cells.slice(0, 5).map((each) => each.textContent)).toEqual([
      "FA-2026-0412",
      "21/04/2026",
      `1${NARROW}800,00`,
      "Hors sous-projet",
      "Suivie",
    ]);
    const kept = within(cells[6] ?? document.body);
    expect(kept.getByText("Fournisseur")).toBeVisible();
    expect(kept.getByText("Câbles du Rhône")).toBeVisible();
    expect(kept.getByText("Élément d'OTP")).toBeVisible();
    expect(kept.getByText("WF.PRJ-001/SP-CAB")).toBeVisible();
    await expectAccessible(container);
  });

  it("accepts a line of negative amount, which lessens the actual cost [WF-CRE-0010-A]", () => {
    render(costsGrid(costsOf("actual_costs")));
    expect(cellsOf("AV-2026-0388")[2]).toHaveTextContent("-200,00");
  });

  it("shows a line whose sub-project is unknown as charged to the project alone [WF-CRE-0020-A]", () => {
    render(costsGrid(costsOf("actual_costs")));
    for (const number of ["FA-2026-0412", "AV-2026-0388", "FA-2026-0301", "FA-2026-0295"]) {
      expect(cellsOf(number)[3]).toHaveTextContent("Hors sous-projet");
    }
  });

  it("names the sub-project of a line by its code and its label, as the server resolves them [WF-CRE-0020-A]", () => {
    render(costsGrid(costsOf("actual_costs_subproject")));
    expect(cellsOf("FA-2026-0521")[3]).toHaveTextContent("SP-CMDPoste de commande");
  });

  it("keeps an excluded line visible, said excluded in words, with the reason of its exclusion [WF-CRE-0030-A]", () => {
    render(costsGrid(costsOf("actual_costs")));
    const cells = cellsOf("FA-2026-0295");
    expect(cells[4]).toHaveTextContent("Exclue");
    expect(cells[5]).toHaveTextContent("Réception du client, non budgétée");
  });

  it("shows in its totals row the general total of the lines retained the server gives, never a sum of the page [WF-CRE-0040-A]", () => {
    render(costsGrid(costsOf("actual_costs_page")));
    const total = within(grid()).getAllByRole("row").at(-1);
    expect(total).toHaveTextContent(/^Total général des lignes retenues\s*3\s650,00$/);
  });

  it("offers no search, which the server does not make, and asks it to sort by the amount", async () => {
    render(costsGrid(costsOf("actual_costs")));
    expect(screen.queryByRole("search")).toBeNull();
    const heading = within(grid()).getByRole("columnheader", { name: /Montant/ });
    await userEvent.click(within(heading).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?sort_by=amount&sort_order=asc`, {
        scroll: false,
      });
    });
  });

  it("asks the server to sort by the scope and by the reason, and offers no sort on the columns kept from the file [WF-IHM-0060-A]", async () => {
    render(costsGrid(costsOf("actual_costs")));
    const sortBy = async (name: RegExp, column: string) => {
      const heading = within(grid()).getByRole("columnheader", { name });
      await userEvent.click(within(heading).getByRole("button"));
      await waitFor(() => {
        expect(router.push).toHaveBeenLastCalledWith(
          `${PATHNAME}?sort_by=${column}&sort_order=asc`,
          { scroll: false },
        );
      });
    };
    await sortBy(/Périmètre suivi/, "in_tracked_scope");
    await sortBy(/Motif de l’exclusion/, "excluded_reason");
    const kept = within(grid()).getByRole("columnheader", { name: /Colonnes conservées/ });
    expect(within(kept).queryByRole("button")).toBeNull();
  });

  it("is named and headed in English too", () => {
    render(
      inLanguage(
        <CostsGrid costs={costsOf("actual_costs")} query={NO_QUERY} preferences={undefined} />,
        "en",
      ),
    );
    const english = screen.getByRole("grid", { name: "Actual costs" });
    expect(within(english).getByRole("columnheader", { name: /Document no\./ })).toBeVisible();
    expect(within(english).getAllByText("No subproject")).toHaveLength(4);
    expect(within(english).getByText("Excluded")).toBeVisible();
  });
});

describe("the totals of the actual costs", () => {
  it("presents the total of the tracked scope, the total excluded and the general total the server gives, and the date of the last import [WF-CRE-0040-A] [WF-CRE-0050-A]", () => {
    const list = listOf("actual_costs");
    render(inLanguage(<CostSummary totals={list.totals} lastImport={list.last_import_at} />));
    const totals = screen.getByRole("region", { name: "Totaux des lignes retenues" });
    expect(totals).toHaveTextContent(
      /Périmètre suivi.*3\s000,00.*Exclu du périmètre suivi.*650,00.*Total général.*3\s650,00/,
    );
    expect(within(totals).getAllByRole("img", { name: "Calculé" })).toHaveLength(3);
    expect(totals).toHaveTextContent(/Dernier import.*4 mai 2026/);
  });

  it("says no import has been made yet, rather than a date", () => {
    const list = example("actual_costs_empty") as CostList;
    render(inLanguage(<CostSummary totals={list.totals} lastImport={list.last_import_at} />));
    expect(screen.getByRole("region", { name: "Totaux des lignes retenues" })).toHaveTextContent(
      /Dernier import\s*Aucun import/,
    );
  });
});

describe("the filters of the actual costs", () => {
  /** Render the filters as the address asks them. */
  function renderFilters(search = "") {
    page.search = search;
    const address = new URLSearchParams(search);
    return render(
      inLanguage(
        <CostFilterBar
          filters={readCostFilters(address)}
          subproject={address.get("subproject_id") ?? undefined}
          subprojects={SUBPROJECTS}
        />,
      ),
    );
  }

  it("asks the server for the excluded lines alone, by the address, back to the first page [WF-CRE-0040-A]", async () => {
    const { container } = renderFilters("sort_by=amount&sort_order=asc&offset=50");
    const scope = screen.getByRole("group", { name: "Périmètre" });
    expect(within(scope).getByRole("button", { name: "Toutes les lignes" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(scope).getByRole("button", { name: "Exclues" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?sort_by=amount&sort_order=asc&in_tracked_scope=false`,
      { scroll: false },
    );
    await expectAccessible(container);
  });

  it("lifts the filter on the scope, and presses the scope the address asks", async () => {
    renderFilters("in_tracked_scope=true");
    const scope = screen.getByRole("group", { name: "Périmètre" });
    expect(within(scope).getByRole("button", { name: "Suivies" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(scope).getByRole("button", { name: "Toutes les lignes" }));
    expect(router.push).toHaveBeenLastCalledWith(PATHNAME, { scroll: false });
  });

  it("asks the server for a sub-project, or for the lines charged to the project alone [WF-CRE-0040-A]", async () => {
    renderFilters();
    const select = screen.getByRole("combobox", { name: "Sous-projet" });
    await userEvent.selectOptions(select, "SP-CMD — Poste de commande");
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?subproject_id=${COMMAND}`, {
      scroll: false,
    });
    await userEvent.selectOptions(select, "Hors sous-projet");
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?subproject_id=unassigned`, {
      scroll: false,
    });
  });

  it("asks the server for the documents of a period, and lifts it when emptied [WF-CRE-0040-A]", async () => {
    const { unmount } = renderFilters("in_tracked_scope=true");
    await userEvent.type(screen.getByLabelText("Pièces du"), "2026-04-01");
    await userEvent.type(screen.getByLabelText("Pièces jusqu’au"), "2026-04-30");
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?in_tracked_scope=true&from=2026-04-01&to=2026-04-30`,
      { scroll: false },
    );
    unmount();
    renderFilters("from=2026-04-01&to=2026-04-30");
    expect(screen.getByLabelText("Pièces du")).toHaveValue("2026-04-01");
    await userEvent.clear(screen.getByLabelText("Pièces du"));
    await userEvent.clear(screen.getByLabelText("Pièces jusqu’au"));
    await userEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    expect(router.push).toHaveBeenLastCalledWith(PATHNAME, { scroll: false });
  });

  it("keeps each bound of the period on its side of the other", async () => {
    renderFilters("from=2026-04-01&to=2026-04-30");
    expect(screen.getByLabelText("Pièces du")).toHaveAttribute("max", "2026-04-30");
    expect(screen.getByLabelText("Pièces jusqu’au")).toHaveAttribute("min", "2026-04-01");
    await userEvent.clear(screen.getByLabelText("Pièces jusqu’au"));
    expect(screen.getByLabelText("Pièces du")).not.toHaveAttribute("max");
  });

  it("keeps chosen a sub-project the address names that the project does not hold, under its value", () => {
    const unknown = "01926f3a-7c00-7000-8000-000000000899";
    renderFilters(`subproject_id=${unknown}`);
    const select = screen.getByRole("combobox", { name: "Sous-projet" });
    expect(select).toHaveValue(unknown);
    expect(within(select).getByRole("option", { selected: true })).toHaveTextContent(unknown);
  });

  it("does not ask a date or a scope the contract would refuse", () => {
    expect(
      readCostFilters(new URLSearchParams("in_tracked_scope=yes&from=avril&to=2026-4-1")),
    ).toEqual({ scope: undefined, from: undefined, to: undefined });
  });

  it("does not ask a date the calendar does not hold", () => {
    expect(readCostFilters(new URLSearchParams("from=2026-02-30&to=2026-13-01"))).toEqual({
      scope: undefined,
      from: undefined,
      to: undefined,
    });
    expect(readCostFilters(new URLSearchParams("from=2028-02-29"))).toMatchObject({
      from: "2028-02-29",
    });
  });
});

describe("the pages of a list the server pages", () => {
  it("leads to the page before and the page after the one shown, the rest of the address kept [WF-CRE-0040-A]", () => {
    page.search = "in_tracked_scope=true&offset=1";
    const list = listOf("actual_costs_page");
    render(inLanguage(<ListPages list="costs" page={list.meta} shown={list.items.length} />));
    const pages = screen.getByRole("navigation", { name: "Pages des coûts réels" });
    expect(within(pages).getByRole("link", { name: /Lignes précédentes/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?in_tracked_scope=true`,
    );
    expect(within(pages).getByRole("link", { name: /Lignes suivantes/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?in_tracked_scope=true&offset=2`,
    );
  });

  it("shows no way through a list the page holds whole", () => {
    const list = listOf("actual_costs");
    const { container } = render(
      inLanguage(<ListPages list="costs" page={list.meta} shown={list.items.length} />),
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("says a page asked beyond the end, and leads back to the last page", () => {
    const beyond = example("cost_imports_beyond") as {
      readonly items: [];
      readonly meta: ListPage;
    };
    render(inLanguage(<ListPages list="imports" page={beyond.meta} shown={beyond.items.length} />));
    expect(screen.getByText("La page demandée est au-delà de la fin du journal.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Imports plus récents/ })).toHaveAttribute(
      "href",
      PATHNAME,
    );
  });

  it("turns a page from the address last asked: a sort under way is kept, from the first page", async () => {
    page.search = "offset=1";
    const list = listOf("actual_costs_page");
    render(
      inLanguage(
        <PendingAddress>
          <CostsGrid
            costs={costsOf("actual_costs_page")}
            query={NO_QUERY}
            preferences={undefined}
          />
          <ListPages list="costs" page={list.meta} shown={list.items.length} />
        </PendingAddress>,
      ),
    );
    const heading = within(grid()).getByRole("columnheader", { name: /Date de pièce/ });
    await userEvent.click(within(heading).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?sort_by=document_date&sort_order=asc`,
        { scroll: false },
      );
    });
    await userEvent.click(screen.getByRole("link", { name: /Lignes suivantes/ }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?sort_by=document_date&sort_order=asc`,
      { scroll: false },
    );
  });

  it("turns a page of the costs from a filter under way to their first page, and keeps the page of the journal", async () => {
    page.search = "offset=1&imports_offset=12";
    const list = listOf("actual_costs_page");
    const journal = example("cost_imports_beyond") as { readonly meta: ListPage };
    render(
      inLanguage(
        <PendingAddress>
          <CostFilterBar
            filters={readCostFilters(new URLSearchParams(page.search))}
            subproject={undefined}
            subprojects={SUBPROJECTS}
          />
          <ListPages list="costs" page={list.meta} shown={list.items.length} />
          <ListPages list="imports" page={journal.meta} shown={0} />
        </PendingAddress>,
      ),
    );
    const scope = screen.getByRole("group", { name: "Périmètre" });
    await userEvent.click(within(scope).getByRole("button", { name: "Exclues" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?imports_offset=12&in_tracked_scope=false`,
      { scroll: false },
    );
    await userEvent.click(screen.getByRole("link", { name: /Lignes suivantes/ }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?imports_offset=12&in_tracked_scope=false`,
      { scroll: false },
    );
    await userEvent.click(screen.getByRole("link", { name: /Imports plus récents/ }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?in_tracked_scope=false`, {
      scroll: false,
    });
  });
});

describe("the journal of the imports", () => {
  /** The journal of an example. */
  function journalOf(name: "cost_imports" | "cost_imports_periods" | "cost_imports_empty") {
    return example(name) as { readonly items: CostImport[]; readonly meta: ListPage };
  }

  it("presents each import with its date, its author, the period extracted and its counts of lines [WF-CRE-0050-A]", async () => {
    const journal = journalOf("cost_imports");
    const { container } = render(
      inLanguage(<ImportJournal imports={journal.items} page={journal.meta} />),
    );
    const table = screen.getByRole("table", { name: "Journal des imports" });
    const rows = within(table).getAllByRole("row");
    expect(rows.map((row) => row.textContent)).toEqual([
      "DateParPériode extraiteCrééesMises à jourIgnorées",
      expect.stringMatching(/^4 mai 2026.*Camille Martindu 01\/04\/2026 au 30\/04\/2026201$/),
      expect.stringMatching(/^3 avr\. 2026.*Camille Martindu 01\/03\/2026 au 31\/03\/2026200$/),
    ]);
    await expectAccessible(container);
  });

  it("says a period the API does not give, or gives a bound of, and its counts in the format of the language [WF-CRE-0050-A]", () => {
    const journal = journalOf("cost_imports_periods");
    render(inLanguage(<ImportJournal imports={journal.items} page={journal.meta} />));
    const rows = within(screen.getByRole("table", { name: "Journal des imports" }))
      .getAllByRole("row")
      .slice(1);
    expect(within(rows[0] ?? document.body).getByText("à partir du 01/05/2026")).toBeVisible();
    expect(within(rows[1] ?? document.body).getByText("jusqu’au 30/04/2026")).toBeVisible();
    expect(rows[1]?.querySelectorAll("td")[5]).toHaveTextContent(/^12\s345$/);
    expect(within(rows[2] ?? document.body).getByText("Non renseignée")).toBeVisible();
  });

  it("writes its counts in English the English way", () => {
    const journal = journalOf("cost_imports_periods");
    render(inLanguage(<ImportJournal imports={journal.items} page={journal.meta} />, "en"));
    expect(screen.getByText("12,345")).toBeVisible();
    expect(screen.getByText("until 30/04/2026")).toBeVisible();
  });

  it("says no import was ever made", () => {
    const journal = journalOf("cost_imports_empty");
    render(inLanguage(<ImportJournal imports={journal.items} page={journal.meta} />));
    expect(screen.getByRole("region", { name: "Journal des imports" })).toHaveTextContent(
      "Aucun coût réel n’a encore été importé.",
    );
  });
});
