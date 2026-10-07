// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/rate-update": "rate_update",
    "GET /projects/{project_id}/revisions/comparison": "comparison",
  };
});

describe("the screen of the revisions of a project", () => {
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

  it("lists the revisions in the order of the server, each with the attributes the API gives", async () => {
    const page = html(await RevisionsPage(at()));
    // The history is read whole, by the largest page the contract takes (#303).
    expect(Object.fromEntries(callTo("GET /projects/{project_id}/revisions")?.query ?? [])).toEqual(
      { limit: "500", offset: "0" },
    );
    expect(table(page, "Historique des révisions")).toBe(
      "Version État Marquée le Description Consultation " +
        "Référence Référence Marquée Ouvrir " +
        "Révision en cours En cours d’élaboration Non marquée Ouvrir " +
        "Offre v1.0 Marquée Offre remise au client avant la commande. Ouvrir",
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
      `${REVISIONS}?revision_id=${REFERENCE}&${filter}`,
      `${REVISIONS}/${REFERENCE}?${filter}`,
      `${REVISIONS}?revision_id=${DRAFT}&${filter}`,
      `${REVISIONS}/${DRAFT}?${filter}`,
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

  it("says a project has no revision, and offers no comparison", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = html(await RevisionsPage(at()));
    expect(text(page)).toContain(
      "Historique des révisions Ce projet n’a aucune révision. " +
        "Comparaison de deux révisions La comparaison demande deux révisions marquées.",
    );
    expect(page).not.toContain("<form");
  });
});

describe("the comparison of two revisions", () => {
  it("offers the marked revisions alone, the second compared to the first by default", async () => {
    const page = html(await RevisionsPage(at({ revision_id: DRAFT, as_of: "2026-05-31" })));
    expect(callTo("GET /projects/{project_id}/revisions/comparison")).toBeUndefined();
    const form = /<form[^>]*action="([^"]*)"[^>]*>(.*?)<\/form>/.exec(page);
    expect(form?.[1]).toBe(REVISIONS);
    const fields = form?.[2] ?? "";
    // The context of the screen is carried on, named as the address names it.
    expect(
      [...fields.matchAll(/<input type="hidden" name="([^"]+)" value="([^"]+)"/g)].map(
        (match) => `${match[1] ?? ""}=${match[2] ?? ""}`,
      ),
    ).toEqual([`revision_id=${DRAFT}`, "as_of=2026-05-31"]);
    expect([...fields.matchAll(/<select[^>]*name="([^"]+)"/g)].map((match) => match[1])).toEqual([
      "from_revision_id",
      "to_revision_id",
    ]);
    const selected = [...fields.matchAll(/<option[^>]*value="([^"]+)" selected="">/g)].map(
      (match) => match[1],
    );
    expect(selected).toEqual([OFFER, REFERENCE]);
    expect(text(fields)).toBe(
      "De la révision Référence Offre v1.0 À la révision Référence Offre v1.0 Comparer",
    );
  });

  it("presents what compareRevisions gives, nothing paired, summed nor ordered by the front [WF-ARC-0020-A]", async () => {
    // Les montants, dates et indices affichés sont ceux que l'API renvoie, sans recalcul.
    const page = html(
      await RevisionsPage(at({ from_revision_id: OFFER, to_revision_id: REFERENCE })),
    );
    const call = callTo("GET /projects/{project_id}/revisions/comparison");
    expect(call?.path).toBe(`${REVISIONS}/comparison`);
    expect(call?.query.toString()).toBe(`from_revision_id=${OFFER}&to_revision_id=${REFERENCE}`);
    expect(table(page, "Ajouts")).toBe(
      "Libellé Nature Réception usine Tâche Provision — risque de reprise du câblage Ligne de devis",
    );
    expect(table(page, "Retraits")).toBe("Libellé Nature Essais préliminaires sur site Tâche");
    expect(table(page, "Modifications")).toBe(
      "Libellé Nature Ce qui change Câblage des armoires Tâche Dates Durée " +
        "Raccordement des borniers Ligne de devis Montant budgété Montant réestimé",
    );
    // The deviations as the API gives them, in its order, each named by the label it resolves
    // (#204): no total the front would add up, no identifier shown.
    expect(table(page, "Écarts de montants")).toBe(
      "Axe Poste Écart " +
        "Nature de coût Main-d'œuvre 1 200,00 Nature de coût Débours -350,00 " +
        "Nature de coût Provision 500,00 Sous-projet Poste de commande 850,00 " +
        "Sous-projet Hors sous-projet 500,00",
    );
    expect(page).not.toContain("01926f3a-7c00-7000-8000-000000000461");
    // The choice keeps the two revisions compared.
    const selected = [...page.matchAll(/<option[^>]*value="([^"]+)" selected="">/g)].map(
      (match) => match[1],
    );
    expect(selected).toEqual([OFFER, REFERENCE]);
  });

  it("says each part empty for an identical pair — the same revision twice, compared, not refused", async () => {
    // Le contrat le dit : une paire identique rend une comparaison vide, jamais un refus.
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/comparison": "comparison_identical",
    };
    const page = html(await RevisionsPage(at({ from_revision_id: OFFER, to_revision_id: OFFER })));
    expect(callTo("GET /projects/{project_id}/revisions/comparison")?.query.toString()).toBe(
      `from_revision_id=${OFFER}&to_revision_id=${OFFER}`,
    );
    expect(text(page)).toContain(
      "Ajouts Rien n’a été ajouté. Retraits Rien n’a été retiré. " +
        "Modifications Rien n’a été modifié. Écarts de montants Aucun écart de montant.",
    );
  });

  it("asks nothing of the API until the address names both revisions", async () => {
    await RevisionsPage(at({ from_revision_id: OFFER, to_revision_id: "" }));
    expect(callTo("GET /projects/{project_id}/revisions/comparison")).toBeUndefined();
  });

  it("is not found when the API finds neither revision, as the other screens of a project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/comparison": NOT_FOUND,
    };
    await expect(
      RevisionsPage(at({ from_revision_id: OFFER, to_revision_id: REFERENCE })),
    ).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});

