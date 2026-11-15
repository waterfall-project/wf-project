// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The natures and the categories of cost in their cards (US-2080, #3071): the creation of a list
 * at the right of the title of its card, filled, the one filled command of the card, offered on an
 * empty list too; the commands of a row in the light border of the tables (#3079).
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import { expectCommandRule } from "@/test/command-rule";
import { example, fakeClient } from "@/test/fixtures";

import type { CostCategory, CostType } from "./cost-grids";
import { natureChoice } from "./cost-kinds";
import { CostCategoryList, CostTypeList } from "./cost-lists";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY = { sort: undefined, search: undefined, size: undefined };
const types = example("cost_types") as { items: CostType[]; meta: ListPage };
const categories = example("volume/cost_categories_page") as {
  items: CostCategory[];
  meta: ListPage;
};

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The natures and the first categories, or none of either, for a session that writes or reads. */
function lists({ empty = false, editable = true } = {}) {
  const none = { ...types.meta, offset: 0, total: 0 };
  return inFrench(
    <>
      <CostTypeList
        rows={empty ? [] : types.items}
        page={empty ? none : types.meta}
        query={NO_QUERY}
        preferences={undefined}
        state={undefined}
        editable={editable}
        kinds={[]}
      />
      <CostCategoryList
        rows={empty ? [] : categories.items.slice(0, 3)}
        page={empty ? none : { ...categories.meta, offset: 0 }}
        query={NO_QUERY}
        preferences={undefined}
        state={undefined}
        editable={editable}
        natures={types.items.map(natureChoice)}
        nature={undefined}
      />
    </>,
  );
}

/** The card of a list, by its title. */
function card(title: string): HTMLElement {
  return screen.getByRole("region", { name: title });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the cards of the natures and of the categories", () => {
  it.each([
    ["Natures de coût", "Nouvelle nature"],
    ["Catégories de coût", "Nouvelle catégorie"],
  ])(
    "sets the creation of « %s » at the right of the title of its card, filled, before its table [WF-IHM-0060-A]",
    (title, creation) => {
      render(lists());
      const section = card(title);
      expect(section).toHaveAttribute("data-slot", "section-card");
      const button = within(section).getByRole("button", { name: creation });
      expect(button.className).toBe(cn(buttonVariants({ variant: "default", size: "sm" })));
      // In the header of the card, beside its title, not in the bar of its table.
      const header = section.querySelector('[data-slot="card-header"]');
      expect(header?.contains(button)).toBe(true);
      expect(header?.contains(within(section).getByRole("heading", { level: 2 }))).toBe(true);
      expect(button.closest("[data-grid-toolbar]")).toBeNull();
      const table = within(section).getByRole("grid", { name: title });
      expect(button.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    },
  );

  it("keeps the rule of the commands: one filled command in each card, its creation [WF-IHM-0060-A]", () => {
    const { container } = render(lists());
    expectCommandRule(container);
    for (const title of ["Natures de coût", "Catégories de coût"]) {
      const filled = within(card(title))
        .getAllByRole("button")
        .filter((button) => button.className.includes("bg-primary"));
      expect(filled).toHaveLength(1);
    }
  });

  it("keeps the creation of an empty list at the right of its title, beside what says it is empty [WF-IHM-0060-A]", () => {
    const { container } = render(lists({ empty: true }));
    const natures = card("Natures de coût");
    expect(within(natures).getByText("Aucune nature de coût.")).toBeVisible();
    expect(within(natures).queryByRole("grid")).toBeNull();
    expect(within(natures).getByRole("button", { name: "Nouvelle nature" })).toBeVisible();
    expect(
      within(card("Catégories de coût")).getByRole("button", { name: "Nouvelle catégorie" }),
    ).toBeVisible();
    expectCommandRule(container);
  });

  it("offers no creation, nor any filled command, to a session that only reads", () => {
    const { container } = render(lists({ editable: false }));
    expect(
      within(card("Natures de coût")).queryByRole("button", { name: "Nouvelle nature" }),
    ).toBeNull();
    expect(container.querySelector('[data-slot="section-card-principal"]')).toBeNull();
    expectCommandRule(container);
  });

  it("draws the commands of a row in their own border, at a label of normal weight (#3079, #3332)", () => {
    render(lists());
    const modify = within(card("Natures de coût")).getAllByRole("button", { name: /^Modifier/ })[0];
    expect(modify?.className).toContain("border-row-command-border");
    expect(modify?.className).toContain("font-normal");
    expect(modify?.className).not.toContain("border-input");
  });

  it("breaks no rule of accessibility", async () => {
    const { container } = render(lists({ empty: true }));
    await expectAccessible(container);
  });
});
