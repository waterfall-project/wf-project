// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { readRiskFilters, RISK_ZONES, riskFilterQuery, RISKS_LIST, universalDay } from "./address";
import { RiskColumnFilters } from "./risk-filters";
import { riskRow, type RiskRows, type RiskSortColumn } from "./risk-grid";
import { RisksGrid } from "./risks-grid";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/projects/p/revisions/r/risks";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type FieldProblem = components["schemas"]["FieldProblem"];

const NONE = { items: [], totals: (example("risks_empty") as RiskRows).totals };
const NO_QUERY: GridQuery<RiskSortColumn> = { sort: undefined, search: undefined, size: undefined };

/** The filters of the register, as the address of the page asks them, in French. */
function renderFilters(fields: readonly FieldProblem[] = [], lastMarkedOn?: string) {
  const search = new URLSearchParams(page.search);
  const zones = RISK_ZONES.filter((zone) => (search.get("zones") ?? "").split(",").includes(zone));
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <RiskColumnFilters
          filters={readRiskFilters(search, zones)}
          fields={fields}
          lastMarkedOn={lastMarkedOn}
        />
      </PendingAddress>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

describe("the address of the register of the risks", () => {
  it("reads the zones, the bounds of each column of figures and the period of the last review, and asks them of the server under the names of the contract [WF-IHM-0130-A]", () => {
    const search = new URLSearchParams(
      "zones=watch&probability_min=0.1&severity_max=900.50&provision_amount_min=100000" +
        "&occurrence_cost_min=1&occurred_reestimated_amount_max=300&last_review_on_from=2026-02-01" +
        "&last_review_on_to=2026-03-01&severity_min=abc",
    );
    const filters = readRiskFilters(search, ["watch"]);
    expect(riskFilterQuery(filters)).toEqual({
      zones: ["watch"],
      probability_min: "0.1",
      severity_max: "900.50",
      provision_amount_min: "100000",
      occurrence_cost_min: "1",
      occurred_reestimated_amount_max: "300",
      last_review_on_from: "2026-02-01",
      last_review_on_to: "2026-03-01",
    });
  });

  it("keeps the list of the register to the filters it reads, so that two addresses that filter alike read alike [WF-IHM-0130-A]", () => {
    expect(RISKS_LIST.reads).toEqual(
      expect.arrayContaining([
        "zones",
        "probability_min",
        "probability_max",
        "severity_min",
        "provision_amount_max",
        "occurrence_cost_min",
        "occurred_reestimated_amount_max",
        "last_review_on_from",
        "last_review_on_to",
      ]),
    );
  });

  it("shows the risks the server retains for a filtered request, the totals of those alone [WF-IHM-0130-A] [WF-RIS-0040-A]", async () => {
    const client = fakeClient({ "GET /projects/{project_id}/risks": "risks_filtered" });
    const filters = readRiskFilters(new URLSearchParams("provision_amount_min=100000"), []);
    const { data } = await client.GET("/projects/{project_id}/risks", {
      params: { path: { project_id: "p" }, query: riskFilterQuery(filters) },
    });
    expect(client.calls[0]?.query.get("provision_amount_min")).toBe("100000");
    const risks: RiskRows = {
      items: (data?.items ?? []).map(riskRow),
      totals: (data ?? NONE).totals,
    };
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <RisksGrid risks={risks} query={NO_QUERY} preferences={undefined} />
      </NextIntlClientProvider>,
    );
    const grid = screen.getByRole("grid", { name: "Registre des risques" });
    const rows = within(grid).getAllByRole("row");
    // The header, the two risks retained, the totals.
    expect(rows).toHaveLength(4);
    expect(rows[1]).toHaveTextContent("Risque de reprise du câblage");
    expect(rows[2]).toHaveTextContent("Indisponibilité de l'automaticien");
    expect(rows[3]).toHaveTextContent(/^Total général1\s100\s000,00$/);
  });
});

