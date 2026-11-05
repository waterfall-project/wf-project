// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { GridFilters, type GridFiltersProps } from "./grid-filters";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

/** What a grid with no filter offered gives, a part of it replaced by `offer`. */
function filters(offer: Partial<GridFiltersProps> = {}) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <GridFilters
        breakdown={undefined}
        difference={undefined}
        differential={false}
        origin={undefined}
        {...offer}
      />
    </NextIntlClientProvider>,
  );
}

describe("the row of the filters of the estimate and of the planning", () => {
  it("renders no row when the grid offers no filter, which would take the space of an empty one [WF-IHM-0130-A]", () => {
    const { container } = filters();
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the row when a filter is offered, « Écarts seulement » on a differential [WF-REV-0100-A]", () => {
    const { container } = filters({ differential: true });
    expect(container.firstElementChild).not.toBeNull();
    expect(screen.getByRole("button")).toBeVisible();
  });
});
