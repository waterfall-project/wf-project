// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, cleanup, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { LeftRefusals } from "@/components/shell/left-refusals";
import { CATALOGUES } from "@/i18n/catalogues";
import { dismissLeftRefusals } from "@/navigation/held-writes";
import type { ListPage } from "@/navigation/pages";
import { example, fakeClient } from "@/test/fixtures";

import type { CostCategory, CostType } from "./cost-grids";
import { natureChoice } from "./cost-kinds";
import { CostCategoryList } from "./cost-lists";

// The server of Next, as far as the list needs it: the fake back, the page rendered again once an
// object is written, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
/** The query of the address the list reads, none save where a test reads it otherwise. */
const address = vi.hoisted(() => ({ query: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(address.query),
}));

const CATEGORY = "PATCH /reference/cost-categories/{cost_category_id}";

const types = example("cost_types") as { items: CostType[]; meta: ListPage };
const categories = example("volume/cost_categories_page") as {
  items: CostCategory[];
  meta: ListPage;
};
/** The first categories of the volumes: the subcontracting first, under the disbursements. */
const first = (example("volume/cost_categories") as { items: CostCategory[] }).items.slice(0, 3);

/** The sentence of the bar of the shell for one write refused once no longer shown. */
const UNTOLD =
  "Une modification qui n’est plus affichée a été refusée : elle n’est pas enregistrée.";

/**
 * The list of the categories, for a session that may modify the cost settings, and the bar of the
 * shell that tells what nothing else does, in French.
 */
function screenWithBar() {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <CostCategoryList
          rows={first}
          page={{ ...categories.meta, offset: 0 }}
          query={{ sort: undefined, search: undefined }}
          preferences={undefined}
          state={undefined}
          readsInactive
          editable
          natures={types.items.map((nature) => natureChoice(nature))}
          nature={undefined}
        />
      </PendingAddress>
      <header>
        <LeftRefusals />
      </header>
    </NextIntlClientProvider>
  );
}

/** Serve a refusal of the modification of a category, held until the test releases it. */
function refusedOnRelease(): () => void {
  let release: () => void = () => undefined;
  const until = new Promise<void>((settle) => {
    release = settle;
  });
  server.client = fakeClient(
    { [CATEGORY]: { problem: { code: "PERMISSION_MISSING", status: 403 } } },
    { hold: () => until },
  );
  return release;
}

/** Send the modification of the subcontracting from its dialog: the dialog, still open. */
async function sent(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole("button", { name: "Modifier « Sous-traitance »" }));
  const form = screen.getByRole("dialog", { name: "Modifier « Sous-traitance »" });
  await userEvent.click(within(form).getByRole("button", { name: "Enregistrer" }));
  return form;
}

/** Release the answer of the server, and let what waits for it run. */
async function answered(release: () => void): Promise<void> {
  await act(async () => {
    release();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

/** The bar of the shell. */
function bar(): HTMLElement {
  return screen.getByRole("banner");
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  sessionStorage.clear();
  dismissLeftRefusals();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  address.query = "";
});

describe("a write refused once the list it was sent from is read otherwise (#863)", () => {
  it("is told by the bar of the shell, as a change no longer shown, the dialog closed: nothing on the list tells it", async () => {
    const release = refusedOnRelease();
    const { rerender } = render(screenWithBar());
    const form = await sent();
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    // The deactivated categories hidden: the list reads otherwise, the screen still there.
    address.query = "category_is_active=true";
    rerender(screenWithBar());
    expect(within(bar()).queryByRole("alert")).toBeNull();
    await answered(release);

    const alert = await within(bar()).findByRole("alert");
    expect(alert).toHaveTextContent(UNTOLD);
    expect(screen.getAllByRole("alert")).toEqual([alert]);
  });

  it("is told by the bar of the shell, once, when the dialog closes after the list is read otherwise and before the refusal arrives", async () => {
    const release = refusedOnRelease();
    const { rerender } = render(screenWithBar());
    const form = await sent();
    // The list reads otherwise while the dialog is open: whether the refusal is told is decided at
    // its arrival, the dialog closed by then, never at the moment the list changes.
    address.query = "category_is_active=true";
    rerender(screenWithBar());
    await userEvent.click(within(form).getByRole("button", { name: "Annuler" }));
    expect(within(bar()).queryByRole("alert")).toBeNull();
    await answered(release);

    const alert = await within(bar()).findByRole("alert");
    expect(alert).toHaveTextContent(UNTOLD);
    expect(screen.getAllByRole("alert")).toEqual([alert]);
    expect(screen.getAllByText(UNTOLD)).toHaveLength(1);
  });

  it("is told by the dialog still open alone, never a second time by the bar of the shell", async () => {
    const release = refusedOnRelease();
    const { rerender } = render(screenWithBar());
    const form = await sent();
    address.query = "category_is_active=true";
    rerender(screenWithBar());
    await answered(release);

    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Vous n’avez pas la permission nécessaire.",
    );
    // The dialog open, the rest of the page is hidden from a reader of the screen: the bar is read
    // by its text.
    expect(screen.queryByText(UNTOLD)).toBeNull();
  });
});
