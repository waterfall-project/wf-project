// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screens that read the structure their address names (US-0500), as a document renders the
 * tree their page composes: the banner and the grid ask their navigations from one address, and the
 * grid of one structure hands none of its own state to the grid of the next. The page is read on
 * the server, as in its own tests; what it composes is client parts, whose sharing only a render
 * in a document shows.
 */
import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode, startTransition } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import EstimatePage from "./estimate/page";
import type { RevisionParams } from "./page";
import PlanningPage from "./planning/page";

// The server of Next, as far as the screens need it: the fake back, a client for each call; the
// router, whose navigations a test holds; and the address the browser shows.
const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ pathname: "", search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => page.pathname,
  useSearchParams: () => new URLSearchParams(page.search),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
// The amendment 2 of the current revision (`structures`).
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
// The lot of the witness, as its work breakdown names it.
const LOT = "01926f3a-7c00-7000-8000-000000000711";
// The French catalogue sets a no-break space inside quotes.
const NB = "\u00a0";

type Page = (props: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) => Promise<ReactNode>;

/** A screen, by its page, the end of its route, and the nodes the fake back serves it. */
interface Screen {
  readonly name: string;
  readonly Page: Page;
  readonly route: string;
  readonly nodes: NonNullable<FakeAnswers[typeof NODES]>;
}

const PLANNING: Screen = {
  name: "planning",
  Page: PlanningPage,
  route: "planning",
  nodes: "nodes_planning",
};
const ESTIMATE: Screen = {
  name: "estimate",
  Page: EstimatePage,
  route: "estimate",
  nodes: "nodes",
};

/** The tree of a screen at the address `search` gives, read on the fake back, in French. */
async function tree({ Page, route, nodes }: Screen, search: string): Promise<ReactNode> {
  page.pathname = `/projects/${PROJECT}/revisions/${REVISION}/${route}`;
  page.search = search;
  server.answers = { ...server.answers, [NODES]: nodes };
  const read = await Page({
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(Object.fromEntries(new URLSearchParams(search))),
  });
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {read}
    </NextIntlClientProvider>
  );
}

/** Hold every navigation asked until the server answers; give back how to let them arrive. */
function holdNavigations(): () => Promise<void> {
  let arrive: () => void = () => undefined;
  const navigation = new Promise<void>((resolve) => {
    arrive = resolve;
  });
  // A navigation of Next stays pending until the server has answered for the new address.
  router.push.mockImplementation(() => {
    startTransition(() => navigation);
  });
  return async () => {
    await act(async () => {
      arrive();
      await navigation;
    });
  };
}

/** The address of the last navigation asked, by its query. */
function lastAsked(): URLSearchParams {
  const [href] = (router.push.mock.lastCall ?? [""]) as [string];
  return new URLSearchParams(href.split("?")[1] ?? "");
}

/** Sort the grid by its inflated amount, from the button of its header. */
async function sortByInflation() {
  await userEvent.click(
    within(screen.getByRole("columnheader", { name: /inflation/ })).getByRole("button"),
  );
}

/** Filter the grid by the lot of the witness, from the choice above it. */
async function chooseLot() {
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Lot ou poste" }),
    screen.getByRole("option", { name: `Lot${NB}: Lot 1` }),
  );
}

