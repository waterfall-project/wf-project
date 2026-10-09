// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import { GridToolbar } from "./grid-toolbar";

// The server of Next, as far as the bar needs it: the address its search is dated by.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useSearchParams: () => new URLSearchParams(),
}));

/** The bar of a grid under the search its address holds, each search entered given to `onSearch`. */
function toolbar(search: string | undefined, onSearch: (search: string) => void) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <GridToolbar columns={[]} search={search} onSearch={onSearch} undoable={undefined} />
    </NextIntlClientProvider>
  );
}

/** The search of the bar. */
function field(): HTMLElement {
  return screen.getByRole("searchbox", { name: "Rechercher un libellé" });
}

describe("the search of a grid, dated by the address (#553)", () => {
  it("keeps the focus in the field that sent the search once the address arrives", async () => {
    const onSearch = vi.fn();
    const { rerender } = render(toolbar(undefined, onSearch));
    const sent = field();
    await userEvent.type(sent, "revue{Enter}");
    expect(onSearch).toHaveBeenLastCalledWith("revue");
    // The address sent arrives: the field stays, with the focus and the search.
    rerender(toolbar("revue", onSearch));
    expect(field()).toBe(sent);
    expect(sent).toHaveFocus();
    expect(sent).toHaveValue("revue");
  });

  it("forgets a search typed and not sent when the address comes back to the search it was typed over", async () => {
    const onSearch = vi.fn();
    const { rerender } = render(toolbar(undefined, onSearch));
    await userEvent.type(field(), "câb");
    // Back in the history to another search, then forward to none: the field shows the address,
    // the entry given up.
    rerender(toolbar("revue", onSearch));
    expect(field()).toHaveValue("revue");
    rerender(toolbar(undefined, onSearch));
    expect(field()).toHaveValue("");
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("forgets a search sent when the address comes back to the search it was typed over", async () => {
    const onSearch = vi.fn();
    const { rerender } = render(toolbar("revue", onSearch));
    await userEvent.clear(field());
    await userEvent.type(field(), "câblage{Enter}");
    rerender(toolbar("câblage", onSearch));
    // « Précédent »: the address the search was typed over shows its own search.
    rerender(toolbar("revue", onSearch));
    expect(field()).toHaveValue("revue");
  });

  it("keeps a search typed, and the focus, through a change of the address the search does not write", async () => {
    const onSearch = vi.fn();
    const { rerender } = render(toolbar(undefined, onSearch));
    const typed = field();
    await userEvent.type(typed, "câb");
    // A sort arrives meanwhile — the page renders the bar anew, its search as it was.
    rerender(toolbar(undefined, vi.fn()));
    expect(field()).toBe(typed);
    expect(typed).toHaveValue("câb");
    expect(typed).toHaveFocus();
  });
});
