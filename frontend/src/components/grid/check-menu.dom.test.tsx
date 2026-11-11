// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, startTransition } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { menuSummary, openMenu } from "@/test/check-menu";

import { CheckMenu } from "./check-menu";
import { ValuesFilter } from "./values-filter";

// Menus of the filters (#2916): the keys, the closing, the burst of choices before the server answers.
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/risks",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const OPTIONS = ["a", "b", "c"].map((value) => ({ value, text: `Valeur ${value}` }));

/** In French, as a page gives it. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

afterEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the menu of one choice", () => {
  it("moves the focus by the arrows without choosing, and chooses by Space or Enter, closing", async () => {
    const onChange = vi.fn();
    render(
      inFrench(
        <CheckMenu
          label="Choix"
          every="Tous"
          options={OPTIONS}
          chosen={[]}
          multiple={false}
          onChange={onChange}
        />,
      ),
    );
    const list = await openMenu("Choix");
    const every = within(list).getByRole("radio", { name: "Tous" });
    every.focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(within(list).getByRole("radio", { name: "Valeur a" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(within(list).getByRole("radio", { name: "Valeur b" })).toHaveFocus();
    // Nothing chosen, the menu still open.
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith(["b"]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes on the value already chosen without asking anything, and forgets the search it was closed on", async () => {
    const onChange = vi.fn();
    render(
      inFrench(
        <CheckMenu
          label="Choix"
          every="Tous"
          options={OPTIONS}
          chosen={["a"]}
          multiple={false}
          searchable
          onChange={onChange}
        />,
      ),
    );
    let list = await openMenu("Choix");
    await userEvent.type(within(list).getByRole("searchbox"), "val");
    await userEvent.click(within(list).getByRole("radio", { name: "Valeur a" }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
    list = await openMenu("Choix");
    expect(within(list).getByRole("searchbox")).toHaveValue("");
  });
});

describe("the menu of several values", () => {
  it("says its summary to a reader while it is open, the page behind it hidden", async () => {
    render(
      inFrench(
        <CheckMenu
          label="Choix"
          every="Tous"
          options={OPTIONS}
          chosen={["a", "b"]}
          multiple
          onChange={() => undefined}
        />,
      ),
    );
    const list = await openMenu("Choix");
    expect(within(list).getByRole("status")).toHaveTextContent("2 sélectionnés");
  });

  it("asks nothing when every value is already the choice", async () => {
    render(
      inFrench(
        <ValuesFilter
          name="s"
          label="État"
          every="Tous"
          values={OPTIONS}
          chosen={[]}
          exhaustive={false}
        />,
      ),
    );
    const list = await openMenu("État");
    await userEvent.click(within(list).getByRole("checkbox", { name: "Tous" }));
    expect(router.push).not.toHaveBeenCalled();
  });

  it("keeps the list open, both boxes checked and the focus in it, when the address asked arrives after two boxes checked in a row", async () => {
    // The server answers late: the navigation stays pending until it is let go.
    router.push.mockImplementation(() => {
      startTransition(() => new Promise<void>(() => undefined));
    });
    const filter = (chosen: readonly string[]) =>
      inFrench(
        <ValuesFilter
          name="s"
          label="État"
          every="Tous"
          values={OPTIONS}
          chosen={chosen}
          exhaustive={false}
        />,
      );
    const { rerender } = render(filter([]));
    const list = await openMenu("État");
    await userEvent.click(within(list).getByRole("checkbox", { name: "Valeur a" }));
    await userEvent.click(within(list).getByRole("checkbox", { name: "Valeur b" }));
    expect(router.push).toHaveBeenLastCalledWith("/risks?s=a%2Cb", { scroll: false });
    page.search = "s=a,b";
    rerender(filter(["a", "b"]));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Valeur a" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Valeur b" })).toBeChecked();
    expect(screen.getByRole("dialog").contains(document.activeElement)).toBe(true);
    await userEvent.keyboard("{Escape}");
    expect(menuSummary("État")).toBe("2 sélectionnés");
  });
});
