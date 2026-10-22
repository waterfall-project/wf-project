// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContextBanner } from "@/components/context/context-banner";
import type { Project, ProjectReading } from "@/components/context/reading";
import { CATALOGUES } from "@/i18n/catalogues";
import { readContext } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { breakdownChip, type BreakdownChoices, readBreakdownFilter } from "./breakdown-filter";
import { BreakdownFilterChoice } from "./breakdown-filter-choice";
import { breakdownItems, type WorkBreakdownReading } from "./planning-attachment";

// The server of Next, as far as the filter needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PLANNING,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const PLANNING = `/projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102/planning`;
// The lot of the witness and its post, as its work breakdown names them.
const LOT = "01926f3a-7c00-7000-8000-000000000711";
const ITEM = "01926f3a-7c00-7000-8000-000000000712";
// The French catalogue sets a no-break space before a colon and inside quotes.
const NB = "\u00a0";
const WORK = `Lot${NB}: Lot 1`;
const POST = `Poste${NB}: Poste 1.1`;

/** The lots and the posts of the work breakdown of the witness, the address read as `search`. */
function choices(search: string): BreakdownChoices {
  return {
    items: breakdownItems(example("work_breakdown") as WorkBreakdownReading),
    filter: readBreakdownFilter(new URLSearchParams(search)),
  };
}

/** The filter of the planning, in French, the address read as `search`. */
function filter(search: string) {
  page.search = search;
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <BreakdownFilterChoice choices={choices(search)} />
    </NextIntlClientProvider>,
  );
}

/** The banner of the planning of the witness, in French, its grid filtered as `search` says. */
function banner(search: string) {
  page.search = search;
  const context = readContext(PLANNING, new URLSearchParams(search));
  if (context === undefined) {
    throw new Error(`No context at ${PLANNING}`);
  }
  const reading: ProjectReading = {
    pathname: PLANNING,
    context,
    project: example("project") as Project,
    revision: undefined,
    edits: new Set(),
    readOnly: false,
    filters: [],
  };
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ContextBanner
        reading={reading}
        restricts={{ order_item_id: "grid" }}
        breakdown={breakdownChip(
          readBreakdownFilter(new URLSearchParams(search)),
          choices(search).items,
        )}
      />
    </NextIntlClientProvider>,
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the filter of a grid by a lot or a post", () => {
  it("offers the lots and the posts of the work breakdown, each named by its kind, a lot before its posts", async () => {
    const { container } = filter("");
    const list = screen.getByRole("combobox", { name: "Lot ou poste" });
    const names = within(list)
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(names).toEqual(["Tous les lots et postes", WORK, POST]);
    expect(list).toHaveValue("");
    await expectAccessible(container);
  });

  it("writes a post chosen under `order_item_id`, the lot lifted and the rest of the address kept", async () => {
    filter(`work_package_id=${LOT}&search=Revue`);
    const list = screen.getByRole("combobox", { name: "Lot ou poste" });
    expect(list).toHaveValue(LOT);
    await userEvent.selectOptions(list, screen.getByRole("option", { name: POST }));
    const asked = `${PLANNING}?search=Revue&order_item_id=${ITEM}`;
    expect(router.push).toHaveBeenLastCalledWith(asked, { scroll: false });
  });

  it("writes a lot chosen under `work_package_id`, and lifts both by the first choice", async () => {
    filter(`order_item_id=${ITEM}`);
    const list = screen.getByRole("combobox", { name: "Lot ou poste" });
    await userEvent.selectOptions(list, screen.getByRole("option", { name: WORK }));
    const asked = `${PLANNING}?work_package_id=${LOT}`;
    expect(router.push).toHaveBeenLastCalledWith(asked, { scroll: false });
    await userEvent.selectOptions(list, screen.getByRole("option", { name: /^Tous/ }));
    expect(router.push).toHaveBeenLastCalledWith(PLANNING, { scroll: false });
  });

  it("keeps chosen a post the work breakdown does not have, under its identifier, to be cleared", () => {
    const unknown = "01926f3a-7c00-7000-8000-000000000799";
    filter(`order_item_id=${unknown}`);
    const list = screen.getByRole("combobox", { name: "Lot ou poste" });
    expect(list).toHaveValue(unknown);
    expect(screen.getByRole("option", { name: unknown })).toBeInTheDocument();
  });
});

describe("the filter by a lot or a post in the banner of the context", () => {
  it("shows the post filtered without opening any panel, by its kind and its label, with the link that lifts it [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres.
    const { container } = banner(`order_item_id=${ITEM}&search=Revue`);
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    const chip = within(chips).getByRole("listitem");
    expect(chip).toHaveTextContent("Poste : Poste 1.1, sur la grille seulement");
    expect(within(chip).getByRole("link")).toHaveAccessibleName(
      `Lever le filtre «${NB}${POST}, sur la grille seulement${NB}»`,
    );
    expect(within(chip).getByRole("link")).toHaveAttribute("href", `${PLANNING}?search=Revue`);
    await expectAccessible(container);
  });

  it("names a lot the work breakdown does not have by the identifier the address gives", () => {
    const unknown = "01926f3a-7c00-7000-8000-000000000798";
    banner(`work_package_id=${unknown}`);
    expect(screen.getByRole("list", { name: "Filtres actifs" })).toHaveTextContent(
      `Lot : ${unknown}`,
    );
  });

  it("shows no chip for a grid filtered by neither", () => {
    banner("");
    expect(screen.queryByRole("list", { name: "Filtres actifs" })).toBeNull();
  });

  it("ignores an identifier the address gives that is none, as if it named nothing", () => {
    banner(`work_package_id=pas-un-uuid&order_item_id=${ITEM}`);
    expect(readBreakdownFilter(new URLSearchParams("order_item_id=../x"))).toBeUndefined();
    // The post read in place of the malformed lot, which the API would refuse.
    expect(screen.getByRole("list", { name: "Filtres actifs" })).toHaveTextContent(
      "Poste : Poste 1.1",
    );
  });
});
