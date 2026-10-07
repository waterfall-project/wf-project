// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import type { RiskState } from "./address";
import { riskRow, type RiskRows, type RiskSortColumn } from "./risk-grid";
import { RisksGrid } from "./risks-grid";
import { RiskStateFilter } from "./state-filter";

// The server of Next, as far as the grid needs it: the preferences it writes, the address it reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/projects/p/revisions/r/risks";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type RiskList = { readonly items: components["schemas"]["Risk"][] } & Pick<RiskRows, "totals">;

const NO_QUERY: GridQuery<RiskSortColumn> = { sort: undefined, search: undefined };
// The spaces of the French formats: before a sign, and between thousands.
const NBSP = "\u00a0";
const NARROW = "\u202f";
const CABLING = "01926f3a-7c00-7000-8000-000000000751";

/** The risks of an example, as the page hands them to the grid. */
function risksOf(name: "risks" | "risks_empty"): RiskRows {
  const list = example(name) as RiskList;
  return { items: list.items.map(riskRow), totals: list.totals };
}

/** The grid of the risks on an example, in a language, as the address asked it. */
function risksGrid(risks: RiskRows, locale: Locale, query: GridQuery<RiskSortColumn> = NO_QUERY) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <RisksGrid risks={risks} query={query} preferences={undefined} />
    </NextIntlClientProvider>
  );
}

/** Render the grid of the risks on an example, in a language. */
function renderRisks(risks: RiskRows = risksOf("risks"), locale: Locale = "fr") {
  return render(risksGrid(risks, locale));
}

/** The grid of the risks. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Registre des risques" });
}

/** The rows of the answer rendered, between the header and the totals. */
function bodyRows(): HTMLElement[] {
  return within(grid()).getAllByRole("row").slice(1, -1);
}

/** The cells of the row of a risk, by its label. */
function cellsOf(label: string): HTMLElement[] {
  const row = bodyRows().find((candidate) =>
    within(candidate).queryByRole("link", { name: label }),
  );
  return [...(row?.querySelectorAll("td") ?? [])];
}

/** A cell of the row of a risk, by its place in the row. */
function cell(label: string, position: number): HTMLElement {
  const found = cellsOf(label)[position];
  if (found === undefined) {
    throw new Error(`no cell ${position.toString()} in the row of ${label}`);
  }
  return found;
}

// The places of the columns in a row: label, probability, severity, provision, state, review, cell.
const SEVERITY = 2;
const PROVISION = 3;
const ZONE = 6;

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

