// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accessibility check of the component tests: axe-core, run on what a component
 * rendered into the document of happy-dom, at the WCAG A and AA levels (§3.6, WF-IHM-0100).
 *
 * happy-dom lays nothing out and applies no stylesheet of Tailwind: what depends on them —
 * the contrast of the colours, the size of a target — cannot be judged here. The contrast of the
 * tokens is measured by contrast.test.ts; the rest waits for the accessibility check in a browser
 * (US-0200, to come — today only `e2e/paste.spec.ts` runs axe in one, on the paste dialog).
 * Everything else axe knows is checked here: names, roles, labels, landmarks, the structure of
 * lists and headings.
 *
 * Only the violations are reported: the selector and the HTML of every node that passes a rule
 * — the hundreds of cells of a grid — took axe as long to write as the rules took to run, and
 * the test reads none of it (EP-02/L28).
 */
import axe from "axe-core";
import { expect } from "vitest";

// The rules of WCAG 2.0 and 2.1, levels A and AA, as axe tags them. WCAG 2.2 AA adds one rule
// only, the size of a target, which needs a layout: no 2.2 tag here.
const LEVELS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

/** Check that what a container holds breaks none of the rules of axe at the AA level. */
export async function expectAccessible(container: Element): Promise<void> {
  const results = await axe.run(container, {
    runOnly: { type: "tag", values: LEVELS },
    rules: { "color-contrast": { enabled: false } },
    resultTypes: ["violations"],
  });
  const violations = results.violations.map((violation) => ({
    rule: violation.id,
    nodes: violation.nodes.map((node) => node.html),
  }));
  expect(violations).toEqual([]);
}
