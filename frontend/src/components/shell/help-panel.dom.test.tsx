// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The panel of the online help (US-0580): opened from the header of a screen by its button or by F1,
 * it shows the page of the code of the screen, read from the files of the help by the server action
 * as it reads them in production; a link shows another page in the panel, a search finds the pages
 * by their titles; Escape closes it and gives the focus back. The action is spied, so that a page
 * with raw HTML, a failure and a late answer can be served.
 *
 * The renderer of the Markdown, which the panel loads lazily, is loaded with this file, before any
 * test: its first loading compiles `react-markdown` and its plugins, which took more than the
 * second a query waits on a loaded workstation, and failed the first test to open the panel
 * (#1537). Its loading is made twice as slow as that second here, so that a test that paid it would
 * fail every time.
 */
import "./help-markdown";

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

vi.mock("./help-markdown", async (original) => {
  const { getConfig } = await import("@testing-library/react");
  // Twice the wait of a query: a test that paid it fails whatever the margin of the workstation.
  await new Promise((resolve) => setTimeout(resolve, 2 * getConfig().asyncUtilTimeout));
  return original<typeof import("./help-markdown")>();
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
  it("opens from the button of the header on the page of the screen, in its fixed sections, its columns from the catalogues [WF-IHM-0140-A]", async () => {
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
    // The definitions of the columns, as the tooltips of the headers say them.
    const columns = within(dialog)
      .getByRole("heading", { name: "Ses colonnes et ses valeurs calculées" })
      .closest("section");
    expect(columns).toHaveTextContent(CATALOGUES.fr.columns.planning.predecessors.help);
    expect(columns).toHaveTextContent(CATALOGUES.fr.grid.columns.totalFloat);
    expect(columns).toHaveTextContent("(valeur calculée par le serveur)");
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
    // The region of the body holds the messages of the interface too: only the page is French (#1442).
    expect(within(dialog).getByRole("region", { name: "Planification" })).not.toHaveAttribute(
      "lang",
    );
    expect(dialog.querySelectorAll('[lang="fr"]').length).toBeGreaterThan(1);
    expect(dialog.querySelector('[lang="fr"] h3')).not.toBeNull();
    await expectAccessible(dialog);
  });

  it("says the title of the list of parts in the language of the interface, its French titles French [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader("en");
    await user.click(screen.getByRole("button", { name: "Help" }));
    const dialog = await panel("Planification");
    const parts = await within(dialog).findByRole("navigation", {
      name: "The parts of the screen",
    });
    // The name of the list is the interface's own; the titles of its links are the help's (#1480).
    expect(within(parts).getByRole("heading", { level: 4 })).toHaveAttribute("lang", "en");
    const links = within(parts).getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link.closest("[lang]")).toHaveAttribute("lang", "fr");
    }
  });

  it("keeps the columns of the grid, the interface's own text, out of the French page [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader("en");
    await user.click(screen.getByRole("button", { name: "Help" }));
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    const definition = within(dialog).getByText(CATALOGUES.en.columns.planning.predecessors.help);
    expect(definition.closest("[lang]")).toHaveAttribute("lang", "en");
    expect(
      within(dialog).getAllByText("(value computed by the server)")[0]?.closest("[lang]"),
    ).toHaveAttribute("lang", "en");
    // Under lang="fr", no grid definition, status nor alert.
    for (const own of dialog.querySelectorAll("dl, [role='status'], [role='alert']")) {
      expect(own.closest("[lang]")?.getAttribute("lang")).not.toBe("fr");
    }
  });

  it("puts the body, which scrolls, in the order of the keyboard, named by the title [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    const body = within(dialog).getByRole("region", { name: "Planification" });
    expect(body).toHaveAttribute("tabindex", "0");
    // Tab goes from the title's neighbours — the close button — to the search, then to the body.
    within(dialog).getByRole("button", { name: "Fermer l’aide" }).focus();
    await user.tab();
    expect(within(dialog).getByRole("searchbox", { name: "Chercher dans l’aide" })).toHaveFocus();
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

  it("searches the titles of the pages and the notions [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    await user.type(
      within(dialog).getByRole("searchbox", { name: "Chercher dans l’aide" }),
      "acquise",
    );
    expect(within(dialog).getByRole("status")).toHaveTextContent("1 page trouvée");
    await user.click(within(dialog).getByRole("link", { name: "La valeur acquise" }));
    await panel("La valeur acquise");
  });

  it.each([
    ["fr", "Chercher dans l’aide", "Aide", "Aucune page de l’aide ne porte ces mots."],
    ["en", "Search the help", "Help", "No page of the help holds these words."],
  ] as const)(
    "says no page holds the words searched, in %s, and clears the query on a followed link [WF-IHM-0140-A]",
    async (locale, label, button, none) => {
      const user = userEvent.setup();
      renderHeader(locale);
      await user.click(screen.getByRole("button", { name: button }));
      const dialog = await panel("Planification");
      await within(dialog).findAllByRole("heading", { level: 3 });
      const box = within(dialog).getByRole("searchbox", { name: label });
      await user.type(box, "zzzz");
      expect(within(dialog).getByRole("status")).toHaveTextContent(none);
      await user.clear(box);
      await user.type(box, "acquise");
      await user.click(within(dialog).getByRole("link", { name: "La valeur acquise" }));
      await panel("La valeur acquise");
      expect(within(dialog).getByRole("searchbox", { name: label })).toHaveValue("");
    },
  );

  it("keeps the alert of a failed reading when a word is typed, with no index to search [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    vi.mocked(readHelp).mockRejectedValueOnce(new Error("out of reach"));
    renderHeader();
    await user.click(helpButton());
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByRole("alert")).toBeInTheDocument();
    await user.type(
      within(dialog).getByRole("searchbox", { name: "Chercher dans l’aide" }),
      "acquise",
    );
    expect(within(dialog).getByRole("alert")).toHaveTextContent("L’aide n’a pas pu être lue");
    expect(within(dialog).queryByText(/Aucune page/)).toBeNull();
  });

  it("keeps the language of the interface on the messages of a search and a failed reading, the French on the titles [WF-IHM-0140-A]", async () => {
    const user = userEvent.setup();
    renderHeader("en");
    await user.click(screen.getByRole("button", { name: "Help" }));
    const dialog = await panel("Planification");
    await within(dialog).findAllByRole("heading", { level: 3 });
    await user.type(within(dialog).getByRole("searchbox", { name: "Search the help" }), "acquise");
    expect(within(dialog).getByRole("status")).toHaveTextContent("1 page found");
    expect(within(dialog).getByRole("status").closest("[lang]")).toBeNull();
    expect(
      within(dialog).getByRole("link", { name: "La valeur acquise" }).closest("[lang]"),
    ).toHaveAttribute("lang", "fr");
    vi.mocked(readHelp).mockRejectedValueOnce(new Error("out of reach"));
    await user.click(within(dialog).getByRole("link", { name: "La valeur acquise" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "The help could not be read.",
    );
    expect(within(dialog).getByRole("alert").closest("[lang]")).toBeNull();
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
        columns: [],
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

  it("opens, on the page of a project, the help of the projects, FBS-4 [WF-IHM-0140-A]", async () => {
    // #1439: the page of a project, which no function of the table routes to, opens the help of
    // the block of the projects, whose page describes it.
    at.pathname = "/projects/01926f3a-7c00-7000-8000-000000000001";
    const user = userEvent.setup();
    renderHeader();
    await user.click(helpButton());
    const dialog = await panel("Projets");
    expect(readHelp).toHaveBeenCalledWith({ kind: "screen", code: "FBS-4" });
    expect(dialog).toHaveTextContent("La page d’un projet");
  });

  it.each([["/account"], ["/account/avatar"], ["/login/unavailable"]])(
    "offers no help at %s, outside the table of the functions",
    (pathname) => {
      at.pathname = pathname;
      renderHeader();
      expect(screen.queryByRole("button", { name: "Aide" })).toBeNull();
    },
  );
});

/** The button of the panel that comes back to the page of the screen. */
function helpButtonInPanel(dialog: HTMLElement) {
  return within(dialog).getByRole("button", { name: "Revenir à l’aide de l’écran" });
}
