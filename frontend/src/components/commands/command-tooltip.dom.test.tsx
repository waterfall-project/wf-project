// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";

import { CommandTooltip } from "./command-tooltip";
import { MenuCommand } from "./menu-command";

// The tooltip of a command (US-0580, #1071), each of the properties of WCAG 1.4.13 the proposal of
// #1071 names: opened on hover as on the focus of the keyboard, closed by Escape the focus left
// where it is, kept open while the pointer passes over it, linked by `aria-describedby`, carrying
// nothing alone.

const REDO = "Control+Shift+Z Meta+Shift+Z";
const HELP = "Rétablit la dernière saisie annulée.";
const LACKING = "Indisponible tant que le serveur ne conserve pas l’historique.";

/** Render in a language, as the shell hands its texts to a screen. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** Redo, its help read from the catalogue as a screen reads it. */
function Redo({
  unavailable,
  describedBy,
}: {
  readonly unavailable?: string;
  readonly describedBy?: string;
}) {
  const said = useTranslations("commands");
  return (
    <CommandTooltip
      label="Rétablir"
      help={said("redo.help")}
      keys={REDO}
      unavailable={unavailable}
      describedBy={describedBy}
    >
      <Button type="button" aria-label="Rétablir">
        R
      </Button>
    </CommandTooltip>
  );
}

/** Redo, available, or unavailable for the reason said beside it. */
function redo(unavailable?: string) {
  return (
    <>
      <Redo {...(unavailable === undefined ? {} : { unavailable, describedBy: "reason" })} />
      {unavailable === undefined ? null : <p id="reason">{unavailable}</p>}
    </>
  );
}

/** Redo in a context menu, as the menu of a cell offers it, with the condition it lacks if any. */
function inMenu(unavailable?: string) {
  return (
    <ContextMenu>
      <ContextMenuTrigger>Zone</ContextMenuTrigger>
      <ContextMenuContent aria-label="Menu">
        <MenuCommand
          item={ContextMenuItem}
          label="Rétablir"
          help={HELP}
          keys={REDO}
          unavailable={unavailable}
          onSelect={(event) => {
            event.preventDefault();
          }}
        />
      </ContextMenuContent>
    </ContextMenu>
  );
}

