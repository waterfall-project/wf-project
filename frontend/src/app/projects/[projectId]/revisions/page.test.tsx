// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UnexpectedAnswer } from "@/api/problem";
import { CATALOGUES } from "@/i18n/catalogues";
import { type FakeAnswers, type FakeCall, type FakeClient, fakeClient } from "@/test/fixtures";

import RevisionsPage, { generateMetadata } from "./page";

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

vi.mock("@/api/server", () => ({
  serverClient: () => {
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/p/revisions",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const OFFER = "01926f3a-7c00-7000-8000-000000000100";
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const DRAFT = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const BANNER = '<section aria-label="Contexte de lecture"';
const REVISIONS = `/projects/${PROJECT}/revisions`;
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const GET_IMPORT = "GET /projects/{project_id}/imports/{import_id}";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render in French, as the shell hands its texts to a screen. */
function html(page: ReactNode): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

/** What Next hands the page, at the query given. */
function at(search: Record<string, string> = {}) {
  return {
    params: Promise.resolve({ projectId: PROJECT }),
    searchParams: Promise.resolve(search),
  };
}

/** The calls the page made to the API. */
function calls(): FakeCall[] {
  return server.clients.flatMap((client) => client.calls);
}

/** The call the page made to an operation. */
function callTo(route: string): FakeCall | undefined {
  return calls().find((call) => call.route === route);
}

/** What a table of the page, named so, says: its texts, one space apart. */
function table(markup: string, name: string): string {
  const found = new RegExp(`<table[^>]*aria-label="${name}"[^>]*>(.*?)</table>`).exec(markup);
  return text(found?.[1] ?? "");
}

/** The opening tag of the button a page names so, or `undefined` when it has none. */
function button(markup: string, name: string): string | undefined {
  return [...markup.matchAll(/(<button[^>]*>)(.*?)<\/button>/g)].find(
    (match) => text(match[2] ?? "") === name,
  )?.[1];
}

/** How a page offers the command it names so. */
function offered(markup: string, name: string): "absent" | "available" | "unavailable" {
  const tag = button(markup, name);
  if (tag === undefined) {
    return "absent";
  }
  return tag.includes('aria-disabled="true"') ? "unavailable" : "available";
}

/** The addresses the links of a page lead to, in its order. */
function links(markup: string): string[] {
  return [...markup.matchAll(/<a[^>]*href="([^"]*)"/g)].map(
    (match) => match[1]?.replaceAll("&amp;", "&") ?? "",
  );
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
  };
});

describe("the screen of the revisions of a project", () => {
  it("shows the report of the import its address names above the history, as the screen of the project does [WF-RIS-0050-A] [WF-IHM-0010-A]", async () => {
    server.answers = { ...server.answers, [GET_IMPORT]: "import_analysed" };
    const page = html(await RevisionsPage(at({ import: IMPORT })));
    expect(callTo(GET_IMPORT)?.path).toBe(`/projects/${PROJECT}/imports/${IMPORT}`);
    expect(text(page)).toContain("Compte rendu de l’import");
    expect(page.indexOf("Compte rendu de l’import")).toBeLessThan(
      page.indexOf("Historique des révisions"),
    );
  });

  it("dit que l’import nommé n’existe plus, sans renvoyer à une liste que l’écran n’a pas [US-3280]", async () => {
    server.answers = { ...server.answers, [GET_IMPORT]: NOT_FOUND };
    const page = text(html(await RevisionsPage(at({ import: IMPORT }))));
    expect(page).toContain("L’import que l’adresse nomme n’existe plus");
    expect(page).not.toContain("listés ci-dessous");
  });

  it("reads no import and shows no report when its address names none, or one no identifier can stand for [WF-RIS-0050-A] [WF-IHM-0010-A]", async () => {
    server.answers = { ...server.answers, [GET_IMPORT]: "import_analysed" };
    const plain = html(await RevisionsPage(at()));
    html(await RevisionsPage(at({ import: ".." })));
    expect(callTo(GET_IMPORT)).toBeUndefined();
    expect(text(plain)).not.toContain("Compte rendu de l’import");
  });

  it("names the project, and the revision the address carries [WF-IHM-0020-A]", async () => {
    // Chaque écran de données de projet nomme le projet et la révision affichée.
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(page.startsWith(BANNER)).toBe(true);
    expect(text(page)).toContain(
      "Projet Modernisation du poste de commande Révision Révision en cours",
    );
    expect(page).toMatch(
      /<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Gestion des révisions<\/h1>/,
    );
  });

  // Carries the first sentence of the Vérif of WF-REV-0070-A, the list of the revisions marked,
  // accessible from the project, its table and its links to open one; and the first of WF-REV-0090-A,
  // each attribute of a revision present in the history — version name, description, status, date
  // of marking, reference year, reference character.
  it("lists the revisions in the order of the server, each with the attributes the API gives [WF-REV-0070-A] [WF-REV-0090-A]", async () => {
    const page = html(await RevisionsPage(at()));
    // The history is read whole, by the largest page the contract takes (#303).
    expect(Object.fromEntries(callTo("GET /projects/{project_id}/revisions")?.query ?? [])).toEqual(
      { limit: "500", offset: "0" },
    );
    expect(table(page, "Historique des révisions")).toBe(
      "Version État Marquée le Année de référence Copie de Taux d’inflation Probabilité de gain " +
        "Description Consultation Commandes " +
        "Révision en cours En cours d’élaboration Non marquée 2026 Référence 3 % 100 % Ouvrir " +
        "Référence Référence Marquée 2026 Offre v1.0 3 % 100 % Ouvrir " +
        "Désigner comme référence Condition non remplie : référence encore corrigeable. " +
        "Offre v1.0 Marquée 2025 Aucune 3 % 100 % Offre remise au client avant la commande. Ouvrir " +
        "Désigner comme référence Condition non remplie : référence encore corrigeable.",
    );
    // Each instant of marking, in the local time of the workstation, which the browser writes.
    expect([...page.matchAll(/<time dateTime="([^"]+)"/g)].map((match) => match[1])).toEqual([
      "2026-02-01T09:00:00Z",
      "2025-12-15T16:00:00Z",
    ]);
  });

  it("shows a revision of the history on this screen, the filters carried on, and opens it", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}/subprojects": "subprojects" };
    const page = html(await RevisionsPage(at({ revision_id: DRAFT, subproject_id: SUBPROJECT })));
    const filter = `subproject_id=${SUBPROJECT}`;
    const history = /<table[^>]*aria-label="Historique des révisions"[^>]*>(.*?)<\/table>/.exec(
      page,
    );
    expect(links(history?.[1] ?? "")).toEqual([
      `${REVISIONS}?revision_id=${DRAFT}&${filter}`,
      `${REVISIONS}/${DRAFT}?${filter}`,
      `${REVISIONS}?revision_id=${REFERENCE}&${filter}`,
      `${REVISIONS}/${REFERENCE}?${filter}`,
      `${REVISIONS}?revision_id=${OFFER}&${filter}`,
      `${REVISIONS}/${OFFER}?${filter}`,
    ]);
    // The revision the screen shows is the current page of the history, and it alone.
    const current = [...page.matchAll(/<a[^>]*aria-current="page"[^>]*>/g)].map(
      (match) => match[0],
    );
    expect(links(current.join(""))).toEqual([`${REVISIONS}?revision_id=${DRAFT}&${filter}`]);
    expect(page).toContain('aria-label="Ouvrir la révision «\u00a0Offre v1.0\u00a0»"');
  });

  it("says a project has no revision, in the one card of the screen, which holds no comparison [WF-REV-0070-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = html(await RevisionsPage(at()));
    const words = text(page);
    expect(words).toContain("Ce projet n’a aucune révision.");
    expect(words).not.toContain("Comparaison de deux révisions");
    expect(page.match(/<section[^>]*aria-label="Historique des révisions"/g)).toHaveLength(1);
    expect(page).not.toContain("<form");
  });
});

