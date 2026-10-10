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
  failureOf,
  SESSION_REQUIRED_DIGEST,
  UNREACHABLE_DIGEST,
} from "./failure";
import { ScreenSkeleton } from "./screen-skeleton";
import { SCREEN } from "@/components/shell/page-header";
import { SystemFailure } from "./system-failure";

type ReferenceReadiness = components["schemas"]["ReferenceReadiness"];

// The address the browser shows, as the router of Next gives it to a client component.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  usePathname: () => "/portfolio/projects",
  useSearchParams: () => new URLSearchParams("as_of=2026-05-31"),
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
      `/login?next=${encodeURIComponent("/portfolio/projects?as_of=2026-05-31")}`,
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("Référence");
    await expectAccessible(container);
  });

  it("names no reference for an empty correlation identifier", () => {
    expect(failureOf(forwarded(correlationDigest("")))).toEqual({
      kind: "unexpected",
      reference: undefined,
    });
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
  it("names the page region for the loading, its shapes hidden and busy", async () => {
    const { container } = inLanguage(<ScreenSkeleton />);
    const main = screen.getByRole("main", { name: "Chargement de l’écran" });
    // A status, hidden from the eye, says the screen loads — outside any busy region, which
    // may hold back what it contains; only the hidden shapes are busy.
    const status = screen.getByRole("status", { name: "Chargement de l’écran" });
    expect(status).toHaveTextContent("Chargement de l’écran");
    expect(status).toHaveClass("sr-only");
    expect(status.closest('[aria-busy="true"]')).toBeNull();
    expect(main.lastElementChild).toHaveAttribute("aria-hidden", "true");
    expect(main.lastElementChild).toHaveAttribute("aria-busy", "true");
    expect(main.querySelectorAll("div > div")).toHaveLength(5);
    // The template of a dense screen, which the page takes in its place: nothing jumps.
    expect(main).toHaveAttribute("class", SCREEN.dense);
    await expectAccessible(container);
  });

  it.each([
    ["an address no screen answers", () => import("@/app/[...path]/loading")],
    ["the home, the list of projects", () => import("@/app/(home)/loading")],
    ["a project", () => import("@/app/projects/[projectId]/loading")],
    ["a revision", () => import("@/app/projects/[projectId]/revisions/[revisionId]/loading")],
  ])("is what %s show while they load", async (_, page) => {
    const { default: Loading } = await page();
    inLanguage(<Loading />, "en");
    expect(screen.getByRole("main", { name: "Loading the screen" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Loading the screen" })).toBeInTheDocument();
  });
});

describe("the empty states", () => {
  it("say there is no project when the list was not filtered", async () => {
    const { container } = inLanguage(<NoProjects filtered={false} />);
    expect(container).toHaveTextContent("Aucun projet.");
    expect(screen.queryByRole("link")).toBeNull();
    await expectAccessible(container);
  });

  it("say the user contributes to no project when the filter emptied the list, leaving its lifting to the filter itself", async () => {
    const { container } = inLanguage(<NoProjects filtered />);
    expect(container).toHaveTextContent("Vous n’êtes contributeur d’aucun projet.");
    expect(screen.queryByRole("link")).toBeNull();
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
      ["une catégorie de main-d’œuvre active", "/reference/costs"],
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
