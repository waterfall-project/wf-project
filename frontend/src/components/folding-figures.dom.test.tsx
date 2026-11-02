// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FoldingFigures } from "./folding-figures";

/** A window whose width matches the large breakpoint or not; returns how to resize it. */
function windowOf(large: boolean): (now: boolean) => void {
  let matches = large;
  const listeners = new Set<() => void>();
  vi.stubGlobal(
    "matchMedia",
    (query: string): MediaQueryList =>
      ({
        get matches() {
          return matches;
        },
        media: query,
        addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
        removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
      }) as unknown as MediaQueryList,
  );
  return (now) => {
    matches = now;
    act(() => {
      listeners.forEach((listener) => {
        listener();
      });
    });
  };
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

  it("are set anew at the breakpoint without the cards being mounted again [WF-IHM-0100-A]", () => {
    const resize = windowOf(false);
    const { container } = render(
      <FoldingFigures title="Key figures">
        <p>Total</p>
      </FoldingFigures>,
    );
    const details = container.querySelector("details");
    const card = screen.getByText("Total");
    expect(details).not.toHaveAttribute("open");
    resize(true);
    expect(container.querySelector("details")).toBe(details);
    expect(screen.getByText("Total")).toBe(card);
    expect(details).toHaveAttribute("open");
    resize(false);
    expect(container.querySelector("details")).toBe(details);
    expect(screen.getByText("Total")).toBe(card);
    expect(details).not.toHaveAttribute("open");
  });
});
