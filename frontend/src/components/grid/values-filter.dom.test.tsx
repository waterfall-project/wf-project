// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { ValuesFilter } from "./values-filter";

// The server of Next, as far as the filter needs it: the address it reads and the navigations it
// asks.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/risks",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const STATES = ["identified", "occurred", "closed"] as const;
type State = (typeof STATES)[number];

/** The filter of the risks by state, the states the address names pressed. */
function filter(chosen: readonly State[]) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ValuesFilter
        name="states"
        label="État"
        every="Tous les états"
        values={STATES.map((state) => ({ value: state, text: state }))}
        chosen={chosen}
        exhaustive
      />
    </NextIntlClientProvider>
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the filter of a list on the values of a column", () => {
  it("shows the values asked pressed while the server reads the list anew, and the address once it has answered", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    const { rerender } = render(filter([]));
    const occurred = screen.getByRole("button", { name: "occurred" });
    await userEvent.click(occurred);
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks?states=occurred", {
      scroll: false,
    });
    // The address has not changed yet: the value asked shows pressed, never the address before it.
    expect(occurred).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // The server answers: the address names the value, which the button goes on showing pressed.
    page.search = "states=occurred";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter(["occurred"]));
    expect(occurred).toHaveAttribute("aria-pressed", "true");
  });

  it("shows the filter lifted while every value of an exhaustive filter is asked", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    page.search = "states=identified,occurred";
    const { rerender } = render(filter(["identified", "occurred"]));
    await userEvent.click(screen.getByRole("button", { name: "closed" }));
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks", {
      scroll: false,
    });
    expect(screen.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    page.search = "";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter([]));
    expect(screen.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