describe("the filters of the register on its columns", () => {
  it("offers the zone, the bounds of the probability and of the four columns of amounts, and the period of the last review [WF-IHM-0130-A]", async () => {
    const { container } = renderFilters();
    expect(screen.getByRole("group", { name: "Filtrer par zone" })).toBeVisible();
    const probability = screen.getByRole("form", { name: "Bornes de la probabilité, de 0 à 1" });
    expect(within(probability).getByRole("textbox", { name: "Probabilité, min." })).toBeVisible();
    const amounts = screen.getByRole("form", { name: "Bornes des montants" });
    for (const column of [
      "Gravité",
      "Provision",
      "Coût à la survenance",
      "Réestimé des survenus",
    ]) {
      expect(within(amounts).getByRole("textbox", { name: `${column}, min.` })).toBeVisible();
      expect(within(amounts).getByRole("textbox", { name: `${column}, max.` })).toBeVisible();
    }
    expect(screen.getByRole("form", { name: "Période du dernier réexamen" })).toBeVisible();
    await expectAccessible(container);
  });

  it("writes the bounds of an amount in the address as the contract writes them, the rest of it kept [WF-IHM-0130-A]", async () => {
    page.search = "sort_by=provision_amount&sort_order=desc";
    renderFilters();
    const amounts = screen.getByRole("form", { name: "Bornes des montants" });
    await userEvent.type(
      within(amounts).getByRole("textbox", { name: "Provision, min." }),
      "100000",
    );
    await userEvent.type(
      within(amounts).getByRole("textbox", { name: "Réestimé des survenus, max." }),
      "300,5",
    );
    await userEvent.click(within(amounts).getByRole("button", { name: "Filtrer" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalled();
    });
    expect(String(router.push.mock.lastCall?.[0])).toBe(
      `${PATHNAME}?sort_by=provision_amount&sort_order=desc&provision_amount_min=100000&occurred_reestimated_amount_max=300.5`,
    );
  });

  it("writes the bounds of the probability as a rate [WF-IHM-0130-A]", async () => {
    renderFilters();
    const form = screen.getByRole("form", { name: "Bornes de la probabilité, de 0 à 1" });
    await userEvent.type(within(form).getByRole("textbox", { name: "Probabilité, min." }), "0,2");
    await userEvent.click(within(form).getByRole("button", { name: "Filtrer" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith(`${PATHNAME}?probability_min=0.2`, {
        scroll: false,
      });
    });
  });

  it("filters on a zone of the matrix, by the address [WF-IHM-0130-A]", async () => {
    page.search = "states=identified";
    renderFilters();
    await userEvent.click(
      within(screen.getByRole("group", { name: "Filtrer par zone" })).getByRole("button", {
        name: "Vigilance",
      }),
    );
    expect(router.push).toHaveBeenLastCalledWith(`${PATHNAME}?states=identified&zones=watch`, {
      scroll: false,
    });
  });

  it("writes the period of the last review under the names of the contract, its end included [WF-IHM-0130-A]", async () => {
    renderFilters();
    const form = screen.getByRole("form", { name: "Période du dernier réexamen" });
    fireEvent.change(within(form).getByLabelText("Du"), { target: { value: "2026-02-01" } });
    fireEvent.change(within(form).getByLabelText("Au"), { target: { value: "2026-03-01" } });
    await userEvent.click(within(form).getByRole("button", { name: "Filtrer" }));
    await waitFor(() => {
      expect(router.push).toHaveBeenCalled();
    });
    expect(String(router.push.mock.lastCall?.[0])).toBe(
      `${PATHNAME}?last_review_on_from=2026-02-01&last_review_on_to=2026-03-01`,
    );
  });

  it("says at its field the end of the period the server refused, the start it names shown [WF-IHM-0130-A]", () => {
    const refusal = example("risks_period_inverted") as { fields: FieldProblem[] };
    page.search = "last_review_on_from=2026-03-01&last_review_on_to=2026-02-01";
    renderFilters(refusal.fields);
    const form = screen.getByRole("form", { name: "Période du dernier réexamen" });
    expect(within(form).getByLabelText("Au")).toBeInvalid();
    expect(form).toHaveTextContent(`La fin de la période ne peut précéder son début, 1 mars 2026.`);
  });

  it("offers « Non réexaminés depuis le dernier marquage », which ends the period of the review at the day of the last marking, the rest of the address kept [WF-RIS-0020-A]", async () => {
    const revisions = example("revisions") as {
      items: { marked_at: string | null }[];
    };
    const marked = revisions.items.find((each) => each.marked_at !== null)?.marked_at;
    const day = new Date(marked ?? "").toISOString().slice(0, 10);
    page.search = "states=identified&offset=50";
    renderFilters([], day);
    const shortcut = screen.getByRole("link", {
      name: "Non réexaminés depuis le dernier marquage",
    });
    expect(shortcut).toHaveAttribute(
      "href",
      `${PATHNAME}?states=identified&last_review_on_to=${day}`,
    );
    expect(shortcut).not.toHaveAttribute("aria-current");
    await userEvent.click(shortcut);
    expect(router.push).toHaveBeenLastCalledWith(
      `${PATHNAME}?states=identified&last_review_on_to=${day}`,
      { scroll: false },
    );
  });

  it("marks the shortcut as asked when the address holds the day, and offers none for a project that marked no revision [WF-RIS-0020-A]", () => {
    page.search = "last_review_on_to=2026-02-01";
    const { unmount } = renderFilters([], "2026-02-01");
    expect(
      screen.getByRole("link", { name: "Non réexaminés depuis le dernier marquage" }),
    ).toHaveAttribute("aria-current", "true");
    unmount();
    renderFilters([], undefined);
    expect(screen.queryByRole("link", { name: /Non réexaminés/ })).toBeNull();
  });

  it("takes the day of the last marking in universal time, an instant near midnight keeping its day [WF-RIS-0020-A]", () => {
    expect(universalDay("2026-02-01T00:30:00+01:00")).toBe("2026-01-31");
    expect(universalDay("2026-01-31T23:59:59Z")).toBe("2026-01-31");
    expect(universalDay("2026-01-31T23:30:00-01:00")).toBe("2026-02-01");
  });

  it("is named in English too [WF-IHM-0130-A]", () => {
    const search = new URLSearchParams("");
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <PendingAddress>
          <RiskColumnFilters
            filters={readRiskFilters(search, [])}
            fields={[]}
            lastMarkedOn="2026-02-01"
          />
        </PendingAddress>
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("group", { name: "Filter by zone" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Not reviewed since the last marking" })).toBeVisible();
  });
});