/** Choose the amendment 2 in the banner, the main structure read. */
async function chooseAmendment() {
  await userEvent.click(
    within(screen.getByRole("region", { name: "Contexte de lecture" })).getByRole("button", {
      name: `Changer de structure, «${NB}Structure principale${NB}» lue`,
    }),
  );
  await userEvent.click(
    within(screen.getByRole("menu")).getByRole("menuitemradio", {
      name: "Avenant 2 — reprise des essais",
    }),
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

beforeEach(() => {
  router.push.mockReset();
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/estimate-indicators": "estimate_indicators",
    "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates_none",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
    "GET /projects/{project_id}/subprojects": "subprojects",
    "GET /projects/{project_id}/work-breakdown": "work_breakdown",
    "GET /projects/{project_id}/timelines": "timelines",
    "PATCH /me/preferences": "preferences",
  };
  // Laid out as a browser would: a window of rows in view.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the address the banner and the grid of a screen ask from", () => {
  // The estimate sorts its lines; the planning keeps the order of its plan and sorts none: the
  // sort is asked of the estimate alone, and the lot filter, which both have, of each.
  it("chooses the structure from the sort asked and not arrived yet, the sort kept", async () => {
    render(await tree(ESTIMATE, ""));
    const arrive = holdNavigations();
    await sortByInflation();
    await chooseAmendment();
    expect(Object.fromEntries(lastAsked())).toEqual({
      sort_by: "inflated_amount",
      sort_order: "asc",
      structure: AMENDMENT,
    });
    await arrive();
  });

  it("sorts from the structure chosen and not arrived yet, the structure kept", async () => {
    render(await tree(ESTIMATE, ""));
    const arrive = holdNavigations();
    await chooseAmendment();
    await sortByInflation();
    expect(Object.fromEntries(lastAsked())).toEqual({
      structure: AMENDMENT,
      sort_by: "inflated_amount",
      sort_order: "asc",
    });
    await arrive();
  });

  it.each([PLANNING, ESTIMATE])(
    "chooses the structure from the lot filtered and not arrived yet, the lot kept, on the $name",
    async (shown) => {
      render(await tree(shown, ""));
      const arrive = holdNavigations();
      await chooseLot();
      await chooseAmendment();
      expect(Object.fromEntries(lastAsked())).toEqual({
        work_package_id: LOT,
        structure: AMENDMENT,
      });
      await arrive();
    },
  );

  it.each([PLANNING, ESTIMATE])(
    "filters by a lot from the structure chosen and not arrived yet, the structure kept, on the $name",
    async (shown) => {
      render(await tree(shown, ""));
      const arrive = holdNavigations();
      await chooseAmendment();
      await chooseLot();
      expect(Object.fromEntries(lastAsked())).toEqual({
        structure: AMENDMENT,
        work_package_id: LOT,
      });
      await arrive();
    },
  );
});

describe("the chip that lifts a filter of the banner", () => {
  /** Lift the filter of the chip, which the only one of the address shown. */
  async function liftFilter() {
    await userEvent.click(screen.getByRole("link", { name: /^Lever le filtre/ }));
  }

  it("lifts the lot from the sort asked and not arrived yet, the sort kept", async () => {
    render(await tree(ESTIMATE, `work_package_id=${LOT}`));
    const arrive = holdNavigations();
    await sortByInflation();
    await liftFilter();
    expect(Object.fromEntries(lastAsked())).toEqual({
      sort_by: "inflated_amount",
      sort_order: "asc",
    });
    await arrive();
  });

  it("lifts both parameters of the lot and keeps the structure read", async () => {
    render(
      await tree(
        { ...ESTIMATE, nodes: "nodes_amendment" },
        `structure=${AMENDMENT}&work_package_id=${LOT}&order_item_id=${LOT}`,
      ),
    );
    const arrive = holdNavigations();
    await liftFilter();
    expect(Object.fromEntries(lastAsked())).toEqual({ structure: AMENDMENT });
    await arrive();
  });
});

describe("the marks of a difference", () => {
  it.each([PLANNING, ESTIMATE])(
    "head the grid of the $name on a differential, and the grid of the main structure has none (US-0500)",
    async (shown) => {
      const { unmount } = render(
        await tree({ ...shown, nodes: "nodes_amendment" }, `structure=${AMENDMENT}`),
      );
      expect(screen.getAllByRole("columnheader")[0]).toHaveAccessibleName("Écart");
      expect(cell(3, "diff_mark")).toHaveTextContent("-Retiré");
      expect(cell(4, "diff_mark")).toHaveTextContent("+Ajouté");
      unmount();
      render(await tree({ ...shown, nodes: "nodes_amendment" }, ""));
      expect(screen.queryByRole("columnheader", { name: "Écart" })).not.toBeInTheDocument();
    },
  );
});

describe("the grid of each structure", () => {
  it.each([PLANNING, ESTIMATE])(
    "is mounted anew on the $name of another structure, the active cell back on its first row (#819.3)",
    async (shown) => {
      const { rerender } = render(await tree(shown, ""));
      await userEvent.click(cell(2, "label"));
      expect(cell(2, "label")).toHaveAttribute("tabindex", "0");
      // The same rows served on the amendment, so that only the grid mounted anew tells its
      // state from that of the main structure.
      rerender(await tree(shown, `structure=${AMENDMENT}`));
      expect(cell(0, "label")).toHaveAttribute("tabindex", "0");
      expect(cell(2, "label")).toHaveAttribute("tabindex", "-1");
    },
  );
});
