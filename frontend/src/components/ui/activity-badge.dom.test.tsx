// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { expectAccessible } from "@/test/axe";

import { ActivityBadge } from "./activity-badge";

/** Render the state of an object, and the element that carries it. */
function state(active: boolean, word: string): HTMLElement {
  const { container } = render(<ActivityBadge active={active}>{word}</ActivityBadge>);
  const shown = container.querySelector<HTMLElement>("[data-slot='activity']");
  if (shown === null) {
    throw new Error("no state rendered");
  }
  return shown;
}

describe("ActivityBadge", () => {
  it("says « Actif » by a dot and its word, the dot in the token of its own #3249 [WF-IHM-0070-A]", () => {
    const shown = state(true, "Actif");
    expect(shown).toHaveTextContent(/^Actif$/);
    const dot = shown.querySelector("[aria-hidden='true']");
    expect(dot).toHaveClass("rounded-full", "bg-active-mark");
    // Not a token of a zone: a signal is `Signal`'s alone.
    expect(shown.outerHTML).not.toMatch(/signal-/);
    expect(shown.querySelector("svg")).toBeNull();
  });

  it("keeps the mark of « Désactivé », an outlined badge and the struck circle, without the dot [WF-IHM-0070-A]", () => {
    const shown = state(false, "Désactivé");
    expect(shown).toHaveTextContent(/^Désactivé$/);
    expect(shown).toHaveClass("border");
    expect(shown.querySelector("svg.lucide-circle-off")).toHaveAttribute("aria-hidden", "true");
    expect(shown.querySelector(".bg-active-mark")).toBeNull();
  });

  it("tells the two states apart in a grey copy, by their shape and their word, not their colour alone [WF-IHM-0070-A]", () => {
    const active = state(true, "Actif");
    const inactive = state(false, "Désactivé");
    // What remains of each without its colours: the word, and the shape drawn beside it.
    const shape = (shown: HTMLElement) => ({
      word: shown.textContent,
      dot: shown.querySelector(".rounded-full") !== null,
      icon: shown.querySelector("svg") !== null,
      outlined: shown.classList.contains("border"),
    });
    expect(shape(active)).toEqual({ word: "Actif", dot: true, icon: false, outlined: false });
    expect(shape(inactive)).toEqual({ word: "Désactivé", dot: false, icon: true, outlined: true });
  });

  it("names nothing a reader of the screen would hear twice [WF-IHM-0100-A]", async () => {
    const { container } = render(
      <ul>
        <li>
          <ActivityBadge active>Actif</ActivityBadge>
        </li>
        <li>
          <ActivityBadge active={false}>Désactivé</ActivityBadge>
        </li>
      </ul>,
    );
    expect(container).toHaveTextContent("ActifDésactivé");
    await expectAccessible(container);
  });
});