describe("the screen of the revisions, the history and its commands alone (US-2370)", () => {
  const STRUCTURES = "GET /projects/{project_id}/revisions/{revision_id}/structures";
  const PROPOSAL = "GET /projects/{project_id}/revisions/{revision_id}/rate-update";

  it("reads neither the cost structures nor the rate update, whatever the revision it reads in, and lists none of them", async () => {
    for (const revision of [DRAFT, REFERENCE]) {
      server.answers = {
        ...server.answers,
        "GET /projects/{project_id}/revisions/{revision_id}":
          revision === DRAFT ? "revision_rate_update_offered" : "revision_marked",
      };
      server.clients = [];
      const page = html(await RevisionsPage(at({ revision_id: revision })));
      expect(callTo(STRUCTURES)).toBeUndefined();
      expect(callTo(PROPOSAL)).toBeUndefined();
      expect(text(page)).not.toContain("Structures de coûts");
      expect(text(page)).not.toContain("Taux du référentiel");
      expect(text(page)).not.toContain("Mise à jour des taux proposée");
      expect(text(page)).not.toContain("Désignation de la référence");
    }
  });

  it("offers the rate update as a command of the current revision, as the revision lists it, the proposal left to its dialog [WF-REV-0060-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_rate_update_offered",
    };
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(offered(page, "Appliquer la mise à jour des taux")).toBe("available");
    expect(page).toContain('aria-haspopup="dialog"');
  });

  it("offers the rate update unavailable when the revision lists it lacking a condition [WF-IHM-0090-A]", async () => {
    // `revision` lists `apply_rate_update` lacking `rate_update_available`.
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(offered(page, "Appliquer la mise à jour des taux")).toBe("unavailable");
    expect(text(page)).toContain("une mise à jour des taux disponible");
  });

  it("offers no rate update when the revision does not list the command", async () => {
    // The revision lists `apply_rate_update` for the callers who may exercise it (#1351): a
    // reader's lists none, nor an estimator's (`edit_estimate` alone).
    for (const revision of ["revision_reader", "revision_estimator"] as const) {
      server.answers = {
        ...server.answers,
        "GET /projects/{project_id}/revisions/{revision_id}": revision,
      };
      const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
      expect(offered(page, "Appliquer la mise à jour des taux")).toBe("absent");
    }
  });

  it("offers the designation of the reference on each marked revision of the history, unavailable here, in no region of its own [WF-REV-0040-A]", async () => {
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(text(page)).not.toContain("Désignation de la référence");
    expect(offered(page, "Désigner comme référence")).toBe("unavailable");
  });

  it("reads nothing of a revision when the address carries none", async () => {
    const page = html(await RevisionsPage(at()));
    // The commands of the project remain — the opening of a revision —, those of a revision do not.
    expect(offered(page, "Marquer la révision")).toBe("absent");
    expect(offered(page, "Ouvrir une révision en cours")).toBe("unavailable");
  });
});

