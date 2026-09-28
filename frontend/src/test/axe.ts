// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accessibility check of the component tests: axe-core, run on what a component
 * rendered into the document of happy-dom, at the WCAG A and AA levels (§3.6, WF-IHM-0100).
 *
 * happy-dom lays nothing out and applies no stylesheet of Tailwind: what depends on them —
 * the contrast of the colours — is left to the end-to-end check in a browser (US-0200), and
 * to contrast.test.ts for the tokens. Everything else axe knows is checked here: names,
 * roles, labels, landmarks, the structure of lists and headings.
 */
import axe from "axe-core";
import { expect } from "vitest";

// The rules of WCAG 2.x, levels A and AA, as axe tags them.
const LEVELS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** Check that what a container holds breaks none of the rules of axe at the AA level. */
export async function expectAccessible(container: Element): Promise<void> {
  const results = await axe.run(container, {
    runOnly: { type: "tag", values: LEVELS },
    rules: { "color-contrast": { enabled: false } },
  });
  const violations = results.violations.map((violation) => ({
    rule: violation.id,
    nodes: violation.nodes.map((node) => node.html),
  }));
  expect(violations).toEqual([]);
}
