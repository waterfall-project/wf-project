// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rules of axe, WCAG A and AA, run in the browser of a journey on what a selector finds: where
 * the colours are those the browser paints, which the document of a unit test does not compute —
 * the contrast of a text on its background among them (WF-IHM-0100).
 */
import { createRequire } from "node:module";

import type { Page } from "@playwright/test";

/** The violations of the rules of axe, WCAG A and AA, on the elements a selector finds. */
export async function axeViolations(page: Page, selector: string): Promise<string[]> {
  const require = createRequire(import.meta.url);
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  return page.evaluate(async (scope) => {
    const axe = (window as unknown as { axe: typeof import("axe-core") }).axe;
    const tags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
    const results = await axe.run(scope, { runOnly: { type: "tag", values: tags } });
    return results.violations.map((violation) => violation.id);
  }, selector);
}
