// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { PROJECT_STATES as STATES, type ProjectState } from "@/navigation/home";
import { expectAccessible } from "@/test/axe";

import { ProjectStateBadge } from "./project-state-badge";

const LOCALES: readonly Locale[] = ["fr", "en"];

/** The badges of every state, in a page of a language. */
function badges(locale: Locale) {
  const { container, unmount } = render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {STATES.map((state) => (
        <ProjectStateBadge key={state} state={state} />
      ))}
    </NextIntlClientProvider>,
  );
  return { found: [...container.children], container, unmount };
}

/** What a badge shows once its colour is gone: its markup without its classes, and its icon. */
function uncoloured(badge: Element) {
  const copy = badge.cloneNode(true) as Element;
  for (const element of [copy, ...copy.querySelectorAll("*")]) {
    element.removeAttribute("class");
  }
  return { seen: copy.outerHTML, shape: copy.querySelector("svg")?.innerHTML ?? "" };
}

/** Whether the values of a list are all different, and none empty. */
function allDistinct(values: readonly string[]): boolean {
  return new Set(values).size === values.length && values.every((value) => value !== "");
}

describe("the badge of the state of a project", () => {
  it.each(LOCALES)("writes the word of each state in %s, and draws its icon", (locale) => {
    // Chaque état rend son mot et son icône (#523).
    const { found, unmount } = badges(locale);
    expect(found.map((badge) => badge.textContent)).toEqual(
      STATES.map((state) => CATALOGUES[locale].enums.ProjectState[state]),
    );
    for (const badge of found) {
      expect(badge.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    }
    unmount();
  });

  it("fills each state with its token of the charter, and writes it in the text of that token", () => {
    const { found, unmount } = badges("fr");
    const tokens = {
      created: "created",
      pricing: "pricing",
      in_progress: "in-progress",
      completed: "completed",
      lost: "lost",
      abandoned: "abandoned",
    } satisfies Record<ProjectState, string>;
    STATES.forEach((state, at) => {
      expect(found[at]).toHaveClass(`bg-state-${tokens[state]}`);
      expect(found[at]).toHaveClass(`text-state-${tokens[state]}-foreground`);
    });
    unmount();
  });

  it("leaves each state identifiable in a grey copy, by its icon and its word [WF-IHM-0070-A]", () => {
    // Une copie d'écran en niveaux de gris laisse identifier chaque signalement : without its
    // classes — and so its colour —, each state keeps an icon of its own and a word of its own.
    for (const locale of LOCALES) {
      const { found, unmount } = badges(locale);
      expect(allDistinct(found.map((badge) => uncoloured(badge).shape))).toBe(true);
      expect(allDistinct(found.map((badge) => badge.textContent))).toBe(true);
      unmount();
    }
  });

  it("never tells two states apart by the colour alone [WF-IHM-0070-A]", () => {
    // Aucun écran ne distingue deux états par la seule couleur : with every class taken away, no
    // two states look alike.
    const { found, unmount } = badges("fr");
    expect(allDistinct(found.map((badge) => uncoloured(badge).seen))).toBe(true);
    unmount();
  });

  it("breaks no rule of accessibility", async () => {
    const { container } = badges("en");
    await expectAccessible(container);
  });
});
