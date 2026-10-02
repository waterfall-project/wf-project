// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient } from "@/api/client";
import { serverClient } from "@/api/server";
import { UNREACHABLE_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, fakeClient } from "@/test/fixtures";

import ScreenPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers } => ({ answers: {} }));

vi.mock("@/api/server", () => ({ serverClient: vi.fn(() => fakeClient(server.answers)) }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

/** The parameters of the page for an address, its search parameters included. */
function at(address: string) {
  const [pathname = "", query = ""] = address.split("?");
  return {
    params: Promise.resolve({ path: pathname.split("/").slice(1) }),
    searchParams: Promise.resolve(Object.fromEntries(new URLSearchParams(query))),
  };
}

/** Render a page in French, as the shell hands it its texts. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const BANNER = '<section aria-label="Contexte de lecture"';

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** What the heading of a page says, its icon left out. */
function heading(markup: string): string | undefined {
  const found = /<h1[^>]*>(.*?)<\/h1>/.exec(markup)?.[1];
  return found === undefined ? undefined : text(found);
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/href="([^"]*)"/g)].map(
    (match) => match[1]?.replaceAll("&amp;", "&") ?? "",
  );
}

const ANSWERS: FakeAnswers = {
  "GET /session": "session",
  "GET /projects/{project_id}": "project",
  "GET /projects/{project_id}/revisions/{revision_id}": "revision",
};

beforeEach(() => {
  server.answers = ANSWERS;
});

/** A client of an API out of reach: every call fails as `fetch` does. */
function unreachable() {
  return createApiClient({
    address: "http://unreachable.invalid",
    fetch: () => Promise.reject(new TypeError("fetch failed")),
  });
}

describe("the page of a function still to come", () => {
  it.each([
    ["/portfolio/projects", "Portefeuille de projets"],
    ["/reference/costs", "Paramètres de coûts"],
    ["/admin/users", "Gestion des utilisateurs"],
    ["/system", "Surveillance de l’état du système"],
  ])(
    "exists at %s without any project open, and names its function [WF-IHM-0010-A]",
    async (address, name) => {
      const page = html(await ScreenPage(at(address)));
      expect(page.startsWith("<main")).toBe(true);
      expect(heading(page)).toBe(name);
      expect(text(page)).toBe(`${name} Cet écran est à venir.`);
      // The heading bears the icon of the function, which a screen reader leaves out.
      expect(page).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"/);
      expect((await generateMetadata(at(address))).title).toBe(`${name} — Waterfall`);
    },
  );

  it("exists in the revision of a project, whose tab names the function and the project", async () => {
    const address = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
    expect(heading(html(await ScreenPage(at(address))))).toBe("Estimation du reste à engager");
    expect((await generateMetadata(at(address))).title).toBe(
      "Estimation du reste à engager · Modernisation du poste de commande — Waterfall",
    );
  });

  it("names the function alone when the project cannot be read", async () => {
    server.answers = { ...ANSWERS, "GET /projects/{project_id}": NOT_FOUND };
    const address = `/projects/${PROJECT}/revisions/${REVISION}/risks`;
    expect((await generateMetadata(at(address))).title).toBe("Gestion des risques — Waterfall");
  });

  it.each([
    ["project", "GET /projects/{project_id}", `/projects/${PROJECT}/revisions/${REVISION}/risks`],
    [
      "revision",
      "GET /projects/{project_id}/revisions/{revision_id}",
      `/projects/${PROJECT}/revisions/${REVISION}/risks`,
    ],
  ] as const)("is not found when the API finds no %s, at %s for %s", async (_, route, address) => {
    server.answers = { ...ANSWERS, [route]: NOT_FOUND };
    await expect(ScreenPage(at(address))).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("leads an address that leads nowhere and a project the user may not read to the same screen", async () => {
    // The API answers a project the user may not read as one it does not find: the page
    // cannot tell them apart, and throws the same verdict for both, which Next renders by
    // the one screen not found — telling them apart would reveal the project exists.
    server.answers = { ...ANSWERS, "GET /projects/{project_id}": NOT_FOUND };
    const nowhere = await ScreenPage(at("/admin/nobody")).catch((error: unknown) => error);
    const refused = await ScreenPage(at(REMAINING)).catch((error: unknown) => error);
    expect(nowhere).toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(refused).toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(String(refused)).toBe(String(nowhere));
  });

  it("is not found at an address that leads to no function", async () => {
    await expect(ScreenPage(at("/admin/nobody"))).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    expect(await generateMetadata(at("/admin/nobody"))).toEqual({});
  });
});

describe("the banner of the reading context of a screen of a project", () => {
  it("names the project and the revision shown, on a screen of a revision [WF-IHM-0020-A]", async () => {
    // Chaque écran de données de projet nomme le projet et la révision affichée.
    const page = html(await ScreenPage(at(REMAINING)));
    expect(page.startsWith(BANNER)).toBe(true);
    expect(text(page)).toContain(
      "Projet Modernisation du poste de commande Révision Révision en cours En cours d’élaboration",
    );
    expect(text(page)).not.toContain("Lecture seule");
  });

  it("presents a marked revision as such, and that it is read only [WF-IHM-0020-A]", async () => {
    // L'ouverture d'une révision marquée présente cet état — la seconde moitié de la phrase,
    // aucune commande de modification proposée, est prouvée avec les commandes (US-0170/L1).
    server.answers = {
      ...ANSWERS,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
    };
    const page = html(await ScreenPage(at(REMAINING)));
    expect(text(page)).toContain(
      "Révision Référence Marquée Révision de référence " +
        "Lecture seule : aucune saisie n’est proposée sur cette révision.",
    );
  });

  it("shows the active filters as chips, each lifted by a link that keeps the rest [WF-IHM-0020-A]", async () => {
    // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres.
    server.answers = { ...ANSWERS, "GET /projects/{project_id}/subprojects": "subprojects" };
    const page = html(
      await ScreenPage(at(`${REMAINING}?subproject_id=${SUBPROJECT}&as_of=2026-05-31&q=x`)),
    );
    expect(text(page)).toContain(
      "Sous-projet : SP-CMD — Poste de commande Date de calcul : 31 mai 2026",
    );
    expect(page).toContain(
      'aria-label="Lever le filtre «\u00a0Date de calcul\u00a0: 31 mai 2026\u00a0»"',
    );
    expect(links(page)).toEqual([
      `${REMAINING}?as_of=2026-05-31`,
      `${REMAINING}?subproject_id=${SUBPROJECT}`,
    ]);
  });

  it("shows no banner outside any project", async () => {
    expect(html(await ScreenPage(at("/system?as_of=2026-05-31")))).not.toContain(BANNER);
  });

  it("leaves the screen of failure to announce the API out of reach, rather than a screen without its banner", async () => {
    vi.mocked(serverClient).mockReturnValueOnce(unreachable()).mockReturnValueOnce(unreachable());
    await expect(ScreenPage(at(REMAINING))).rejects.toMatchObject({
      digest: UNREACHABLE_DIGEST,
    });
  });

  it.each([[`/projects/a.b/revisions/${REVISION}/risks`], [REMAINING]])(
    "is not found at %s when it names no project or revision the API finds",
    async (address) => {
      server.answers = {
        ...ANSWERS,
        "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
      };
      await expect(ScreenPage(at(address))).rejects.toMatchObject({
        digest: "NEXT_HTTP_ERROR_FALLBACK;404",
      });
    },
  );
});
