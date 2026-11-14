// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rule of the commands of a screen (EP-25, « Une carte de section commune »; #3088, rules 2 to
 * 4), read in what a test rendered: in each card of a section (`SectionCard`), one filled command
 * at most — its principal command, when it creates or triggers —, none when the principal command
 * modifies, and every other outlined; at the right of the title of a screen (`PageHeader`), none
 * filled. A screen recomposed in cards calls `expectCommandRule` in its tests.
 *
 * A button or a link is filled when it carries the classes the filled variant of `buttonVariants`
 * has and the outlined one has not: read from the button itself, so that the rule follows the
 * charter when the button changes.
 */
import { expect } from "vitest";

import { buttonVariants } from "@/components/ui/button";

/** The classes that only the filled variant of a button carries. */
const FILLED = (() => {
  const outlined = new Set(buttonVariants({ variant: "outline" }).split(/\s+/));
  return buttonVariants({ variant: "default" })
    .split(/\s+/)
    .filter((name) => name !== "" && !outlined.has(name));
})();

/** Whether an element is drawn as a filled button. */
function filled(element: Element): boolean {
  return FILLED.length > 0 && FILLED.every((name) => element.classList.contains(name));
}

/** What a command is called in a breach: its accessible text, as a reader would find it. */
function nameOf(element: Element): string {
  return element.getAttribute("aria-label") ?? element.textContent.trim();
}

/** The filled buttons and links an element holds. */
function filledIn(root: Element): Element[] {
  return [...root.querySelectorAll("button, a")].filter(filled);
}

/** The breaches of the rule of the commands in what a container holds, one sentence each. */
export function commandRuleBreaches(container: ParentNode): string[] {
  const breaches: string[] = [];
  for (const header of container.querySelectorAll('[data-slot="screen-commands"]')) {
    for (const command of filledIn(header)) {
      breaches.push(`the screen offers « ${nameOf(command)} » filled`);
    }
  }
  for (const card of container.querySelectorAll('[data-slot="section-card"]')) {
    const title = card.getAttribute("aria-label") ?? "";
    const principal = card.querySelector('[data-slot="section-card-principal"]');
    const filledPrincipal = principal === null ? [] : filledIn(principal);
    for (const command of filledIn(card)) {
      if (!filledPrincipal.includes(command)) {
        breaches.push(`the card « ${title} » offers « ${nameOf(command)} » filled`);
      }
    }
    const does = principal?.getAttribute("data-does");
    if (does === "modify" && filledPrincipal.length > 0) {
      breaches.push(`the card « ${title} » fills a principal command that modifies`);
    }
    if ((does === "create" || does === "trigger") && filledPrincipal.length !== 1) {
      breaches.push(
        `the card « ${title} » has ${String(filledPrincipal.length)} filled principal commands, not one`,
      );
    }
  }
  return breaches;
}

/** Check that what a container holds keeps the rule of the commands. */
export function expectCommandRule(container: ParentNode): void {
  expect(commandRuleBreaches(container)).toEqual([]);
}
