// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FoldingFigures } from "./folding-figures";

/** A window whose width matches the large breakpoint or not. */
function windowOf(large: boolean) {
  vi.stubGlobal(
    "matchMedia",
    (query: string): MediaQueryList =>
      ({
        matches: large,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the cards of figures folded into a summary", () => {
  it("are folded below 1024 points, where the totals of the grid must stay in view [WF-IHM-0100-A]", () => {
    windowOf(false);
    const { container } = render(
      <FoldingFigures title="Key figures">
        <p>Total</p>
      </FoldingFigures>,
    );
    expect(screen.getByText("Key figures")).toBeInTheDocument();
    expect(container.querySelector("details")).not.toHaveAttribute("open");
  });

  it("are open from 1024 points up [WF-IHM-0100-A]", () => {
    windowOf(true);
    const { container } = render(
      <FoldingFigures title="Key figures">
        <p>Total</p>
      </FoldingFigures>,
    );
    expect(container.querySelector("details")).toHaveAttribute("open");
  });
});
