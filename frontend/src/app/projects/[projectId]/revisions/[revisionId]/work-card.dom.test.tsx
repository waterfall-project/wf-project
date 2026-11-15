// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a grid of work (EP-25, US-2140/L1): it holds what it is given, the planning start
 * date above the grid among it, and shrinks to the room its screen leaves it only when the screen
 * fills the window — a screen that does not fill is not stretched (WF-IHM-0100-A).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { expectAccessible } from "@/test/axe";

import { WorkCard } from "./work-card";

describe("WorkCard", () => {
  it("holds the date above the grid in its body, a card of the page [WF-IHM-0100-A]", async () => {
    const { container } = render(
      <WorkCard fill>
        <p>Date de début de planning</p>
        <div role="grid" aria-label="Planification" />
      </WorkCard>,
    );
    const card = container.querySelector("[data-slot='work-card']");
    expect(card).not.toBeNull();
    expect(card).toContainElement(screen.getByText("Date de début de planning"));
    expect(card).toContainElement(screen.getByRole("grid", { name: "Planification" }));
    await expectAccessible(container);
  });

  it("takes the room its screen leaves it when it fills the window, and no more", () => {
    const { container } = render(
      <>
        <WorkCard fill>
          <p>plein</p>
        </WorkCard>
        <WorkCard>
          <p>libre</p>
        </WorkCard>
      </>,
    );
    const [filled, free] = Array.from(container.querySelectorAll("[data-slot='work-card']"));
    expect(filled?.className).toContain("flex-1");
    expect(filled?.className).toContain("min-h-0");
    expect(free?.className).not.toContain("flex-1");
  });
});
