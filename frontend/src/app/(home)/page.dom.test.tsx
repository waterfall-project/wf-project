// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, rendered in a document (US-2130): a screen of consultation in the airy column, its title
 * at the size of the airy ones, no command beside it; the list of the projects in its card, « Créer
 * un projet » the one filled command of the card, at the right of its title (#3264), as the rule of
 * the commands wants it (`expectCommandRule`).
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SCREEN } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectCommandRule } from "@/test/command-rule";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import HomePage from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: () => fakeClient(server.answers) }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

/** The classes only the filled variant of a button carries: the primary background. */
const FILLED = "bg-primary";

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
  server.answers = {
    "GET /me": "me",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
  };
});

/** Render the home at an address, in English. */
async function renderHome(search: Record<string, string> = {}) {
  const page = await HomePage({ searchParams: Promise.resolve(search) });
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {page}
    </NextIntlClientProvider>,
  );
}

describe("the home, rendered", () => {
  it("sets the list in its card, « Create a project » filled at the right of its title, the one filled command of the screen (US-2130, #3264)", async () => {
    const { container } = await renderHome();
    expect(screen.getByRole("main")).toHaveClass(...SCREEN.airy.split(" "));
    const card = screen.getByRole("region", { name: "List of projects" });
    expect(within(card).getByRole("heading", { level: 2 })).toHaveTextContent("List of projects");
    const create = within(card).getByRole("button", { name: "Create a project" });
    expect(create).toHaveClass(...buttonVariants({ variant: "default", size: "sm" }).split(" "));
    expect(create.closest('[data-slot="section-card-principal"]')).toHaveAttribute(
      "data-does",
      "create",
    );
    expect(within(card).getByRole("grid", { name: "List of projects" })).toBeInTheDocument();
    // Nothing beside the title of the screen: the filter of the contributor is a chip of the table.
    expect(container.querySelector('[data-slot="screen-commands"]')).toBeNull();
    expect(container.querySelectorAll(`button.${FILLED}, a.${FILLED}`)).toHaveLength(1);
    expectCommandRule(container);
  });

  it("keeps « Create a project » filled in its card while the reference is incomplete, unavailable and saying why (US-2130)", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const { container } = await renderHome();
    const create = within(screen.getByRole("region", { name: "List of projects" })).getByRole(
      "button",
      { name: "Create a project" },
    );
    expect(create).toHaveAttribute("aria-disabled", "true");
    expect(create).toHaveAccessibleDescription("The minimum reference data is incomplete.");
    expect(create).toHaveClass(FILLED);
    expectCommandRule(container);
  });

  it("titles the screen at the size of the airy screens (US-2130)", async () => {
    await renderHome();
    expect(screen.getByRole("heading", { level: 1 }).parentElement).toHaveClass("text-2xl");
  });
});