describe("the grid of the risks", () => {
  it("presents the six columns of the register and the cell of the matrix, each risk as the API gives it [WF-RIS-0040-A]", async () => {
    const { container } = renderRisks();
    expect(
      within(grid())
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual(["Libellé", "Probabilité", "Gravité", "Provision", "État", "Dernier réexamen", ""]);
    expect(within(grid()).getByRole("columnheader", { name: /Case de la matrice/ })).toBeVisible();
    expect(cellsOf("Risque de reprise du câblage").map((each) => each.textContent)).toEqual([
      "Risque de reprise du câblage",
      `40${NBSP}%`,
      `1${NARROW}250,00`,
      "500,00",
      "Identifié",
      "02/03/2026",
      "",
    ]);
    expect(cell("Retard de livraison des armoires", 4)).toHaveTextContent("Survenu");
    expect(cell("Indisponibilité de l'automaticien", 4)).toHaveTextContent("Écarté");
    await expectAccessible(container);
  });

  it("leads from the label of a risk to its detail — its notes and the history of its reviews —, the rest of the address kept [WF-RIS-0040-A]", () => {
    page.search = "states=identified&sort_by=provision_amount&sort_order=desc";
    renderRisks();
    const link = within(grid()).getByRole("link", { name: "Risque de reprise du câblage" });
    expect(link).toHaveAttribute(
      "href",
      `${PATHNAME}?states=identified&sort_by=provision_amount&sort_order=desc&risk=${CABLING}`,
    );
    // Out of the order of tabulation: the grid is one stop.
    expect(link).toHaveAttribute("tabindex", "-1");
    expect(link).not.toHaveAttribute("aria-current");
  });

  it("says which risk the detail shows", () => {
    page.search = `risk=${CABLING}`;
    renderRisks();
    expect(
      within(grid()).getByRole("link", { name: "Risque de reprise du câblage" }),
    ).toHaveAttribute("aria-current", "true");
    expect(
      within(grid()).getByRole("link", { name: "Retard de livraison des armoires" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("follows the label of a risk to its detail from the keyboard, Enter on its cell", async () => {
    renderRisks();
    const link = within(grid()).getByRole("link", { name: "Risque de reprise du câblage" });
    const followed = vi.fn((event: Event) => {
      event.preventDefault();
    });
    link.addEventListener("click", followed);
    cell("Risque de reprise du câblage", 0).focus();
    await userEvent.keyboard("{Enter}");
    expect(followed).toHaveBeenCalledTimes(1);
  });

  it("presents the severity and the provision of a risk as computed, and takes no entry of them, naming what they depend on [WF-IHM-0030-A]", async () => {
    renderRisks();
    for (const name of [/^Calculé\s*Gravité/, /^Calculé\s*Provision/]) {
      expect(within(grid()).getByRole("columnheader", { name })).toBeVisible();
    }
    const severity = cell("Risque de reprise du câblage", SEVERITY);
    const provision = cell("Risque de reprise du câblage", PROVISION);
    expect(severity).toHaveAccessibleName(/^Calculé/);
    expect(provision).toHaveAccessibleName(/^Calculé/);

    // Typed into, from the keyboard: refused, naming what the value depends on, nothing entered.
    severity.focus();
    await userEvent.keyboard("9");
    const refusal = screen.getByRole("dialog", { name: "Valeur calculée" });
    expect([...refusal.querySelectorAll("p")].map((p) => p.textContent)).toEqual([
      "Valeur calculée",
      `Gravité ne se saisit pas${NBSP}: Waterfall calcule cette valeur.`,
      "La gravité d’un risque est le total de son devis propre.",
    ]);
    expect(screen.queryByRole("textbox")).toBeNull();
    await userEvent.keyboard("{Escape}");

    // Double-clicked: refused as well, never an entry.
    await userEvent.dblClick(provision);
    expect(screen.getByRole("dialog", { name: "Valeur calculée" })).toHaveTextContent(
      "Provision ne se saisit pas : Waterfall calcule cette valeur." +
        "La provision d’un risque est sa gravité pondérée par sa probabilité.",
    );
    expect(screen.queryByRole("textbox")).toBeNull();
    // Nothing is asked of the server: the risk names itself what they depend on.
    expect((server.client as FakeClient).calls).toEqual([]);
  });

  it("presents no cell of the grid for entry: a risk is entered by the epic of the risks", async () => {
    renderRisks();
    for (const position of [0, 1, 4, 5]) {
      cell("Risque de reprise du câblage", position).focus();
      await userEvent.keyboard("{F2}");
      expect(screen.queryByRole("textbox")).toBeNull();
    }
  });

  it("gives each risk the cell of the matrix the server classes it in, by a shape and a name, never by colour alone [WF-IHM-0070-A]", () => {
    renderRisks();
    const zone = (label: string) =>
      within(cell(label, ZONE)).getByRole("img").getAttribute("aria-label");
    expect(zone("Risque de reprise du câblage")).toBe("Vigilance");
    expect(zone("Retard de livraison des armoires")).toBe("Nominal");
    expect(zone("Indisponibilité de l'automaticien")).toBe("Vigilance");
  });

  it("asks the server to sort by the provision, from the heaviest to the lightest [WF-RIS-0040-A]", async () => {
    const { rerender } = renderRisks();
    const heading = () => within(grid()).getByRole("columnheader", { name: /Provision/ });
    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?sort_by=provision_amount&sort_order=asc`,
        { scroll: false },
      );
    });
    // The page reads anew, sorted as the address asks.
    page.search = "sort_by=provision_amount&sort_order=asc";
    rerender(
      risksGrid(risksOf("risks"), "fr", {
        sort: { column: "provision_amount", order: "asc" },
        search: undefined,
      }),
    );
    expect(heading()).toHaveAttribute("aria-sort", "ascending");
    await userEvent.click(within(heading()).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?sort_by=provision_amount&sort_order=desc`,
        { scroll: false },
      );
    });
  });

  it("shows in its totals row the general total of the provisions the server gives, never a sum [WF-RIS-0040-A]", () => {
    renderRisks();
    const totals = within(grid()).getAllByRole("row").at(-1);
    expect(totals).toHaveTextContent(/^Total général.*1 160,00$/);
  });

  it("says no risk answers the request, its totals those of the server", () => {
    renderRisks(risksOf("risks_empty"));
    expect(grid()).toHaveTextContent("Aucune ligne ne répond à la demande.");
    expect(within(grid()).getAllByRole("row").at(-1)).toHaveTextContent(/^Total général.*0,00$/);
  });

  it("is named and headed in English too", () => {
    renderRisks(risksOf("risks"), "en");
    const english = screen.getByRole("grid", { name: "Risk register" });
    expect(within(english).getByRole("columnheader", { name: /Severity/ })).toBeVisible();
    expect(within(english).getAllByRole("row").at(-1)).toHaveTextContent(
      /^General total.*1,160\.00$/,
    );
  });
});

/** The filter of the risks by state, in French, the address filtering on `states`. */
function filterOf(states: readonly RiskState[]) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <RiskStateFilter states={states} />
    </NextIntlClientProvider>
  );
}

/** Render the filter of the risks by state, the address filtering on some. */
function renderFilter(states: readonly RiskState[]) {
  return render(filterOf(states));
}

/** The filter, by its name. */
function filter(): HTMLElement {
  return screen.getByRole("group", { name: "Filtrer par état" });
}

describe("the filter of the risks by state", () => {
  it("offers each state of the contract, and every state pressed while the address filters on none [WF-RIS-0040-A]", async () => {
    const { container } = renderFilter([]);
    const pressed = within(filter())
      .getAllByRole("button")
      .map((button) => [button.textContent, button.getAttribute("aria-pressed")]);
    expect(pressed).toEqual([
      ["Tous les états", "true"],
      ["Identifié", "false"],
      ["Survenu", "false"],
      ["Écarté", "false"],
    ]);
    await expectAccessible(container);
  });

  it("asks the server to filter on a state chosen, by the address, the rest of it kept [WF-RIS-0040-A]", async () => {
    page.search = "sort_by=provision_amount&sort_order=desc";
    renderFilter([]);
    await userEvent.click(within(filter()).getByRole("button", { name: "Survenu" }));
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?sort_by=provision_amount&sort_order=desc&states=occurred`,
      { scroll: false },
    );
  });

  it("adds a state to those filtered on, in the order of the contract, and takes one off — from the address arrived, what was asked forgotten", async () => {
    page.search = "states=occurred";
    const { rerender } = renderFilter(["occurred"]);
    expect(within(filter()).getByRole("button", { name: "Survenu" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(filter()).getByRole("button", { name: "Identifié" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=identified%2Coccurred`, {
      scroll: false,
    });
    // A navigation arrives — another than the one asked, which it replaced —: the next change
    // goes on from the address of the screen, what was asked forgotten (#288).
    page.search = "states=identified";
    rerender(filterOf(["identified"]));
    await userEvent.click(within(filter()).getByRole("button", { name: "Survenu" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=identified%2Coccurred`, {
      scroll: false,
    });
    // What was just asked is kept until it arrives: the next change goes on from it.
    await userEvent.click(within(filter()).getByRole("button", { name: "Identifié" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=occurred`, {
      scroll: false,
    });
  });

  it("lifts the filter on every state", async () => {
    page.search = "states=dismissed&search=automaticien";
    renderFilter(["dismissed"]);
    await userEvent.click(within(filter()).getByRole("button", { name: "Tous les états" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?search=automaticien`, {
      scroll: false,
    });
  });
});

describe("the changes the screen makes to its address, before the server has answered", () => {
  /** Render the filter and the grid of the risks, as the page shares the address they ask. */
  function renderScreen() {
    return render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PendingAddress>
          <RiskStateFilter states={[]} />
          <RisksGrid risks={risksOf("risks")} query={NO_QUERY} preferences={undefined} />
        </PendingAddress>
      </NextIntlClientProvider>,
    );
  }

  it("compose: two states chosen in a row, then a sort, all asked of the server [WF-RIS-0040-A]", async () => {
    renderScreen();
    // The address of the screen stays the one before: no navigation has arrived.
    await userEvent.click(within(filter()).getByRole("button", { name: "Identifié" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=identified`, {
      scroll: false,
    });
    await userEvent.click(within(filter()).getByRole("button", { name: "Survenu" }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=identified%2Coccurred`, {
      scroll: false,
    });
    const heading = within(grid()).getByRole("columnheader", { name: /Provision/ });
    await userEvent.click(within(heading).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?states=identified%2Coccurred&sort_by=provision_amount&sort_order=asc`,
        { scroll: false },
      );
    });
  });

  it("leave a click with a modifier to the browser, on the address shown — without the sort asked —, and navigate nothing themselves", async () => {
    renderScreen();
    const heading = within(grid()).getByRole("columnheader", { name: /Provision/ });
    await userEvent.click(within(heading).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?sort_by=provision_amount&sort_order=asc`,
        { scroll: false },
      );
    });
    const link = within(grid()).getByRole("link", { name: "Risque de reprise du câblage" });
    // The `href` is the address shown, the sort not arrived: a new tab opens without it (#288).
    expect(link).toHaveAttribute("href", `${PATHNAME}?risk=${CABLING}`);
    const pushes = router.push.mock.calls.length;
    fireEvent.click(link, { ctrlKey: true });
    fireEvent.click(link, { button: 1 });
    expect(router.push).toHaveBeenCalledTimes(pushes);
  });

  it("keep a sort under way when a risk is opened, by a click or from the keyboard [WF-RIS-0040-A]", async () => {
    renderScreen();
    const heading = within(grid()).getByRole("columnheader", { name: /Provision/ });
    await userEvent.click(within(heading).getByRole("button"));
    await waitFor(() => {
      expect(router.push).toHaveBeenLastCalledWith(
        `${PATHNAME}?sort_by=provision_amount&sort_order=asc`,
        { scroll: false },
      );
    });
    await userEvent.click(
      within(grid()).getByRole("link", { name: "Risque de reprise du câblage" }),
    );
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?sort_by=provision_amount&sort_order=asc&risk=${CABLING}`,
      { scroll: false },
    );
    cell("Retard de livraison des armoires", 0).focus();
    await userEvent.keyboard("{Enter}");
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?sort_by=provision_amount&sort_order=asc&risk=01926f3a-7c00-7000-8000-000000000752`,
      { scroll: false },
    );
  });
});
