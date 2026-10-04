// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { SidebarProvider } from "@/components/ui/sidebar";
import { CATALOGUES } from "@/i18n/catalogues";
import { LAST_CONTEXT_COOKIE } from "@/navigation/context";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { Navigation } from "./navigation";

// The address the browser shows, as the router of Next gives it to a client component.
const address = vi.hoisted(() => ({ pathname: "/", search: new URLSearchParams() }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => address.pathname,
  useSearchParams: () => address.search,
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const IN_PROJECT = `/projects/${PROJECT}/revisions/${REVISION}`;
const CONTEXT = `?subproject_id=${SUBPROJECT}&as_of=2026-05-31`;

/** The permissions of a session of the contract. */
function permissions(name: string) {
  return (example(name) as components["schemas"]["Session"]).permissions;
}

/** Show an address, as a navigation of the browser would. */
function visit(pathname: string, search = "") {
  address.pathname = pathname;
  address.search = new URLSearchParams(search);
}

/** Render the navigation, in French, for a session and the cookie of the request. */
function navigation(session = "session", remembered?: string) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      <SidebarProvider>
        <Navigation permissions={permissions(session)} remembered={remembered} theme="default" />
      </SidebarProvider>
    </NextIntlClientProvider>
  );
}

/** Open every block of the FBS the navigation shows closed, and give back their names. */
async function openBlocks(): Promise<string[]> {
  const nav = screen.getByRole("navigation", { name: "Fonctions" });
  const closed = within(nav)
    .queryAllByRole("button")
    .filter((button) => button.getAttribute("aria-expanded") === "false");
  for (const block of closed) {
    await userEvent.click(block);
  }
  return closed.map((block) => block.textContent);
}

/** The address a link of the navigation leads to, found by its name. */
function href(name: string): string | null {
  return screen.getByRole("link", { name }).getAttribute("href");
}

beforeEach(() => {
  visit("/");
  document.cookie = `${LAST_CONTEXT_COOKIE}=; path=/; max-age=0`;
});

