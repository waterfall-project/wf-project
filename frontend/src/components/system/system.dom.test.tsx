// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, renderHook, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import PageError from "@/app/error";
import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { useBrowserLocale } from "./browser-locale";
import { NoProjects, NoRevisions, ReferenceIncomplete } from "./empty-states";
import {
  type BoundaryError,
  correlationDigest,
  SESSION_REQUIRED_DIGEST,
  UNREACHABLE_DIGEST,
} from "./failure";
import { ScreenSkeleton } from "./screen-skeleton";
import { SystemFailure } from "./system-failure";

type ReferenceReadiness = components["schemas"]["ReferenceReadiness"];

// The address the browser shows, as the router of Next gives it to a client component.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/projects",
  useSearchParams: () => new URLSearchParams("is_contributor=true"),
}));

/** Render in a language, as the shell hands its texts to a screen. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {children}
    </NextIntlClientProvider>,
  );
}

/** An error as Next forwards it from the server in production: a generic message, a digest. */
function forwarded(digest: string): BoundaryError {
  return Object.assign(new Error("An error occurred in the Server Components render."), {
    digest,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the screen of failure", () => {
  it("announces the API out of reach as such, and offers to try again", async () => {
    const retry = vi.fn();
    const { container } = inLanguage(
      <SystemFailure error={forwarded(UNREACHABLE_DIGEST)} retry={retry} />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(
      "Service injoignable" +
        "Le service ne répond pas : l’écran n’a pas pu lire ses données. " +
        "Réessayez dans un instant.",
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Service injoignable");
    expect(alert).not.toHaveTextContent("Référence");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(retry).toHaveBeenCalledOnce();
    await expectAccessible(container);
  });

  it("tells an unexpected error apart, with the reference that finds it in the logs", async () => {
    const { container } = inLanguage(
      <SystemFailure error={forwarded(correlationDigest("req-7f3a"))} retry={vi.fn()} />,
      "en",
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Unexpected error");
    expect(screen.getByRole("alert")).toHaveTextContent("Reference: req-7f3a");
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
    await expectAccessible(container);
  });

  it("shows the digest Next computed as the reference of an error without a correlation identifier", () => {
    inLanguage(<SystemFailure error={forwarded("2894650101")} retry={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Référence : 2894650101");
  });

  it("leads a read refused for want of a session to the sign-in page, which comes back to the screen", async () => {
    const { container } = inLanguage(
      <SystemFailure error={forwarded(SESSION_REQUIRED_DIGEST)} retry={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Session requise");
    expect(screen.getByRole("link", { name: "Se connecter" })).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent("/projects?is_contributor=true")}`,
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("Référence");
    await expectAccessible(container);
  });

  it("says an error without a reference is unexpected, and names no reference", () => {
    inLanguage(<SystemFailure error={new Error("a defect")} retry={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Erreur inattendue");
    expect(screen.getByRole("alert")).not.toHaveTextContent("Référence");
    inLanguage(<SystemFailure error={forwarded("")} retry={vi.fn()} />);
    expect(screen.getAllByRole("alert")[1]).not.toHaveTextContent("Référence");
  });

  it("is what the boundary of the pages shows in place of the page, inside the shell", async () => {
    const retry = vi.fn();
    inLanguage(<PageError error={forwarded(UNREACHABLE_DIGEST)} retry={retry} />);
    expect(screen.getByRole("main")).toHaveTextContent("Service injoignable");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});

describe("the language of the screen of failure of the root layout", () => {
  it("is the first offered language the browser asks for", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE", "en-GB", "fr"]);
    expect(renderHook(() => useBrowserLocale()).result.current).toBe("en");
  });

  it("is the language of the reference catalogue when the browser asks for none offered", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE"]);
    expect(renderHook(() => useBrowserLocale()).result.current).toBe("fr");
  });
});

describe("the skeleton of a screen that loads", () => {
  it("shows the page region busy, and names it, its shapes hidden from a screen reader", async () => {
    const { container } = inLanguage(<ScreenSkeleton />);
    const main = screen.getByRole("main", { name: "Chargement de l’écran" });
    expect(main).toHaveAttribute("aria-busy", "true");
    // aria-busy alone says nothing: a status, hidden from the eye, announces the loading.
    const status = screen.getByRole("status", { name: "Chargement de l’écran" });
    expect(status).toHaveTextContent("Chargement de l’écran");
    expect(status).toHaveClass("sr-only");
    expect(main.lastElementChild).toHaveAttribute("aria-hidden", "true");
    expect(main.querySelectorAll("div > div")).toHaveLength(5);
    await expectAccessible(container);
  });

  it.each([
    ["the functions still to come", () => import("@/app/[...path]/loading")],
    ["the list of projects", () => import("@/app/projects/loading")],
    ["a project", () => import("@/app/projects/[projectId]/loading")],
    ["a revision", () => import("@/app/projects/[projectId]/revisions/[revisionId]/loading")],
  ])("is what %s show while they load", async (_, page) => {
    const { default: Loading } = await page();
    inLanguage(<Loading />, "en");
    expect(screen.getByRole("main", { name: "Loading the screen" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });
});

describe("the empty states", () => {
  it("say there is no project, with nothing to lift when the list was not filtered", async () => {
    const { container } = inLanguage(<NoProjects unfiltered={undefined} />);
    expect(container).toHaveTextContent("Aucun projet.");
    expect(screen.queryByRole("link")).toBeNull();
    await expectAccessible(container);
  });

  it("lift the contributor filter that emptied the list", async () => {
    const { container } = inLanguage(<NoProjects unfiltered="/projects" />);
    expect(container).toHaveTextContent("Vous n’êtes contributeur d’aucun projet.");
    expect(screen.getByRole("link", { name: "Voir tous les projets" })).toHaveAttribute(
      "href",
      "/projects",
    );
    await expectAccessible(container);
  });

  it("say a project has no revision yet, even without an address to lead to", async () => {
    const { container } = inLanguage(<NoRevisions revisions={undefined} />);
    expect(container).toHaveTextContent("Ce projet n’a encore aucune révision.");
    expect(screen.queryByRole("link")).toBeNull();
    await expectAccessible(container);
  });

  it("name what an incomplete reference lacks under a heading, each leading to its function", async () => {
    const readiness = example("reference_readiness_incomplete") as ReferenceReadiness;
    const { permissions } = example("session") as components["schemas"]["Session"];
    const { container } = inLanguage(
      <ReferenceIncomplete readiness={readiness} permissions={permissions} />,
    );
    const section = screen.getByRole("region", { name: "Référentiel incomplet" });
    expect(section).toHaveTextContent(
      /^Référentiel incompletAucun projet ne peut être créé tant que le référentiel commun n’a pas :/,
    );
    expect(
      screen
        .getAllByRole("listitem")
        .map((item) => [item.textContent, item.querySelector("a")?.getAttribute("href")]),
    ).toEqual([
      ["un calendrier par défaut pourvu d’heures travaillées", "/reference/resources"],
      ["une catégorie de coût active", "/reference/costs"],
    ]);
    await expectAccessible(container);
  });

  it("say nothing of a complete reference", () => {
    const readiness = example("reference_readiness") as ReferenceReadiness;
    const { container } = inLanguage(
      <ReferenceIncomplete readiness={readiness} permissions={[]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
