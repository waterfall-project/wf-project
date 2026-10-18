// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rules of axe for WCAG A and AA, run in the browser of a journey: where the colours are those the
 * browser paints, which the document of a unit test does not compute — the contrast of a text on
 * its background among them (WF-IHM-0100).
 *
 * axe-core is held at 4.13.0, without a range: 4.14 judges the button of the account against
 * « Label in Name » (WCAG 2.5.3, `label-content-name-mismatch`) — its visible initials are not in
 * its name, « Compte de … » — on every screen. Adopting 4.14 is a change of that name, and of the
 * tests that look the button up by it, not of a dependency.
 */
import { createRequire } from "node:module";

import type { Page } from "@playwright/test";

/** The tags axe gives the rules of WCAG 2.x, levels A and AA. */
const LEVELS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/**
 * What the tools of the development server of Next add to the page — their button, their panel,
 * in a shadow root of their own —, which the front built for production does not have.
 */
const DEVELOPMENT_TOOLS = "nextjs-portal";

/** A rule of axe broken, and where: each element by its selector, and what axe says of it. */
export interface AxeBreach {
  readonly rule: string;
  readonly nodes: readonly string[];
}

/** Give the page axe, once: the script weighs half a megabyte, and a page keeps it. */
async function withAxe(page: Page): Promise<void> {
  const loaded = await page.evaluate(() => "axe" in window);
  if (!loaded) {
    const require = createRequire(import.meta.url);
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  }
}

/** The violations of the rules of axe for WCAG A and AA, on the elements a selector finds. */
export async function axeViolations(page: Page, selector: string): Promise<string[]> {
  await withAxe(page);
  return page.evaluate(
    async ({ scope, tags }) => {
      const axe = (window as unknown as { axe: typeof import("axe-core") }).axe;
      const results = await axe.run(scope, { runOnly: { type: "tag", values: tags } });
      return results.violations.map((violation) => violation.id);
    },
    { scope: selector, tags: LEVELS },
  );
}

/** What axe said of a whole document: the rules broken, and the texts whose contrast it left. */
export interface AxeAudit {
  readonly breaches: readonly AxeBreach[];
  /**
   * The texts axe left without a measure of their contrast, by the reason it gives — over a
   * picture, partly hidden… —, those in a figure of curves, whose drawing it cannot read, apart.
   */
  readonly unmeasured: Readonly<Record<string, number>>;
}

/**
 * Every rule of axe for WCAG A and AA, run on the whole document, the tools of the development
 * server aside. Each element broken is said by its selector, and for the contrast of a text by
 * what axe measured: its colours and their ratio. A text axe left « incomplete » with a measure
 * that fails — a single character under the ratio expected, which it will not call a text, or a
 * text the colour of its background — is a breach as well: its two colours were measured.
 */
export async function axeAudit(page: Page): Promise<AxeAudit> {
  await withAxe(page);
  return page.evaluate(
    async ({ tags, tools }) => {
      const axe = (window as unknown as { axe: typeof import("axe-core") }).axe;
      const results = await axe.run(
        { exclude: [tools] },
        {
          runOnly: { type: "tag", values: tags },
          resultTypes: ["violations", "incomplete"],
          elementRef: true,
        },
      );
      interface Measure {
        fgColor?: string;
        bgColor?: string;
        contrastRatio?: number;
        messageKey?: string;
      }
      type Node = (typeof results.violations)[number]["nodes"][number];
      const measureOf = (node: Node) =>
        node.any.find((check) => check.id === "color-contrast")?.data as Measure | undefined;
      const said = (node: Node) => {
        const measure = measureOf(node);
        const where = `${node.target.join(" ")} ${node.html.slice(0, 120)}`;
        return measure?.contrastRatio === undefined
          ? where
          : `${where} (${String(measure.fgColor)} on ${String(measure.bgColor)}: ${String(measure.contrastRatio)}${measure.messageKey === undefined ? "" : `, ${measure.messageKey}`})`;
      };
      // A text left incomplete whose measure fails, its two colours measured: the colour of its
      // background, or too short to be called a text — axe leaves a measured text incomplete for
      // nothing else, under the ratio expected. Too short with a colour unmeasured, the measure is
      // wanting, not failing: axe writes its brevity over the reason it could not measure — a
      // picture under it, a box over it.
      const measuredBoth = (measure: Measure) =>
        measure.fgColor !== undefined && measure.bgColor !== undefined;
      const fails = (measure: Measure | undefined) =>
        measure !== undefined &&
        measuredBoth(measure) &&
        ["shortTextContent", "equalRatio"].includes(measure.messageKey ?? "");
      const reasonOf = (measure: Measure | undefined) => {
        const reason = measure?.messageKey ?? "no reason";
        return measure !== undefined && !measuredBoth(measure) && reason === "shortTextContent"
          ? `${reason}, colours unmeasured`
          : reason;
      };
      const left = results.incomplete
        .filter((rule) => rule.id === "color-contrast")
        .flatMap((rule) => rule.nodes);
      const breaches = results.violations.map((violation) => ({
        rule: violation.id,
        nodes: violation.nodes.map(said),
      }));
      const failing = left.filter((node) => fails(measureOf(node)));
      if (failing.length > 0) {
        breaches.push({ rule: "color-contrast, left incomplete by axe", nodes: failing.map(said) });
      }
      const unmeasured: Record<string, number> = {};
      for (const node of left.filter((each) => !fails(measureOf(each)))) {
        const figure = node.element instanceof Element && node.element.closest("figure") !== null;
        const reason = `${reasonOf(measureOf(node))}${figure ? " in a figure" : ""}`;
        unmeasured[reason] = (unmeasured[reason] ?? 0) + 1;
      }
      return { breaches, unmeasured };
    },
    { tags: LEVELS, tools: DEVELOPMENT_TOOLS },
  );
}