describe("the navigation", () => {
  it("leads a user who opened no project to the portfolio, the reference, the administration and the status screen [WF-IHM-0010-A]", async () => {
    const { container } = render(navigation());

    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    expect(await openBlocks()).toEqual([
      "Administration",
      "Portefeuille",
      "Paramètres applicatifs",
    ]);
    expect(href("Portefeuille de projets")).toBe("/portfolio/projects");
    expect(href("Paramètres de coûts")).toBe("/reference/costs");
    expect(href("Gestion des utilisateurs")).toBe("/admin/users");
    expect(href("Surveillance de l’état du système")).toBe("/system");
    // No project is open: its functions wait for one, and there is none to go back to.
    expect(within(nav).queryByRole("link", { name: "Planification" })).toBeNull();
    expect(within(nav).queryByRole("link", { name: "Retour au projet" })).toBeNull();
    expect(href("Projets")).toBe("/");
    await expectAccessible(container);
  });

  it("still leads to the status screen, alone, when the session cannot be read", async () => {
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <SidebarProvider>
          <Navigation permissions="unreadable" remembered={undefined} theme={undefined} />
        </SidebarProvider>
      </NextIntlClientProvider>,
    );
    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    // Its block is open from the start: there is nothing else to look for.
    expect(await openBlocks()).toEqual([]);
    expect(
      within(nav)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual(["/system"]);
    expect(href("Surveillance de l’état du système")).toBe("/system");
    await expectAccessible(container);
  });

  it("groups the functions by where they live, the blocks of the FBS closed on theirs, and offers each function the session may read", async () => {
    render(navigation());
    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    const headings = within(nav)
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    // No project is open: the functions of a revision wait for one, and so does their group.
    expect(headings).toEqual(["Plateforme", "Projet"]);
    // No page of a block is shown: each is closed, and the list of projects alone is a link.
    expect(
      within(nav)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Projets"]);
    await openBlocks();
    expect(within(nav).getAllByRole("link")).toHaveLength(4 + 7 + 4 + 1);
    for (const block of ["Administration", "Portefeuille", "Paramètres applicatifs"]) {
      expect(within(nav).getByRole("button", { name: block })).toHaveAttribute(
        "aria-expanded",
        "true",
      );
    }
  });

  it("opens the block of the page shown, and closes it at the user's wish", async () => {
    visit("/reference/risks");
    render(navigation());
    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    const block = within(nav).getByRole("button", { name: "Paramètres applicatifs" });
    expect(block).toHaveAttribute("aria-expanded", "true");
    expect(within(nav).getByRole("link", { name: "Paramètres de risques" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("button", { name: "Portefeuille" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    await userEvent.click(block);
    expect(block).toHaveAttribute("aria-expanded", "false");
    expect(within(nav).queryByRole("link", { name: "Paramètres de risques" })).toBeNull();
  });

  it("gives every entry an icon, hidden from a screen reader beside the name it keeps", async () => {
    visit(`${IN_PROJECT}/remaining`);
    render(navigation());
    await openBlocks();
    const nav = screen.getByRole("navigation", { name: "Fonctions" });
    const headings = within(nav)
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(headings).toEqual(["Plateforme", "Projet", "Révision en cours"]);
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(15 + 1 + 3 + 6);
    for (const link of [...links, ...within(nav).getAllByRole("button")]) {
      expect(link.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
      expect(link.textContent).not.toBe("");
    }
  });

  it("offers no function whose read permission the session lacks", async () => {
    render(navigation("session_without_administration"));
    expect(await openBlocks()).toEqual(["Portefeuille", "Paramètres applicatifs"]);
    expect(screen.queryByRole("link", { name: "Surveillance de l’état du système" })).toBeNull();
    expect(screen.getByRole("link", { name: "Portefeuille de projets" })).toBeInTheDocument();
  });

  it("carries the revision, the sub-project and the calculation date from one function of a project to the others", async () => {
    visit(`${IN_PROJECT}/remaining`, `${CONTEXT}&sort_by=label`);
    const { container } = render(navigation());
    await openBlocks();

    expect(href("Gestion des risques")).toBe(`${IN_PROJECT}/risks${CONTEXT}`);
    expect(href("Indicateurs projets")).toBe(`${IN_PROJECT}/indicators${CONTEXT}`);
    const current = screen.getByRole("link", { name: "Estimation du reste à engager" });
    expect(current).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Planification" })).not.toHaveAttribute("aria-current");
    // A function outside the project leaves the context behind.
    expect(href("Portefeuille de projets")).toBe("/portfolio/projects");
    await expectAccessible(container);
  });

  it("marks current the function whose leaf the page shows, which the bar does not offer", async () => {
    visit(`${IN_PROJECT}/workload`, CONTEXT);
    render(navigation());
    await openBlocks();
    expect(screen.queryByRole("link", { name: "Plan de charge" })).toBeNull();
    const estimate = screen.getByRole("link", { name: "Chiffrage et devis" });
    expect(estimate).toHaveAttribute("aria-current", "true");
    expect(estimate).toHaveAttribute("href", `${IN_PROJECT}/estimate${CONTEXT}`);
    expect(screen.getByRole("link", { name: "Planification" })).not.toHaveAttribute("aria-current");
  });

  it("leads back from a function outside any project to the same project context [WF-IHM-0010-A]", () => {
    visit(`${IN_PROJECT}/remaining`, CONTEXT);
    const view = render(navigation());
    expect(screen.queryByRole("link", { name: "Retour au projet" })).toBeNull();

    visit("/portfolio/projects");
    view.rerender(navigation());

    expect(href("Retour au projet")).toBe(`${IN_PROJECT}/remaining${CONTEXT}`);
    expect(screen.getByRole("link", { name: "Portefeuille de projets" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("link", { name: "Planification" })).toBeNull();
  });

  it("keeps the last project context in a cookie, for the next visit", () => {
    visit(`${IN_PROJECT}/risks`, CONTEXT);
    render(navigation());
    expect(document.cookie).toBe(
      `${LAST_CONTEXT_COOKIE}=${encodeURIComponent(`${IN_PROJECT}/risks${CONTEXT}`)}`,
    );
  });

  it("leads back to the project context the cookie of the request kept [WF-IHM-0010-A]", () => {
    visit("/system");
    render(navigation("session", `${IN_PROJECT}/risks${CONTEXT}`));
    expect(href("Retour au projet")).toBe(`${IN_PROJECT}/risks${CONTEXT}`);
    expect(screen.getByRole("link", { name: "Projets" })).not.toHaveAttribute("aria-current");
  });

  it("offers the functions of the project itself to a project without a revision", async () => {
    visit(`/projects/${PROJECT}`);
    const { container } = render(navigation());
    expect(href("Gestion des révisions")).toBe(`/projects/${PROJECT}/revisions`);
    expect(href("Paramètres de projets")).toBe(`/projects/${PROJECT}/settings`);
    expect(href("Cycle de vie du projet")).toBe(`/projects/${PROJECT}/lifecycle`);
    // The functions of a revision wait for one.
    expect(screen.queryByRole("link", { name: "Planification" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Retour au projet" })).toBeNull();
    await expectAccessible(container);
  });

  it("keeps the revision on a function of the project itself, for the next function of a revision", () => {
    visit(`/projects/${PROJECT}/lifecycle`, `?revision_id=${REVISION}&as_of=2026-05-31`);
    render(navigation());
    expect(screen.getByRole("link", { name: "Cycle de vie du projet" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(href("Planification")).toBe(`${IN_PROJECT}/planning?as_of=2026-05-31`);
    expect(href("Gestion des révisions")).toBe(
      `/projects/${PROJECT}/revisions?revision_id=${REVISION}&as_of=2026-05-31`,
    );
    expect(document.cookie).toContain(
      encodeURIComponent(`/projects/${PROJECT}/lifecycle?revision_id=${REVISION}&as_of=2026-05-31`),
    );
  });

  it("marks the list of projects, the home, as the page shown", () => {
    visit("/");
    render(navigation());
    expect(screen.getByRole("link", { name: "Projets" })).toHaveAttribute("aria-current", "page");
  });
});
