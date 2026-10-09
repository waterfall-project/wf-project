// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, startTransition } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import { ListPages } from "@/components/grid/list-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { listReads } from "./address";
import { InactiveSwitch, StateFilter } from "./reference-filters";
import {
  CALENDAR_ADDRESS,
  RESOURCE_ROLE_ADDRESS,
  ROLE_COST_CATEGORY,
  ROLE_STATE,
} from "./resource-grids";

// The server of Next, as far as the filters need it: the address they read and the navigations
// they ask.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** The second page of fifty categories of the two hundred of the volumes, as the server pages them. */
const MIDDLE = (example("volume/cost_categories_page") as { meta: ListPage }).meta;

/** The roles, as the screen reads them: their own parameters of the address. */
const ROLES = {
  page: RESOURCE_ROLE_ADDRESS.offset,
  reads: listReads(RESOURCE_ROLE_ADDRESS, ROLE_COST_CATEGORY, ROLE_STATE),
};

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

beforeEach(() => {
  page.search = "";
});

afterEach(() => {
  router.push.mockReset();
});

describe("the filters of a list of the reference data", () => {
  it("filter on the state, the address changed under the name of the grid, back to its first page [WF-IHM-0130-A]", async () => {
    page.search = "role_offset=50&calendar_offset=50";
    const { rerender } = render(
      inFrench(
        <StateFilter
          name={ROLE_STATE}
          label="État des objets de « Rôles »"
          chosen={undefined}
          page={RESOURCE_ROLE_ADDRESS.offset}
        />,
      ),
    );
    const group = screen.getByRole("group", { name: "État des objets de « Rôles »" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "Désactivés" }));
    // The page of the calendars, another list, is kept.
    expect(lastAddress()).toBe("/reference/resources?calendar_offset=50&role_is_active=false");
    page.search = "role_is_active=false";
    rerender(
      inFrench(
        <StateFilter
          name={ROLE_STATE}
          label="État des objets de « Rôles »"
          chosen={false}
          page={RESOURCE_ROLE_ADDRESS.offset}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: "Désactivés" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "Actifs" }));
    expect(lastAddress()).toBe("/reference/resources?role_is_active=true");
    await userEvent.click(screen.getByRole("button", { name: "Tous les états" }));
    expect(lastAddress()).toBe("/reference/resources");
  });

  it("show the state asked pressed while the server reads the list anew, and the address once it has answered", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    const filter = (chosen: boolean | undefined) =>
      inFrench(<StateFilter name={ROLE_STATE} label="État" chosen={chosen} />);
    const { rerender } = render(filter(undefined));
    const inactive = screen.getByRole("button", { name: "Désactivés" });
    await userEvent.click(inactive);
    expect(lastAddress()).toBe("/reference/resources?role_is_active=false");
    // The address has not changed yet: the state asked shows pressed, never the address before it.
    expect(inactive).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // The server answers: the address names the state, which the button goes on showing pressed.
    page.search = "role_is_active=false";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter(false));
    expect(inactive).toHaveAttribute("aria-pressed", "true");
  });

  it("filter on an object chosen, back to the first page, and keep one the list does not offer, to be cleared [WF-IHM-0130-A]", async () => {
    page.search = "role_offset=50";
    render(
      inFrench(
        <ChoiceFilter
          name={ROLE_COST_CATEGORY}
          label="Catégorie de coût"
          every="Toutes les catégories"
          choices={[{ value: "mo-001", text: "MO-001 · Ingénierie électrique" }]}
          chosen="gone"
          page={RESOURCE_ROLE_ADDRESS.offset}
        />,
      ),
    );
    const filter = screen.getByRole("combobox", { name: "Catégorie de coût" });
    expect(filter).toHaveValue("gone");
    await userEvent.selectOptions(filter, "mo-001");
    expect(lastAddress()).toBe("/reference/resources?role_cost_category_id=mo-001");
    await userEvent.selectOptions(filter, "");
    expect(lastAddress()).toBe("/reference/resources");
  });

  it("show the object chosen while the server reads the list anew, and the address once it has answered", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    const filter = (chosen: string | undefined) =>
      inFrench(
        <ChoiceFilter
          name={ROLE_COST_CATEGORY}
          label="Catégorie de coût"
          every="Toutes les catégories"
          choices={[{ value: "mo-001", text: "MO-001 · Ingénierie électrique" }]}
          chosen={chosen}
        />,
      );
    const { rerender } = render(filter(undefined));
    const select = screen.getByRole("combobox", { name: "Catégorie de coût" });
    await userEvent.selectOptions(select, "mo-001");
    expect(lastAddress()).toBe("/reference/resources?role_cost_category_id=mo-001");
    // The address has not changed yet: the list shows the choice, never the address before it.
    expect(select).toHaveValue("mo-001");
    // The server answers: the address names the object, which the list goes on showing.
    page.search = "role_cost_category_id=mo-001";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter("mo-001"));
    expect(select).toHaveValue("mo-001");
  });

  it("show the deactivated objects too back to the first page of each list the server pages [WF-REF-0150-A]", () => {
    page.search = "role_offset=50&calendar_offset=50&role_search=Ing";
    render(
      inFrench(
        <InactiveSwitch
          shown={false}
          pages={[RESOURCE_ROLE_ADDRESS.offset, CALENDAR_ADDRESS.offset]}
        />,
      ),
    );
    expect(screen.getByRole("link", { name: "Afficher aussi les désactivés" })).toHaveAttribute(
      "href",
      "/reference/resources?role_search=Ing&include_inactive=true",
    );
  });
});

