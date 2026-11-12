// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { GridToolbar } from "./grid-toolbar";
import { TreeFilters, type TreeFiltersProps } from "./tree-filters";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATH = "/projects/p/revisions/r/estimate";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATH,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const LOT = "01926f3a-7c00-7000-8000-000000000711";
const ORIGIN = "01926f3a-7c00-7000-8000-000000000a01";

/** The bar of a tree grid whose screen offers `offer` to filter it by (#2916/L6). */
function bar(offer: TreeFiltersProps = {}) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <GridToolbar
        columns={[]}
        search={undefined}
        onSearch={undefined}
        undoable={undefined}
        treeFilters={<TreeFilters {...offer} />}
      />
    </NextIntlClientProvider>,
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the filters of the estimate, of the planning and of the remaining, in the bar of the grid [WF-IHM-0130-A] [WF-PLA-0080-A] (#2916)", () => {
  it("renders nothing when the grid offers no filter, so that the bar keeps its line", () => {
    const { container } = render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <TreeFilters />
      </NextIntlClientProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("puts the menus and the toggle in the one line of the bar, each named", () => {
    const { container } = bar({
      breakdown: { items: [{ id: LOT, kind: "work_package", label: "Lot 1" }], filter: undefined },
      differential: true,
      difference: undefined,
      origin: { risks: [{ id: ORIGIN, label: "Risque" }], filter: undefined },
    });
    const line = container.querySelector("[data-grid-toolbar]");
    expect(line).not.toBeNull();
    const inside = within(line as HTMLElement);
    expect(inside.getByRole("button", { name: /Differences only/ })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(inside.getByRole("button", { name: /Work package or order item/ })).toBeVisible();
    expect(inside.getByRole("button", { name: /^Origin/ })).toBeVisible();
    // Neither a row of their own above the bar, nor a native list.
    expect(container.querySelector("select")).toBeNull();
    expect(container.firstElementChild).toBe(line);
  });

  it("writes a choice of the menu in the address, back to the filter lifted by the first choice", async () => {
    page.search = "search=Review";
    bar({
      breakdown: { items: [{ id: LOT, kind: "work_package", label: "Lot 1" }], filter: undefined },
    });
    await userEvent.click(screen.getByRole("button", { name: /Work package or order item/ }));
    await userEvent.click(screen.getByRole("radio", { name: /Lot 1/ }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATH}?search=Review&work_package_id=${LOT}`, {
      scroll: false,
    });
  });

  it("writes « Écarts seulement » by a pressed toggle", async () => {
    bar({ differential: true });
    await userEvent.click(screen.getByRole("button", { name: /Differences only/ }));
    expect(router.push).toHaveBeenLastCalledWith(`${PATH}?difference=added%2Cremoved%2Cmodified`, {
      scroll: false,
    });
  });
});
