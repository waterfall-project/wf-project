// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ListPages } from "@/components/grid/list-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";

import { RISKS_LIST } from "./address";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/projects/p/revisions/r/risks";

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

/** The second page of ten of a registry of thirty-five risks, as `meta` says it. */
const SECOND: ListPage = { limit: 10, offset: 10, total: 35 };

/** The pages of the registry of the risks, in French. */
function pages(meta: ListPage, shown: number) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>
        <ListPages list={RISKS_LIST} texts="risks.pages" page={meta} shown={shown} />
      </PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address the last navigation asked for. */
async function lastAddress(): Promise<string> {
  await waitFor(() => {
    expect(router.push).toHaveBeenCalled();
  });
  return String(router.push.mock.lastCall?.[0]);
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
});

describe("the pages of the registry of the risks", () => {
  it("leads to the pages before and after the one shown, the states and the sort of the address kept [WF-IHM-0060-A]", () => {
    page.search = "states=identified&sort_by=label&limit=10&offset=10";
    render(pages(SECOND, 10));
    const nav = screen.getByRole("navigation", { name: "Pages des risques" });
    expect(within(nav).getByRole("link", { name: /Risques précédents/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?states=identified&sort_by=label&limit=10`,
    );
    expect(within(nav).getByRole("link", { name: /Risques suivants/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?states=identified&sort_by=label&limit=10&offset=20`,
    );
  });

  it("offers « Lignes par page », and a size chosen takes the registry back to its first page [WF-IHM-0060-A]", async () => {
    page.search = "states=identified&limit=10&offset=10";
    render(pages(SECOND, 10));
    const size = screen.getByRole("combobox", { name: "Lignes par page" });
    expect(size).toHaveValue("10");
    expect([...size.querySelectorAll("option")].map((option) => option.value)).toEqual([
      "10",
      "25",
      "50",
      "100",
    ]);
    await userEvent.selectOptions(size, "25");
    expect(await lastAddress()).toBe(`${PATHNAME}?states=identified&limit=25`);
  });

  it("offers neither pages nor sizes to a registry of no more than the smallest page [WF-IHM-0060-A]", () => {
    render(pages({ limit: 50, offset: 0, total: 3 }, 3));
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
