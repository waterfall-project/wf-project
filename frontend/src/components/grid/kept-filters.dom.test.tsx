// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { type KeptFilters, useKeptFilters } from "./kept-filters";

// The address of the page, as far as the hook needs it.
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useSearchParams: () => new URLSearchParams(page.search),
}));

const CONFIG = {
  filters: ["states"],
  defaulted: { states: "pricing,in_progress" },
  searchKept: false,
};

/** Show the hook at the address, the account having kept the filters given. */
function show(kept: Record<string, string> | undefined, record: (filters: KeptFilters) => void) {
  function Screen() {
    useKeptFilters(CONFIG, kept === undefined ? undefined : { filters: kept }, record);
    return null;
  }
  render(<Screen />);
}

afterEach(() => {
  page.search = "";
});

describe("the filters with a default, kept with the settings of a grid (WF-IHM-0060)", () => {
  it("record nothing at the default, named or not, and do not forget what the account kept for an address that names none", () => {
    const record = vi.fn();
    show(undefined, record);
    page.search = "states=pricing%2Cin_progress";
    show(undefined, record);
    page.search = "";
    show({ states: "completed" }, record);
    expect(record).not.toHaveBeenCalled();
  });

  it("record the states chosen, `all` included, and the return to the default as nothing, the search never", () => {
    const record = vi.fn();
    page.search = "states=all&search=x";
    show(undefined, record);
    expect(record).toHaveBeenLastCalledWith({ states: "all" });
    page.search = "states=pricing%2Cin_progress";
    show({ states: "all" }, record);
    expect(record).toHaveBeenLastCalledWith({});
  });
});