describe("the parts of the revision the screen reads in", () => {
  it("lists its cost structures, each by its nature and its label, an amendment merged said so", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": "revision_marked",
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures_amendments",
    };
    const page = html(await RevisionsPage(at({ revision_id: REFERENCE })));
    expect(callTo("GET /projects/{project_id}/revisions/{revision_id}/structures")?.path).toBe(
      `${REVISIONS}/${REFERENCE}/structures`,
    );
    expect(table(page, "Structures de coûts")).toBe(
      "Nature Libellé État Structure principale Structure principale " +
        "Avenant Avenant 1 — extension du poste Fusionnée Avenant Avenant 2 — reprise des essais " +
        "Devis de risque Risque de reprise du câblage " +
        "Devis de risque Retard de livraison des armoires " +
        "Devis de risque Indisponibilité de l'automaticien",
    );
    // A marked revision is immutable: no rate update is read for it.
    expect(
      callTo("GET /projects/{project_id}/revisions/{revision_id}/rate-update"),
    ).toBeUndefined();
    expect(text(page)).not.toContain("Mise à jour des taux");
  });

  it("presents the rate update proposed for the current revision, category by category, as the API gives it", async () => {
    // À la création d'une révision suivant une modification de taux, l'écart est présenté
    // catégorie par catégorie — la mise à jour, jamais imposée, n'est pas appliquée ici.
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(callTo("GET /projects/{project_id}/revisions/{revision_id}/rate-update")?.path).toBe(
      `${REVISIONS}/${DRAFT}/rate-update`,
    );
    expect(text(page)).toContain(
      "Mise à jour des taux proposée Taux de l’année 2026 Une proposition, jamais imposée",
    );
    expect(table(page, "Mise à jour des taux proposée")).toBe(
      "Catégorie Taux précédent Taux proposé Origine " +
        "Ingénierie électrique 78,50 80,86 Taux précédent, projeté par l’inflation " +
        "Mise en service 80,00 82,40 Taux précédent, projeté par l’inflation",
    );
  });

  it("says the reference has not changed when no rate update is proposed", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/rate-update": "rate_update_none",
      "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    };
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    expect(text(page)).toContain(
      "Mise à jour des taux proposée Le référentiel n’a pas changé : aucune mise à jour des taux n’est proposée.",
    );
    expect(text(page)).not.toContain("Taux de l’année");
  });

  it("reads nothing of a revision when the address carries none", async () => {
    const page = html(await RevisionsPage(at()));
    expect(calls().map((call) => call.route)).not.toContain(
      "GET /projects/{project_id}/revisions/{revision_id}/structures",
    );
    expect(text(page)).not.toContain("Structures de coûts");
    expect(page).not.toContain('aria-label="Commandes"');
  });
});

describe("the commands of the revision the screen reads in", () => {
  it("offers the commands of a draft revision, those of modification among them [WF-IHM-0020-A]", async () => {
    const page = html(await RevisionsPage(at({ revision_id: DRAFT })));
    for (const name of ["Modifier le planning", "Modifier le devis", "Marquer la révision"]) {
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
      "Modifier le planning",
      "Modifier le devis",
      "Réestimer le reste à engager",
      "Créer une structure",
      "Fusionner une structure",
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
    expect(offered(page, "Modifier le devis")).toBe("available");
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
