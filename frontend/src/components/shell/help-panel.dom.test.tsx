// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the online help (US-0580): opened from the header of a screen by its button or by F1,
 * it shows the page of the code of the screen, read from the files of the help by the server action
 * as it reads them in production; a link shows another page in the panel, Escape closes it and gives the focus back. The action is
 * spied, so that a page
 * with raw HTML, a failure and a late answer can be served.
 */
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { readHelp } from "@/api/actions/help";
import type { HelpReading } from "@/help/help";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";

import { PageHeader } from "./page-header";

const at = vi.hoisted(() => ({ pathname: "/projects/p/revisions/r/planning" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => at.pathname,
}));

vi.mock("@/api/actions/help", async (original) => {
  const actual = await original<typeof import("@/api/actions/help")>();
  return { readHelp: vi.fn(actual.readHelp) };
});

const real = vi.mocked(readHelp).getMockImplementation();

beforeEach(() => {
  at.pathname = "/projects/p/revisions/r/planning";
  vi.mocked(readHelp).mockClear();
  if (real !== undefined) {
    vi.mocked(readHelp).mockImplementation(real);
  }
});

/** The header of a screen, with its help, in the language of the interface. */
function renderHeader(locale: "fr" | "en" = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      <PageHeader title="Planification" />
      <input aria-label="Ailleurs" />
    </NextIntlClientProvider>,
  );
}

/** The first of the elements a query found, which found at least one. */
function first(elements: readonly HTMLElement[]): HTMLElement {
  const [element] = elements;
  if (element === undefined) {
    throw new Error("no element found");
  }
  return element;
}

/** The button of the help. */
function helpButton() {
  return screen.getByRole("button", { name: "Aide" });
}

/** The panel, once open on the page of a title. */
async function panel(title: string) {
  const dialog = await screen.findByRole("dialog", { name: title });
  return dialog;
}

