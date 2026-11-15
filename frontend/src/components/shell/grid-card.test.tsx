// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a grid (EP-25, US-2310/L2, #3421): it holds what it is given, the planning start date
 * above the grid among it, in the order it is given (WF-IHM-0100-A), and it names nothing of its own.
 * A server component with no state, so tried in the node project; that it fills the window and that
 * its rows keep their height is measured in a browser by `e2e/work-cards.spec.ts`, and its
 * accessibility — keyboard, contrast, zoom — by `e2e/accessibility.spec.ts`, which draws these
 * screens by `tableScreens()` of `e2e/routes.ts` (#3423).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GridCard } from "./grid-card";

describe("GridCard", () => {
  it("holds the date above the grid in its body, a card of the page [WF-IHM-0100-A]", () => {
    const html = renderToStaticMarkup(
      <GridCard fill>
        <p>Date de début de planning</p>
        <div role="grid" aria-label="Planification" />
      </GridCard>,
    );
    const body = html.indexOf('data-slot="card-content"');
    const date = html.indexOf("Date de début de planning");
    const grid = html.indexOf('role="grid"');
    expect(html.indexOf('data-slot="grid-card"'), "one card").toBeGreaterThanOrEqual(0);
    expect(body, "the card has a body").toBeGreaterThan(0);
    expect(date, "the date is in the body").toBeGreaterThan(body);
    expect(grid, "the grid is below the date").toBeGreaterThan(date);
  });

  it("has no title, no header and no region of its own: its screen names it [WF-IHM-0100-A]", () => {
    const html = renderToStaticMarkup(<GridCard>{"A chart"}</GridCard>);
    expect(html).not.toContain('data-slot="card-header"');
    expect(html).not.toContain('data-slot="card-title"');
    expect(html).not.toContain("<section");
  });

  it("takes the room its screen leaves it only when it is told to [WF-IHM-0100-A]", () => {
    expect(renderToStaticMarkup(<GridCard fill>{"x"}</GridCard>)).toContain("min-h-0 flex-1");
    expect(renderToStaticMarkup(<GridCard>{"x"}</GridCard>)).not.toContain("min-h-0 flex-1");
  });
});
