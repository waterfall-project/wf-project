// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import type { DifferenceValue } from "./difference-filter";
import { DifferencesOnly } from "./differences-only";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** The button « Écarts seulement », for the differences the address retains. */
function button(filter: readonly DifferenceValue[] | undefined, offered = true) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <DifferencesOnly filter={filter} offered={offered} />
    </NextIntlClientProvider>
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("« Écarts seulement » [WF-REV-0100-A] [WF-REV-0080-A]", () => {
  it("writes the three differences of the contract in the address, the rest of the query kept", async () => {
    page.search = "structure=s&search=Revue";
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    render(button(undefined));
    const only = screen.getByRole("button", { name: "Écarts seulement" });
    expect(only).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(only);
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/planning?structure=s&search=Revue&difference=added%2Cremoved%2Cmodified",
      { scroll: false },
    );
    expect(only).toHaveAttribute("aria-pressed", "true");
  });

  it("lifts the filter from the address when pressed again", async () => {
    page.search = "structure=s&difference=added%2Cremoved%2Cmodified";
    render(button(["added", "removed", "modified"]));
    const only = screen.getByRole("button", { name: "Écarts seulement" });
    expect(only).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(only);
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/planning?structure=s", {
      scroll: false,
    });
  });

  it("is not pressed for some of the differences alone, and is absent where the structure bears none", () => {
    const { rerender } = render(button(["added"]));
    expect(screen.getByRole("button", { name: "Écarts seulement" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    rerender(button(undefined, false));
    expect(screen.queryByRole("button", { name: "Écarts seulement" })).toBeNull();
  });
});
