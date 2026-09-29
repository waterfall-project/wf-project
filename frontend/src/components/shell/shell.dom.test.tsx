// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { SIDEBAR_COOKIE } from "@/components/ui/sidebar-state";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { Shell, type ShellProps } from "./shell";
import { ShowProject } from "./shown-project";

// The address the browser shows, as the router of Next gives it to a client component.
const address = vi.hoisted(() => ({ pathname: "/", search: new URLSearchParams() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => address.pathname,
  useSearchParams: () => address.search,
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const { user, permissions } = example("session") as components["schemas"]["Session"];
const project = example("project") as components["schemas"]["Project"];

/** Render a page in the shell, in French, for the account and the session of the contract. */
function shell(props: Partial<ShellProps> = {}, page = <main />) {
  return render(
    <Shell
      locale="fr"
      account={user}
      preference="default"
      theme="default"
      permissions={permissions}
      remembered={undefined}
      sidebarOpen
      {...props}
    >
      {page}
    </Shell>,
  );
}

/** The bar of the shell. */
function bar() {
  return within(screen.getByRole("banner"));
}

/** Show an address, as a navigation of the browser would. */
function visit(pathname: string, search = "") {
  address.pathname = pathname;
  address.search = new URLSearchParams(search);
}

/** Make the window a narrow screen: every query of its width answers that it is one. */
function narrow() {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query) =>
      ({
        matches: true,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

beforeEach(() => {
  visit("/");
  document.cookie = `${SIDEBAR_COOKIE}=; path=/; max-age=0`;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the shell", () => {
  it.each([
    ["fr", "Replier la barre latérale", "Rechercher", "Compte de Camille Martin"],
    ["en", "Collapse the side bar", "Search", "Account of Camille Martin"],
  ] as const)(
    "sets the side bar beside the bar of the page, which folds it, shows where the page sits, searches, follows the tasks and opens the account, in %s",
    async (locale, fold, search, account) => {
      const { container } = shell({ locale });
      expect(bar().getByRole("button", { name: fold })).toHaveAttribute("aria-expanded", "true");
      expect(bar().getByRole("navigation")).toHaveTextContent(locale === "fr" ? "Accueil" : "Home");
      expect(bar().getByRole("searchbox", { name: search })).toBeInTheDocument();
      expect(
        bar().getByRole("button", { name: /^(Tâches de fond|Background tasks)$/ }),
      ).toHaveAttribute("aria-expanded", "false");
      expect(bar().getByRole("button", { name: account })).toHaveAttribute("aria-haspopup", "menu");
      expect(
        screen.getByRole("navigation", { name: /^(Fonctions|Functions)$/ }),
      ).toBeInTheDocument();
      await expectAccessible(container);
    },
  );

  it("gives every button of the bar an icon, hidden from a screen reader", () => {
    shell();
    for (const button of bar().getAllByRole("button")) {
      expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("folds the side bar into a rail of icons, whose entries keep their names and show them in a tooltip, and keeps it folded", async () => {
    shell();
    const fold = bar().getByRole("button", { name: "Replier la barre latérale" });
    await userEvent.click(fold);

    expect(fold).toHaveAccessibleName("Déplier la barre latérale");
    expect(fold).toHaveAttribute("aria-expanded", "false");
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute(
      "data-state",
      "collapsed",
    );
    expect(document.cookie).toContain(`${SIDEBAR_COOKIE}=false`);
    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    const link = within(nav).getByRole("link", { name: "Projets" });
    act(() => {
      link.focus();
    });
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Projets");
    await userEvent.keyboard("{Escape}");

    // A block of the FBS, pressed in the rail, unfolds the bar on its functions.
    await userEvent.click(within(nav).getByRole("button", { name: "Portefeuille" }));
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute("data-state", "expanded");
    expect(within(nav).getByRole("link", { name: "Portefeuille de projets" })).toBeInTheDocument();
    await userEvent.click(bar().getByRole("button", { name: "Replier la barre latérale" }));

    // The foot of the bar unfolds it again, as the button of the bar of the page does.
    const [, foot] = screen.getAllByRole("button", { name: "Déplier la barre latérale" });
    await userEvent.click(foot ?? fold);
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute("data-state", "expanded");
    expect(document.cookie).toContain(`${SIDEBAR_COOKIE}=true`);
  });

  it("starts folded when the user left it folded, and folds or unfolds with Ctrl+B", async () => {
    shell({ sidebarOpen: false });
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute(
      "data-state",
      "collapsed",
    );
    await userEvent.keyboard("{Control>}b{/Control}");
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute("data-state", "expanded");
    await userEvent.keyboard("{Meta>}b{/Meta}");
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute(
      "data-state",
      "collapsed",
    );
    await userEvent.keyboard("b");
    expect(document.querySelector("[data-slot=sidebar]")).toHaveAttribute(
      "data-state",
      "collapsed",
    );
  });

  it("slides the side bar over the page on a narrow screen, a dialog named for it", async () => {
    narrow();
    shell();
    expect(screen.queryByRole("navigation", { name: "Fonctions" })).toBeNull();
    const open = bar().getByRole("button", { name: "Déplier la barre latérale" });

    await userEvent.click(open);

    const sheet = await screen.findByRole("dialog", { name: "Barre latérale" });
    expect(within(sheet).getByRole("navigation", { name: "Fonctions" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
  });

  it("opens the menu of the account on its name and address, its preferences, its pages, and a way out still to come", async () => {
    shell();
    await userEvent.click(bar().getByRole("button", { name: "Compte de Camille Martin" }));
    const menu = screen.getByRole("menu");
    expect(menu).toHaveTextContent("Camille Martin");
    expect(menu).toHaveTextContent("camille.martin@example.com");
    expect(within(menu).getByRole("menuitem", { name: /^Langue/ })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /^Mode d’affichage/ })).toBeInTheDocument();
    const pages = ["Mon compte", "Changer le mot de passe", "Changer l’avatar"].map((name) =>
      within(menu).getByRole("menuitem", { name }).getAttribute("href"),
    );
    expect(pages).toEqual(["/account", "/account/password", "/account/avatar"]);
    expect(within(menu).getByRole("menuitem", { name: "Se déconnecter" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    for (const item of within(menu).getAllByRole("menuitem")) {
      expect(item.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    }
    await expectAccessible(menu);
  });

  it("offers no preference in the menu of an account whose preferences it was not given", async () => {
    shell({ preference: undefined, theme: undefined });
    await userEvent.click(bar().getByRole("button", { name: "Compte de Camille Martin" }));
    const menu = screen.getByRole("menu");
    expect(menu).not.toHaveTextContent("Préférences");
    expect(within(menu).queryByRole("menuitem", { name: /^Langue/ })).toBeNull();
    expect(within(menu).getByRole("menuitem", { name: "Mon compte" })).toBeInTheDocument();
  });

  it("holds the pieces of the side bar within its provider only", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<SidebarTrigger />)).toThrow(
      "a piece of the side bar is rendered within a SidebarProvider only",
    );
  });

  it("offers neither the menu of the account nor the side bar without an account: the logo leads home", () => {
    shell({ account: undefined, preference: undefined, theme: undefined, permissions: undefined });
    expect(bar().queryByRole("button", { name: /^Compte de/ })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Fonctions" })).toBeNull();
    expect(bar().queryByRole("button", { name: /barre latérale/ })).toBeNull();
    expect(bar().getByRole("link", { name: "Waterfall" })).toHaveAttribute("href", "/");
  });

  it("says no project is open outside any project, and leads to the list of projects", async () => {
    visit("/portfolio/projects");
    shell();
    expect(bar().getByRole("navigation", { name: "Fil d’Ariane" })).toHaveTextContent(
      "PortefeuillePortefeuille de projets",
    );
    await userEvent.click(screen.getByRole("button", { name: "Aucun projet ouvert" }));
    const menu = screen.getByRole("menu");
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((item) => item.getAttribute("href")),
    ).toEqual(["/projects"]);
  });

  it("names the project its screen hands on, in the side bar and in the breadcrumb", async () => {
    visit(`/projects/${PROJECT}/revisions/${REVISION}/risks`, "as_of=2026-05-31");
    shell(
      {},
      <main>
        <ShowProject project={project} />
      </main>,
    );
    const choice = await screen.findByRole("button", {
      name: "Modernisation du poste de commande PRJ-001 · En cours",
    });
    const crumbs = bar().getByRole("navigation", { name: "Fil d’Ariane" });
    expect(within(crumbs).getByRole("link", { name: "Projets" })).toHaveAttribute(
      "href",
      "/projects",
    );
    expect(
      within(crumbs).getByRole("link", { name: "Modernisation du poste de commande" }),
    ).toHaveAttribute("href", `/projects/${PROJECT}?revision_id=${REVISION}&as_of=2026-05-31`);
    expect(within(crumbs).getByText("Gestion des risques")).toHaveAttribute("aria-current", "page");

    await userEvent.click(choice);
    expect(
      within(screen.getByRole("menu"))
        .getAllByRole("menuitem")
        .map((item) => item.getAttribute("href")),
    ).toEqual(["/projects", `/projects/${PROJECT}?revision_id=${REVISION}&as_of=2026-05-31`]);
  });

  it("says a project is open without naming it while its screen has not handed it on", () => {
    visit(`/projects/${PROJECT}/lifecycle`);
    shell();
    expect(screen.getByRole("button", { name: "Projet ouvert" })).toBeInTheDocument();
    expect(bar().getByRole("link", { name: "Projet ouvert" })).toHaveAttribute(
      "href",
      `/projects/${PROJECT}`,
    );
  });
});