describe("the commands of the revision the screen reads in", () => {
  it("offers the commands of a draft revision, those of modification among them [WF-IHM-0020-A]", async () => {
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    // The draft carries amendment 2, not merged: another one opens all the same, several
    // coexisting (WF-REV-0100, #1211).
    for (const name of [
      "Préparer un avenant",
      "Marquer la révision",
      "Abandonner la révision en cours",
    ]) {
      expect(offered(page, name)).toBe("available");
    }
  });

  it("offers no command of modification on a marked revision [WF-IHM-0020-A]", async () => {
    // L'ouverture d'une révision marquée présente cet état et ne propose aucune commande de
    // modification.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
    };
    const page = html(await RevisionsPage(at({ revision_id: REFERENCE })));
    expect(text(page)).toContain("Marquée");
    expect(text(page)).toContain("Lecture seule");
    for (const name of [
      "Préparer un avenant",
      "Marquer la révision",
      "Abandonner la révision en cours",
    ]) {
      expect(offered(page, name)).toBe("unavailable");
    }
  });

  it("does not show a command the user may not exercise [WF-IHM-0090-A]", async () => {
    // Un utilisateur sans la permission de marquer une révision ne voit pas cette commande.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_estimator",
    };
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(offered(page, "Marquer la révision")).toBe("absent");
    // The estimate, the one command left them, is offered by its grid: the screen lists no command
    // of the revision, and the opening of a revision, which the project lists, alone.
    expect(offered(page, "Préparer un avenant")).toBe("absent");
    expect(offered(page, "Abandonner la révision en cours")).toBe("absent");
  });

  it("presents the marking unavailable while a background task runs on the revision, naming the condition", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marking",
    };
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(offered(page, "Marquer la révision")).toBe("unavailable");
    expect(text(page)).toContain(
      "Marquer la révision Condition non remplie : aucun traitement de fond en cours sur l’objet.",
    );
  });
});

describe("the address of the screen of the revisions", () => {
  it.each([
    ["the project", "GET /projects/{project_id}"],
    ["the revision it carries", "GET /projects/{project_id}/revisions/{revision_id}"],
    ["the history", "GET /projects/{project_id}/revisions"],
  ] as const)("is not found when the API does not find %s", async (_, route) => {
    server.answers = { ...server.answers, [route]: NOT_FOUND };
    await expect(RevisionsPage(at({ revision_id: DRAFT }))).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("fails as any read does when the API answers an error for the history, which the banner shares", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions": { problem: { code: "INTERNAL_ERROR", status: 500 } },
    };
    await expect(RevisionsPage(at({ revision_id: DRAFT }))).rejects.toBeInstanceOf(
      UnexpectedAnswer,
    );
  });

  it("is not found at an address that names no project, before the API is asked", async () => {
    const page = RevisionsPage({
      params: Promise.resolve({ projectId: "a.b" }),
      searchParams: Promise.resolve({}),
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(calls()).toEqual([]);
  });

  it("titles the tab with the revisions and the project", async () => {
    const params = Promise.resolve({ projectId: PROJECT });
    expect((await generateMetadata({ params })).title).toBe(
      "Gestion des révisions · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the screen of the revisions served by the service", () => {
  it("shows no note of the mock-up, the history, the revision and its structures being served (US-0960)", async () => {
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(page).not.toContain('role="note"');
    expect(text(page)).not.toContain("Filtres, recherche, tri et pages ignorés");
  });
});