/** Open the context menu by a right click, the focus on its first item. */
async function openMenu(): Promise<HTMLElement> {
  fireEvent.contextMenu(screen.getByText("Zone"), { clientX: 300, clientY: 200 });
  const menu = await screen.findByRole("menu", { name: "Menu" });
  await userEvent.keyboard("{ArrowDown}");
  expect(within(menu).getByRole("menuitem", { name: "Rétablir" })).toHaveFocus();
  return menu;
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

/** Let the rest of the pointer, or of the focus in a menu, run out. */
async function rest() {
  await act(() => new Promise((resolve) => setTimeout(resolve, 400)));
}

describe("the tooltip of a command", () => {
  // aucune exigence : propre à l'US (US-0580, le composant commun des infobulles).
  it("opens on hover, with the name, the help of the catalogue and the keys, describing the control by its help", async () => {
    inLanguage(redo());
    const button = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.hover(button);
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent(HELP);
    expect(button).toHaveAccessibleDescription(HELP);
    // What is shown: the name, the help and the keys, those of the workstation alone.
    const shown = document.querySelector("[data-slot=tooltip-content]");
    expect([...(shown?.querySelectorAll("p") ?? [])].map((line) => line.textContent)).toEqual([
      "Rétablir",
      HELP,
    ]);
    expect([...(shown?.querySelectorAll("kbd") ?? [])].map((key) => key.textContent)).toEqual([
      "Ctrl+Maj+Z",
    ]);
  });

  // aucune exigence : propre à l'US (US-0580, WCAG 1.4.13).
  it("opens on the focus of the keyboard at once, and closes by Escape, the focus left on the control", async () => {
    inLanguage(redo());
    const button = screen.getByRole("button", { name: "Rétablir" });
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(screen.getByRole("tooltip")).toHaveTextContent(HELP);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(button).toHaveFocus();
    expect(button).not.toHaveAttribute("aria-describedby");
  });

  // aucune exigence : propre à l'US (US-0580, WCAG 1.4.13).
  it("stays open while the pointer passes from the control over it", async () => {
    inLanguage(redo());
    await userEvent.hover(screen.getByRole("button", { name: "Rétablir" }));
    await screen.findByRole("tooltip");
    const shown = document.querySelector<HTMLElement>("[data-slot=tooltip-content]");
    if (shown === null) {
      throw new Error("no tooltip shown");
    }
    await userEvent.hover(shown);
    await rest();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    // Escape closes it there too.
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  // aucune exigence : propre à l'US (US-0580, les touches à une seule source).
  it("sets the keys it shows on the control, as aria-keyshortcuts names them: one source", () => {
    inLanguage(redo());
    expect(screen.getByRole("button", { name: "Rétablir" })).toHaveAttribute(
      "aria-keyshortcuts",
      REDO,
    );
  });

  // aucune exigence : propre à l'US (US-0580, les touches selon le poste).
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

  // aucune exigence : propre à l'US (US-0580, les touches selon le poste).
  it("writes the keys on a Mac by their signs, Cmd for Ctrl", async () => {
    const restore = onMac();
    try {
      inLanguage(redo());
      await userEvent.tab();
      expect(document.querySelector("[data-slot=tooltip-content] kbd")?.textContent).toBe("⌘⇧Z");
    } finally {
      restore();
    }
  });

  it("says the condition an unavailable command lacks, the command reached and described by it where it is said [WF-IHM-0090-A]", async () => {
    inLanguage(redo(LACKING));
    const button = screen.getByRole("button", { name: "Rétablir" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toBeEnabled();
    expect(button).toHaveAccessibleDescription(LACKING);
    await userEvent.tab();
    expect(button).toHaveFocus();
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      `${HELP}${LACKING}`,
    );
    // The tooltip open, the control is described by the condition and by the help.
    expect(button).toHaveAccessibleDescription(`${LACKING} ${HELP}`);
  });

  it("describes an unavailable command by its condition, said nowhere else, tooltip closed and open [WF-IHM-0090-A]", async () => {
    inLanguage(<Redo unavailable={LACKING} />);
    const button = screen.getByRole("button", { name: "Rétablir" });
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(button).toHaveAccessibleDescription(LACKING);
    // The condition is no text of the page: only the description of the control.
    expect(screen.queryByText(LACKING)).not.toBeVisible();
    await userEvent.tab();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(button).toHaveAccessibleDescription(`${LACKING} ${HELP}`);
  });

  // aucune exigence : propre à l'US (US-0580, Échap dans un menu).
  it("leaves Escape pressed at once in a menu to the menu, which closes", async () => {
    inLanguage(inMenu());
    await openMenu();
    expect(screen.queryByRole("tooltip")).toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    await rest();
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  // aucune exigence : propre à l'US (US-0580, Échap dans un menu).
  it("opens in a menu once the focus rests on the item, closes first by Escape, the menu by a second", async () => {
    inLanguage(inMenu());
    const menu = await openMenu();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(HELP);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("tooltip")).toBeNull();
    expect(menu).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "Rétablir" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  // aucune exigence : propre à l'US (US-0580, le focus rendu au menu, #1414).
  it("stays open in a menu when the focus goes from its item to the menu itself, as the pointer leaving an item does", async () => {
    inLanguage(inMenu());
    const menu = await openMenu();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(HELP);
    fireEvent.blur(within(menu).getByRole("menuitem", { name: "Rétablir" }), {
      relatedTarget: menu,
    });
    expect(screen.getByRole("tooltip")).toHaveTextContent(HELP);
  });

  // aucune exigence : propre à l'US (US-0580, le focus rendu au menu, #1414).
  it("closes in a menu when the focus goes from its item to anything but the menu", async () => {
    inLanguage(inMenu());
    const menu = await openMenu();
    await screen.findByRole("tooltip");
    fireEvent.blur(within(menu).getByRole("menuitem", { name: "Rétablir" }), {
      relatedTarget: document.body,
    });
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("describes an item of a menu by the condition it lacks, said nowhere else, tooltip closed and open [WF-IHM-0090-A]", async () => {
    inLanguage(inMenu(LACKING));
    const menu = await openMenu();
    const item = within(menu).getByRole("menuitem", { name: "Rétablir" });
    expect(item).toHaveAttribute("aria-disabled", "true");
    expect(item).toHaveAccessibleDescription(LACKING);
    // The condition is the description of the item alone, not a text of the menu.
    expect(within(menu).queryByText(LACKING)).not.toBeVisible();
    await screen.findByRole("tooltip");
    expect(document.querySelector("[data-slot=tooltip-content]")).toHaveTextContent(
      `${HELP}${LACKING}`,
    );
    expect(item).toHaveAccessibleDescription(`${LACKING} ${HELP}`);
    await expectAccessible(menu);
  });

  // aucune exigence : propre à l'US (US-0580, le repos dans un menu).
  it("opens no tooltip in a menu once its item is pressed", async () => {
    inLanguage(inMenu());
    const menu = await openMenu();
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Rétablir" }));
    await rest();
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  // aucune exigence : propre à l'US (US-0580, un fournisseur à la racine de la coquille).
  it.each([
    ["shares the delay with the next one under one provider: it opens at once", true],
    ["waits its own delay outside any provider", false],
  ] as const)("%s", async (_, provided) => {
    const commands = (
      <>
        <CommandTooltip label="Annuler" help="Annule.">
          <Button type="button">A</Button>
        </CommandTooltip>
        <CommandTooltip label="Rétablir" help={HELP}>
          <Button type="button">B</Button>
        </CommandTooltip>
      </>
    );
    inLanguage(provided ? <TooltipProvider>{commands}</TooltipProvider> : commands);
    await userEvent.hover(screen.getByRole("button", { name: "A" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Annule.");
    await userEvent.keyboard("{Escape}");
    await userEvent.hover(screen.getByRole("button", { name: "B" }));
    if (provided) {
      expect(screen.getByRole("tooltip")).toHaveTextContent(HELP);
    } else {
      expect(screen.queryByRole("tooltip")).toBeNull();
      expect(await screen.findByRole("tooltip")).toHaveTextContent(HELP);
    }
  });

  // aucune exigence : propre à l'US (US-0580, WCAG 1.4.13).
  it("breaks no rule of axe, open on an unavailable command", async () => {
    const { container } = inLanguage(redo("Indisponible."));
    await userEvent.tab();
    await screen.findByRole("tooltip");
    await expectAccessible(container);
    await expectAccessible(document.body);
  });
});
