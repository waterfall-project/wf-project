// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, cleanup, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { startTransition } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { closeMenu, menuSummary, openMenu, pick } from "@/test/check-menu";

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

/** The filter of the risks by state, the states the address names checked. */
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

/** The same filter with a box « Sans état » that the address writes as the flag `none`. */
function withFlag(chosen: readonly (State | "none")[]) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ValuesFilter<State | "none">
        name="states"
        label="État"
        every="Tous les états"
        values={[
          { value: "none", text: "Sans état" },
          ...STATES.map((state) => ({ value: state, text: state })),
        ]}
        chosen={chosen}
        exhaustive
        flag={{ value: "none", name: "none" }}
      />
    </NextIntlClientProvider>
  );
}

/** The same filter, an old parameter of the address saying one of its values. */
function withSaid(
  chosen: readonly State[],
  said: { readonly name: string; readonly value: string; readonly reads: State },
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ValuesFilter
        name="states"
        label="État"
        every="Tous les états"
        values={STATES.map((state) => ({ value: state, text: state }))}
        chosen={chosen}
        exhaustive
        lifts={[said.name]}
        said={said}
      />
    </NextIntlClientProvider>
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the filter of a list on the values of a column", () => {
  it("shows the values asked checked while the server reads the list anew, and the address once it has answered", async () => {
    let arrive: () => void = () => undefined;
    const navigation = new Promise<void>((resolve) => {
      arrive = resolve;
    });
    // A navigation of Next stays pending until the server has answered for the new address.
    router.push.mockImplementation(() => {
      startTransition(() => navigation);
    });
    const { rerender } = render(filter([]));
    await pick("État", "occurred");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks?states=occurred", {
      scroll: false,
    });
    // The address has not changed yet: the value asked shows checked, never the address before it.
    expect(menuSummary("État")).toBe("occurred");
    await openMenu("État");
    expect(screen.getByRole("checkbox", { name: "occurred" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Tous les états" })).not.toBeChecked();
    await closeMenu();
    // The server answers: the address names the value, which the button goes on showing pressed.
    page.search = "states=occurred";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter(["occurred"]));
    await openMenu("État");
    expect(screen.getByRole("checkbox", { name: "occurred" })).toBeChecked();
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
    await pick("État", "closed");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks", {
      scroll: false,
    });
    await openMenu("État");
    expect(screen.getByRole("checkbox", { name: "Tous les états" })).toBeChecked();
    await closeMenu();
    page.search = "";
    await act(async () => {
      arrive();
      await navigation;
    });
    rerender(filter([]));
    await openMenu("État");
    expect(screen.getByRole("checkbox", { name: "Tous les états" })).toBeChecked();
  });

  it("says Tous, the value, or how many are checked, and checks and unchecks a value in a row (#2916)", async () => {
    // The server never answers: what is asked stays shown, and goes on from what was last asked.
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    render(filter([]));
    expect(menuSummary("État")).toBe("Tous les états");
    await pick("État", "identified");
    await pick("État", "closed");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/risks?states=identified%2Cclosed",
      { scroll: false },
    );
    expect(menuSummary("État")).toBe("2 sélectionnés");
    await pick("État", "identified");
    expect(menuSummary("État")).toBe("closed");
    await pick("État", "Tous les états");
    expect(menuSummary("État")).toBe("Tous les états");
  });

  it("searches a long menu: eleven values or more offer a search, fewer none (#2916)", async () => {
    const many = Array.from({ length: 12 }, (_, index) => `valeur-${String(index)}`);
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <ValuesFilter
          name="states"
          label="Long"
          every="Tous"
          values={many.map((value) => ({ value, text: value }))}
          chosen={[]}
          exhaustive={false}
        />
      </NextIntlClientProvider>,
    );
    await openMenu("Long");
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Rechercher dans «\u00a0Long\u00a0»" }),
      "-11",
    );
    expect(screen.getByRole("checkbox", { name: "valeur-11" })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "valeur-3" })).toBeNull();
    await userEvent.clear(screen.getByRole("searchbox"));
    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    expect(screen.getByText("Aucune valeur ne correspond.")).toBeInTheDocument();
  });

  it("writes a flag under its own name, true when checked, removed when unchecked, and keeps it out of the exhaustive values (#3050)", async () => {
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    render(withFlag([]));
    await pick("État", "Sans état");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks?none=true", {
      scroll: false,
    });
    await pick("État", "identified");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/risks?none=true&states=identified",
      { scroll: false },
    );
    await pick("État", "Sans état");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/risks?states=identified",
      { scroll: false },
    );
    // Every value of the contract lifts the filter; the flag is not one of them, nor does it
    // prevent the others from being all of them.
    await pick("État", "occurred");
    await pick("État", "closed");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks", {
      scroll: false,
    });
    // Every value chosen and the flag checked: the values are lifted, the flag stays.
    await pick("État", "Sans état");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks?none=true", {
      scroll: false,
    });
  });

  it("reads a flag checked from the address, and unchecks it from there (#3050)", async () => {
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    page.search = "states=closed&none=true";
    render(withFlag(["closed", "none"]));
    await pick("État", "Sans état");
    expect(router.push).toHaveBeenLastCalledWith("/projects/p/revisions/r/risks?states=closed", {
      scroll: false,
    });
  });

  it("reads the old parameter as a value only while the parameter of the filter is absent (#3050)", async () => {
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    const said = { name: "old", value: "no", reads: "identified" as const };
    page.search = "old=no";
    render(withSaid([], said));
    await pick("État", "closed");
    // The old parameter says « identified »: it is read as chosen, and lifted by the choice.
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/risks?states=identified%2Cclosed",
      { scroll: false },
    );
    router.push.mockClear();
    // The filter has its own parameter: the old one says nothing more.
    page.search = "states=occurred&old=no";
    cleanup();
    render(withSaid(["occurred"], said));
    await pick("État", "closed");
    expect(router.push).toHaveBeenLastCalledWith(
      "/projects/p/revisions/r/risks?states=occurred%2Cclosed",
      { scroll: false },
    );
  });

  it("offers no search to a short menu, and breaks no rule of accessibility (#2916)", async () => {
    const { container } = render(filter(["occurred"]));
    // Closed, the page breaks no rule; open, the dialog is judged in a browser (`e2e/accessibility.spec.ts`).
    await expectAccessible(container);
    await openMenu("État");
    expect(screen.queryByRole("searchbox")).toBeNull();
  });
});