describe("the panel of the help", () => {
  it("opens from the button of the header on the page of the screen, in its fixed sections [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    expect(helpButton()).toHaveAttribute("aria-keyshortcuts", "F1");
    await user.click(helpButton());
    const dialog = await panel("Planification");
    expect(readHelp).toHaveBeenCalledWith({ kind: "screen", code: "FBS-4.3" });
    expect(
      (await within(dialog).findAllByRole("heading", { level: 3 })).map((h) => h.textContent),
    ).toEqual([
      "Ce que montre l’écran",
      "Ses commandes",
      "Ses colonnes et ses valeurs calculées",
      "Les gestes au clavier",
      "Voir aussi",
    ]);
    // The parts of the screen lead to their own pages.
    expect(
      within(dialog).getByRole("navigation", { name: "Les parties de l’écran" }),
    ).toHaveTextContent("Grille de planningGantt");
    // A key is written as a key.
    expect((await within(dialog).findAllByText("Ctrl+Z"))[0]?.tagName).toBe("KBD");
  });

  it("opens by F1 anywhere on the screen, and closes by Escape, the focus given back [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    helpButton().focus();
    await user.keyboard("{F1}");
    const dialog = await panel("Planification");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(helpButton()).toHaveFocus();
  });

  it("opens by F1 from any element of the screen, and gives the focus back to it [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    const elsewhere = screen.getByRole("textbox", { name: "Ailleurs" });
    elsewhere.focus();
    await user.keyboard("{F1}");
    await panel("Planification");
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(elsewhere).toHaveFocus();
  });

  it("gives the focus back to the button when F1 was pressed with nothing focused [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    expect(document.body).toHaveFocus();
    await user.keyboard("{F1}");
    await panel("Planification");
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(helpButton()).toHaveFocus();
  });

  it("ignores F1 with a modifier, which is another command of the browser [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.keyboard("{Control>}{F1}{/Control}");
    await user.keyboard("{Shift>}{F1}{/Shift}");
    await user.keyboard("{Alt>}{F1}{/Alt}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(readHelp).not.toHaveBeenCalled();
  });

  it("says its French pages are French in an interface in English, title and body [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader("en");
    await user.click(screen.getByRole("button", { name: "Help" }));
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    const title = within(dialog).getByRole("heading", { name: "Planification" });
    expect(title).toHaveAttribute("lang", "fr");
    expect(dialog.querySelectorAll('[lang="fr"]').length).toBeGreaterThan(1);
    expect(dialog.querySelector('[lang="fr"] h3')).not.toBeNull();
    // What is the interface's own — the name of the list of parts — is not said French.
    expect(
      within(dialog).getByRole("navigation", { name: "The parts of the screen" }).closest("[lang]"),
    ).toHaveAttribute("lang", "en");
    await expectAccessible(dialog);
  });

  it("puts the body, which scrolls, in the order of the keyboard, named by the title [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    const body = within(dialog).getByRole("region", { name: "Planification" });
    expect(body).toHaveAttribute("tabindex", "0");
    // Tab goes from the title's neighbours — the close button — to the body.
    within(dialog).getByRole("button", { name: "Fermer l’aide" }).focus();
    await user.tab();
    expect(body).toHaveFocus();
  });

  it("is accessible, open: named by its title, its sections and its links named [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    await expectAccessible(dialog);
  });

  it("follows a link to a notion in the panel, its title focused, and comes back [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    await user.click(
      first(await within(dialog).findAllByRole("link", { name: "valeur planifiée" })),
    );
    const notion = await panel("La valeur planifiée");
    await waitFor(() => {
      expect(within(notion).getByRole("heading", { name: "La valeur planifiée" })).toHaveFocus();
    });
    expect(notion).toHaveTextContent("Désigne la part du budget de référence");
    await user.click(
      within(notion).getByRole("button", { name: "Revenir à la page précédente de l’aide" }),
    );
    await panel("Planification");
  });

  it("says that the help of a page not written yet is to come [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    // The link is to a page the real files have: the action answers it as a page to come.
    const target = { kind: "screen", code: "FBS-4.4" } as const;
    vi.mocked(readHelp).mockResolvedValueOnce({
      page: { kind: "pending", target },
      index: [],
    } satisfies HelpReading);
    await user.click(first(await within(dialog).findAllByRole("link", { name: "le devis" })));
    await waitFor(() => {
      expect(within(dialog).getByText("L’aide de cette page est à venir.")).toBeInTheDocument();
    });
    expect(readHelp).toHaveBeenLastCalledWith(target);
  });

  it("renders no raw HTML a page would hold, nor an image, nor a link out of the help [WF-IHM-0140-A]", async () => {
    vi.mocked(readHelp).mockResolvedValue({
      page: {
        kind: "written",
        target: { kind: "screen", code: "FBS-4.3" },
        title: "Planification",
        intro: "",
        sections: [
          {
            heading: "Ce que montre l’écran",
            body: 'Avant <b>gras</b> <script>alert(1)</script> ![image](x.png) [dehors](https://example.org) et [le devis](FBS-4.4.md).\n\n<div onclick="x">bloc</div>',
          },
        ],
      },
      index: [],
    } satisfies HelpReading);
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    const section = (
      await within(dialog).findByRole("heading", { name: "Ce que montre l’écran" })
    ).closest("section");
    expect(section?.querySelector("b, script, img, div")).toBeNull();
    // The tags are dropped, their text kept inert.
    expect(section).not.toHaveTextContent("<b>");
    expect(section).not.toHaveTextContent("<script>");
    expect(within(dialog).queryByRole("link", { name: "dehors" })).toBeNull();
    expect(section).toHaveTextContent("dehors");
    expect(within(dialog).getByRole("link", { name: "le devis" })).toBeInTheDocument();
  });

  it("drops the answer of a page asked before the one shown, and says a failed reading", async () => {
    let release: (reading: HelpReading | undefined) => void = () => undefined;
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    // The link to the estimate answers late; the one to a notion fails before it.
    vi.mocked(readHelp)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            release = resolve;
          }),
      )
      .mockRejectedValueOnce(new Error("out of reach"));
    await user.click(first(await within(dialog).findAllByRole("link", { name: "le devis" })));
    await user.click(helpButtonInPanel(dialog));
    await waitFor(() => {
      expect(within(dialog).getByRole("alert")).toHaveTextContent("L’aide n’a pas pu être lue.");
    });
    await act(async () => {
      release(await (real ?? readHelp)({ kind: "screen", code: "FBS-4.4" }));
    });
    expect(within(dialog).getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Chiffrage et devis" })).toBeNull();
  });

  it("offers no help where the table of the functions knows no screen", () => {
    at.pathname = "/account";
    renderHeader();
    expect(screen.queryByRole("button", { name: "Aide" })).toBeNull();
  });
});

/** The button of the panel that comes back to the page of the screen. */
function helpButtonInPanel(dialog: HTMLElement) {
  return within(dialog).getByRole("button", { name: "Revenir à l’aide de l’écran" });
}
