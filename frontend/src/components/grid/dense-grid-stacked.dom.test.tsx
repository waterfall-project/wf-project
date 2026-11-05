// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { allShown } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import { type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r",
  useSearchParams: () => new URLSearchParams(""),
}));

const witness = example("nodes") as NodeList;
const PLAIN: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = {
  key: "plain",
  name: "estimate",
  searched: true,
  rowKey: (node) => node.node_id,
  columns: ESTIMATE_GRID.columns.map((column) => ({ ...column, pinned: false })),
};

/** The grid, stacked or not; returns the element that scrolls. */
function renderGrid(stacked: boolean | undefined): HTMLElement {
  const { container } = render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <DenseGrid
        config={PLAIN}
        rows={witness.items}
        totals={witness.totals}
        totalsCaption={() => "—"}
        query={{ sort: undefined, search: undefined, size: undefined }}
        preferences={allShown(ESTIMATE_GRID.columns)}
        stacked={stacked}
      />
    </NextIntlClientProvider>,
  );
  const scroller = container.querySelector<HTMLElement>(".max-h-svh");
  if (scroller === null) {
    throw new Error("the element that scrolls is missing");
  }
  return scroller;
}

/** A window of `inner` points, the page scrolled by `scrolled`, the frame `top` from the view. */
function layOut(inner: number, scrolled: number, top: number, height = 400) {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(height);
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    top,
  } as DOMRect);
  vi.stubGlobal("innerHeight", inner);
  vi.stubGlobal("scrollY", scrolled);
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("the grid a screen stacks under its cards", () => {
  it("is bounded to the window less where it starts on the page, scrolled or not [WF-IHM-0100-A]", () => {
    layOut(900, 100, 300);
    expect(renderGrid(true).style.maxHeight).toBe("500px");
  });

  it("is kept as the window is resized and as the page above it changes [WF-IHM-0100-A]", () => {
    // Only what observes the page is the frame's: the virtualizer observes its own elements.
    const pageObservers: (() => void)[] = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(private readonly callback: () => void) {}
        observe = (target: Element) => {
          if (target === document.body) {
            pageObservers.push(this.callback);
          }
        };
        unobserve = () => undefined;
        disconnect = () => undefined;
      },
    );
    layOut(900, 0, 300);
    const scroller = renderGrid(true);
    expect(scroller.style.maxHeight).toBe("600px");
    layOut(700, 0, 300);
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(scroller.style.maxHeight).toBe("400px");
    layOut(700, 0, 350);
    act(() => {
      pageObservers.forEach((callback) => {
        callback();
      });
    });
    expect(scroller.style.maxHeight).toBe("350px");
  });

  it("is bounded without a ResizeObserver too [WF-IHM-0100-A]", () => {
    vi.stubGlobal("ResizeObserver", undefined);
    layOut(900, 0, 300);
    expect(renderGrid(true).style.maxHeight).toBe("600px");
  });

  it("is not bounded where its screen does not stack it [WF-IHM-0100-A]", () => {
    layOut(900, 0, 300);
    expect(renderGrid(undefined).style.maxHeight).toBe("");
  });

  it("is not bounded where the browser lays nothing out, nor where no room is left [WF-IHM-0100-A]", () => {
    layOut(900, 0, 300, 0);
    expect(renderGrid(true).style.maxHeight).toBe("");
    vi.restoreAllMocks();
    layOut(900, 0, 1000);
    expect(renderGrid(true).style.maxHeight).toBe("");
  });
});
