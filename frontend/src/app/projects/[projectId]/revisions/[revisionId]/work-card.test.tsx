// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a grid of work (EP-25, US-2140/L1): it holds what it is given, the planning start
 * date above the grid among it, in the order it is given (WF-IHM-0100-A). A server component with
 * no state, so tried in the node project; that it fills the window and that its rows keep their
 * height is measured in a browser by `e2e/work-cards.spec.ts`, and its accessibility by
 * `accessibility.spec.ts`.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WorkCard } from "./work-card";

describe("WorkCard", () => {
  it("holds the date above the grid in its body, a card of the page [WF-IHM-0100-A]", () => {
    const html = renderToStaticMarkup(
      <WorkCard fill>
        <p>Date de début de planning</p>
        <div role="grid" aria-label="Planification" />
      </WorkCard>,
    );
    const body = html.indexOf('data-slot="card-content"');
    const date = html.indexOf("Date de début de planning");
    const grid = html.indexOf('role="grid"');
    expect(html.startsWith('<div data-slot="work-card"'), "one card").toBe(true);
    expect(body, "the card has a body").toBeGreaterThan(0);
    expect(date, "the date is in the body").toBeGreaterThan(body);
    expect(grid, "the grid is below the date").toBeGreaterThan(date);
  });
});
