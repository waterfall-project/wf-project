// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
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
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000401";
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
      <Navigation permissions={permissions(session)} remembered={remembered} />
    </NextIntlClientProvider>
  );
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
    expect(href("Portefeuille de projets")).toBe("/portfolio/projects");
    expect(href("Paramètres de coûts")).toBe("/reference/costs");
    expect(href("Gestion des utilisateurs")).toBe("/admin/users");
    expect(href("Surveillance de l’état du système")).toBe("/system");
    // No project is open: its functions wait for one, and there is none to go back to.
    expect(within(nav).queryByRole("link", { name: "Planification" })).toBeNull();
    expect(within(nav).queryByRole("link", { name: "Retour au projet" })).toBeNull();
    expect(href("Projets")).toBe("/projects");
    await expectAccessible(container);
  });

  it("names the blocks of the FBS, and offers each function the session may read", () => {
    render(navigation());
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "Administration",
      "Portefeuille",
      "Paramètres applicatifs",
      "Projets",
    ]);
    expect(screen.getAllByRole("link")).toHaveLength(4 + 7 + 4 + 1);
  });

  it("offers no function whose read permission the session lacks", () => {
    render(navigation("session_project_manager"));
    expect(screen.queryByRole("heading", { name: "Administration" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Surveillance de l’état du système" })).toBeNull();
    expect(screen.getByRole("link", { name: "Portefeuille de projets" })).toBeInTheDocument();
  });

  it("carries the revision, the sub-project and the calculation date from one function of a project to the others", async () => {
    visit(`${IN_PROJECT}/remaining`, `${CONTEXT}&sort_by=label`);
    const { container } = render(navigation());

    expect(href("Gestion des risques")).toBe(`${IN_PROJECT}/risks${CONTEXT}`);
    expect(href("Indicateurs projets")).toBe(`${IN_PROJECT}/indicators${CONTEXT}`);
    const current = screen.getByRole("link", { name: "Estimation du reste à engager" });
    expect(current).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Planification" })).not.toHaveAttribute("aria-current");
    // A function outside the project leaves the context behind.
    expect(href("Portefeuille de projets")).toBe("/portfolio/projects");
    await expectAccessible(container);
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

  it("offers no function of a project without a revision to read in", () => {
    visit(`/projects/${PROJECT}`);
    render(navigation());
    expect(screen.queryByRole("link", { name: "Planification" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Retour au projet" })).toBeNull();
    expect(screen.getByRole("link", { name: "Projets" })).toBeInTheDocument();
  });

  it("marks the list of projects as the page shown", () => {
    visit("/projects");
    render(navigation());
    expect(screen.getByRole("link", { name: "Projets" })).toHaveAttribute("aria-current", "page");
  });
});