describe("the pages of a list of the reference data", () => {
  it("lead to the pages before and after the one shown, named after the list, the rest of the address kept", async () => {
    page.search = "role_offset=50&calendar_sort_by=label";
    const { container } = render(
      inFrench(<ListPages list={ROLES} title="Rôles de ressources" page={MIDDLE} shown={50} />),
    );
    const pages = screen.getByRole("navigation", { name: "Pages de « Rôles de ressources »" });
    expect(pages).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/reference/resources?calendar_sort_by=label",
    );
    expect(screen.getByRole("link", { name: /Page suivante/ })).toHaveAttribute(
      "href",
      "/reference/resources?role_offset=100&calendar_sort_by=label",
    );
    await expectAccessible(container);
  });

  it("lead to the first page from an address that reads the list otherwise, a filter of its own under way, never for another list's sort", async () => {
    page.search = "role_offset=50";
    const { rerender } = render(
      inFrench(
        <>
          <StateFilter
            name={ROLE_STATE}
            label="État"
            chosen={undefined}
            page={RESOURCE_ROLE_ADDRESS.offset}
          />
          <ListPages list={ROLES} title="Rôles" page={MIDDLE} shown={50} />
        </>,
      ),
    );
    // A filter of the roles asked, not shown yet: the next page is the first of the list filtered.
    await userEvent.click(screen.getByRole("button", { name: "Actifs" }));
    await userEvent.click(screen.getByRole("link", { name: /Page suivante/ }));
    expect(lastAddress()).toBe("/reference/resources?role_is_active=true");
    // Shown, the sort of another list under way leaves the place of the roles as it is.
    page.search = "role_offset=50&calendar_sort_by=label";
    rerender(inFrench(<ListPages list={ROLES} title="Rôles" page={MIDDLE} shown={50} />));
    await userEvent.click(screen.getByRole("link", { name: /Page suivante/ }));
    expect(lastAddress()).toBe("/reference/resources?role_offset=100&calendar_sort_by=label");
  });

  it("say a page asked beyond the end, and lead back to the last one; nothing for a list of one page", () => {
    page.search = "role_offset=400";
    const beyond = { ...MIDDLE, offset: 400 };
    const { rerender } = render(
      inFrench(<ListPages list={ROLES} title="Rôles" page={beyond} shown={0} />),
    );
    expect(screen.getByText("La page demandée est au-delà de la fin de la liste.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Page précédente/ })).toHaveAttribute(
      "href",
      "/reference/resources?role_offset=150",
    );
    expect(screen.queryByRole("link", { name: /Page suivante/ })).toBeNull();
    const whole = { ...MIDDLE, offset: 0, total: 50 };
    rerender(inFrench(<ListPages list={ROLES} title="Rôles" page={whole} shown={50} />));
    expect(screen.queryByRole("navigation")).toBeNull();
  });
});
