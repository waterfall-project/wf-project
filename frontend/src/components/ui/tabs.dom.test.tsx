// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { expectAccessible } from "@/test/axe";

import { Tabs, tabVariants } from "./tabs";

const CURRENT_LOOK = [
  "aria-[current=true]:border-primary",
  "aria-[current=page]:border-primary",
  "aria-pressed:border-primary",
];

function chronologies() {
  return render(
    <Tabs aria-label="Chronologies">
      <a href="#launch" aria-current="true" className={tabVariants()}>
        Launch
      </a>
      <a href="#delivery" className={tabVariants()}>
        Delivery
      </a>
    </Tabs>,
  );
}

describe("Tabs", () => {
  it("say the current choice by a line under it and by aria-current, never by a fill #3088 [WF-IHM-0070-A]", () => {
    chronologies();
    const row = screen.getByRole("navigation", { name: "Chronologies" });
    const current = within(row).getByRole("link", { name: "Launch" });
    const other = within(row).getByRole("link", { name: "Delivery" });
    expect(current).toHaveAttribute("aria-current", "true");
    expect(other).not.toHaveAttribute("aria-current");
    // The line is a shape, which a grey copy keeps; the look follows the attribute a reader hears.
    expect(current).toHaveClass("border-b-2", ...CURRENT_LOOK);
    // The fill is kept for the main command of a card.
    expect(tabVariants()).not.toMatch(/(^|\s|:)bg-/);
  });

  it("are reached one by one by the keyboard, the focus drawn by the ring [WF-IHM-0100-A]", async () => {
    chronologies();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Launch" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Delivery" })).toHaveFocus();
    expect(tabVariants()).toMatch(/focus-visible:ring-\[3px\]/);
  });

  it("say a current toggle by aria-pressed, as a filter of the screen does #3088", () => {
    render(
      <Tabs aria-label="Perimeter">
        <button type="button" aria-pressed="true" className={tabVariants()}>
          Open
        </button>
        <button type="button" aria-pressed="false" className={tabVariants()}>
          Closed
        </button>
      </Tabs>,
    );
    expect(screen.getByRole("button", { name: "Open", pressed: true })).toHaveClass(
      "aria-pressed:border-primary",
      "aria-pressed:text-foreground",
    );
    expect(screen.getByRole("button", { name: "Closed", pressed: false })).toBeInTheDocument();
  });

  it("hold the rules of accessibility [WF-IHM-0100-A]", async () => {
    const { container } = chronologies();
    await expectAccessible(container);
  });
});
