// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";

import { CommandTooltip } from "./command-tooltip";

// The tooltip of a command (US-0580, #1071), each of the properties of WCAG 1.4.13 the proposal of
// #1071 names: opened on hover as on the focus of the keyboard, closed by Escape the focus left
// where it is, kept open while the pointer passes over it, linked by `aria-describedby`, carrying
// nothing alone.

const REDO = "Control+Shift+Z Meta+Shift+Z";

/** Render in a language, as the shell hands its texts to a screen. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** Redo, available, or unavailable for the reason said beside it. */
function redo(unavailable?: string) {
  return (
    <>
      <CommandTooltip
        label="Rétablir"
        help="redo"
        keys={REDO}
        unavailable={unavailable}
        describedBy={unavailable === undefined ? undefined : "reason"}
      >
        <Button type="button" aria-label="Rétablir">
          R
        </Button>
      </CommandTooltip>
      {unavailable === undefined ? null : <p id="reason">{unavailable}</p>}
    </>
  );
}

/** Run on a Mac, as its browser tells it; gives back the end of it. */
function onMac(): () => void {
  Object.defineProperty(navigator, "userAgent", {
    value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    configurable: true,
  });
  return () => {
    Reflect.deleteProperty(navigator, "userAgent");
  };
}

describe("the tooltip of a command", () => {
  it("opens on hover, with the name, the help of the catalogue and the keys, describing the control by its help (US-0580)", async () => {
    inLanguage(redo());
    const button = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.hover(button);
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("Rétablit la dernière saisie annulée.");
    expect(button).toHaveAccessibleDescription("Rétablit la dernière saisie annulée.");
    // What is shown: the name, the help and the keys, those of the workstation alone.
    const shown = document.querySelector("[data-slot=tooltip-content]");
    expect([...(shown?.querySelectorAll("p") ?? [])].map((line) => line.textContent)).toEqual([
      "Rétablir",
      "Rétablit la dernière saisie annulée.",
    ]);
    expect([...(shown?.querySelectorAll("kbd") ?? [])].map((key) => key.textContent)).toEqual([
      "Ctrl+Maj+Z",
    ]);
  });

  it("opens on the focus of the keyboard at once, and closes by Escape, the focus left on the control (US-0580)", async () => {
    inLanguage(redo());
    const button = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Rétablit la dernière saisie annulée.");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(button).toHaveFocus();
    expect(button).not.toHaveAttribute("aria-describedby");
  });

  it("stays open while the pointer passes from the control over it (US-0580)", async () => {
    inLanguage(redo());
    await userEvent.hover(screen.getByRole("button", { name: "Rétablir" }));
    await screen.findByRole("tooltip");
    const shown = document.querySelector<HTMLElement>("[data-slot=tooltip-content]");
    if (shown === null) {
      throw new Error("no tooltip shown");
    }
    await userEvent.hover(shown);
    await act(() => new Promise((resolve) => setTimeout(resolve, 400)));
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    // Escape closes it there too.
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("sets the keys it shows on the control, as aria-keyshortcuts names them: one source (US-0580)", () => {
    inLanguage(redo());
    expect(screen.getByRole("button", { name: "Rétablir" })).toHaveAttribute(
      "aria-keyshortcuts",
      REDO,
    );
  });

  it.each([
    ["fr", "Ctrl+Maj+Z"],
    ["en", "Ctrl+Shift+Z"],
  ] as const)(
    "writes the keys off a Mac by Ctrl, in the language of the reader: %s",
    async (locale, keys) => {
      inLanguage(redo(), locale);
      await userEvent.tab();
      expect(document.querySelector("[data-slot=tooltip-content] kbd")?.textContent).toBe(keys);
    },
  );

  it("writes the keys on a Mac by their signs, Cmd for Ctrl (US-0580)", async () => {
    const restore = onMac();
    try {
      inLanguage(redo());
      await userEvent.tab();
      expect(document.querySelector("[data-slot=tooltip-content] kbd")?.textContent).toBe("⌘⇧Z");
    } finally {
      restore();
    }
  });

  it("says the condition an unavailable command lacks, the command reached and described by it where it is said (WF-IHM-0090, US-0580)", async () => {
    inLanguage(redo("Indisponible tant que le serveur ne conserve pas l’historique."));
    const button = screen.getByRole("button", { name: "Rétablir" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toBeEnabled();
    expect(button).toHaveAccessibleDescription(
      "Indisponible tant que le serveur ne conserve pas l’historique.",
    );
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      "Rétablit la dernière saisie annulée.Indisponible tant que le serveur ne conserve pas l’historique.",
    );
    // The tooltip open, the control is described by the condition and by the help.
    expect(button).toHaveAccessibleDescription(
      "Indisponible tant que le serveur ne conserve pas l’historique. Rétablit la dernière saisie annulée.",
    );
  });

  it("opens in a menu once the focus rests on the item, and never after the item is pressed (US-0580)", async () => {
    inLanguage(
      <CommandTooltip label="Rétablir" help="redo" keys={REDO} inMenu>
        <button type="button">Rétablir</button>
      </CommandTooltip>,
    );
    const item = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.tab();
    // Escape pressed at once is the menu's: nothing is open yet.
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Rétablit la dernière saisie annulée.",
    );
    await userEvent.keyboard("{Escape}");
    // Pressed, the item opens no tooltip once the rest is over.
    await userEvent.click(item);
    await act(() => new Promise((resolve) => setTimeout(resolve, 400)));
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("breaks no rule of axe, open on an unavailable command", async () => {
    const { container } = inLanguage(redo("Indisponible."));
    await userEvent.tab();
    await screen.findByRole("tooltip");
    await expectAccessible(container);
    await expectAccessible(document.body);
  });
});
