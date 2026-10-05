// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import SystemStatusPage, { generateMetadata as statusMetadata } from "../system/page";
import AccessRolesPage, { generateMetadata as rolesMetadata } from "./access-roles/page";
import BackupsPage, { generateMetadata as backupsMetadata } from "./backups/page";
import UsersPage, { generateMetadata as usersMetadata } from "./users/page";

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

const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render a page of the administration in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The search parameters of an address. */
function searched(search: PageSearchParams = {}) {
  return { searchParams: Promise.resolve(search) };
}

/** The queries of the calls the pages made to an operation. */
function queriesOf(route: string) {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => Object.fromEntries(call.query));
}

/** The texts of the rows of a table of a page, by its name. */
function rows(markup: string, table: string): string[] {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === table,
  );
  expect(found).toBeDefined();
  return [...(found?.[2] ?? "").matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((row) => text(row[1] ?? ""));
}

/** The instants a page writes for the browser to show in its local time. */
function instants(markup: string): string[] {
  return [...markup.matchAll(/<time datetime="([^"]*)"/gi)].map((match) => match[1] ?? "");
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/<a [^>]*href="([^"]*)"/g)].map((match) => match[1] ?? "");
}

/** The names of the buttons of a page. */
function buttons(markup: string): string[] {
  return [...markup.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((match) => text(match[1] ?? ""));
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /users": "users",
    "GET /access-roles": "access_roles",
    "GET /permissions": "permissions",
    "GET /system/status": "system_status",
    "GET /backups": "backups",
    "GET /backup-schedule": "backup_schedule",
  };
});

describe("the accounts", () => {
  it("title the tab with the function", async () => {
    expect((await usersMetadata()).title).toBe("Gestion des utilisateurs — Waterfall");
  });

  it("present each account with its origin, its roles and its node as the server names them, deactivated ones listed, asked of the server", async () => {
    const page = rendered(await UsersPage(searched()));
    expect(rows(page, "Comptes utilisateurs")).toEqual([
      "Nom Prénom Adresse électronique Origine Rôles d’habilitation Rattachement État",
      "Bernard Dominique dominique.bernard@example.com Importé de l’annuaire Manager Aucun Actif",
      "Lefèvre Sacha sacha.lefevre@example.com Créé par le fournisseur d’identité Aucun rôle Aucun Actif",
      "Martin Camille camille.martin@example.com Créé dans Waterfall Direction de projet Aucun Actif",
      "Moreau Alix alix.moreau@example.com Créé dans Waterfall Chef de projet Bureau d'études électricité Désactivé",
    ]);
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
    expect(text(page)).toContain("4 comptes");
    expect(page).not.toContain("<nav");
  });

  it("offer to delete no account, nor anything else [WF-ADM-0060-A]", async () => {
    const page = rendered(await UsersPage(searched()));
    expect(buttons(page)).toEqual([]);
    expect(text(page)).not.toMatch(/Supprimer/);
  });

  it("ask the page the address names, and lead back to the one before it", async () => {
    server.answers = { ...server.answers, "GET /users": "users_page" };
    const page = rendered(await UsersPage(searched({ offset: "2" })));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true", offset: "2" }]);
    expect(rows(page, "Comptes utilisateurs").slice(1)).toEqual([
      "Martin Camille camille.martin@example.com Créé dans Waterfall Direction de projet Aucun Actif",
      "Moreau Alix alix.moreau@example.com Créé dans Waterfall Chef de projet Bureau d'études électricité Désactivé",
    ]);
    expect(links(page)).toEqual(["/admin/users"]);
    expect(text(page)).toContain("4 comptes Page précédente");
  });

  it("ask the first page of an address whose page no server could take", async () => {
    await UsersPage(searched({ offset: "-3" }));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
  });

  it("are not found when the API refuses or does not find the list", async () => {
    server.answers = { ...server.answers, "GET /users": NOT_FOUND };
    await expect(UsersPage(searched())).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});

describe("the access roles", () => {
  it("title the tab with the function", async () => {
    expect((await rolesMetadata()).title).toBe("Gestion des rôles d’habilitation — Waterfall");
  });

  it("present each role, predefined or composed, with how many accounts hold it", async () => {
    const page = rendered(await AccessRolesPage());
    expect(rows(page, "Rôles d’habilitation")).toEqual([
      "Libellé Nature Comptes porteurs",
      "Administrateur Prédéfini 0",
      "Chef de projet Prédéfini 1",
      "Direction de projet Composé 1",
      "Manager Prédéfini 1",
    ]);
  });

  it("present the permissions of the catalogue in its order, under the function of the second level each covers, and whether each role holds it", async () => {
    const matrix = rows(rendered(await AccessRolesPage()), "Permissions par fonction");
    expect(matrix).toHaveLength(56);
    expect(matrix.slice(0, 3)).toEqual([
      "Fonction Permission Administrateur Chef de projet Direction de projet Manager",
      "FBS-1.1 Gestion des utilisateurs Consulter les utilisateurs Accordée Non accordée Accordée Non accordée",
      "Modifier les utilisateurs Accordée Non accordée Accordée Non accordée",
    ]);
    expect(matrix).toContain(
      "FBS-3.1 Paramètres de coûts Consulter les paramètres de coûts Non accordée Accordée Accordée Accordée",
    );
    expect(matrix.slice(-8)).toEqual([
      "Modifier le cycle de vie du projet Non accordée Accordée Accordée Non accordée",
      "Action irréversible Marquer une révision Non accordée Accordée Accordée Non accordée",
      "Désigner la révision de référence Non accordée Accordée Accordée Non accordée",
      "Clore un projet : terminé, perdu ou abandonné Non accordée Accordée Accordée Non accordée",
      "Déclarer la survenance d’un risque Non accordée Accordée Accordée Non accordée",
      "Exclure des lignes de coût réel Non accordée Accordée Accordée Non accordée",
      "Restaurer la plateforme Accordée Non accordée Accordée Non accordée",
      "Permission structurante Consulter tous les projets Non accordée Non accordée Accordée Accordée",
    ]);
  });

  it("offer to create no permission, nor anything else [WF-ADM-0100-A]", async () => {
    const page = rendered(await AccessRolesPage());
    expect(buttons(page)).toEqual([]);
    expect(links(page)).toEqual([]);
  });
});

describe("the state of the system", () => {
  it("title the tab with the function", async () => {
    expect((await statusMetadata()).title).toBe("Surveillance de l’état du système — Waterfall");
  });

  it("say the version installed, and date the last reading of the accounts of the identity provider and the last restoration test [WF-ADM-0130-A]", async () => {
    const page = rendered(await SystemStatusPage());
    expect(text(page)).toContain("Version installée : 1.0.0");
    expect(rows(page, "Dernières opérations")).toEqual([
      "Opération Date Résultat Motif",
      "Lecture des comptes du fournisseur d’identité Réussie",
      "Sauvegarde Réussie",
      "Test de restauration Réussie",
    ]);
    expect(instants(page)).toEqual(
      expect.arrayContaining([
        "2026-03-16T02:00:00Z",
        "2026-03-16T01:00:00Z",
        "2026-03-01T03:00:00Z",
      ]),
    );
  });

  it("present each component, available or not, checked when, and the storage used and available", async () => {
    const page = rendered(await SystemStatusPage());
    const components = rows(page, "Composants");
    expect(components).toHaveLength(8);
    expect(components.slice(0, 2)).toEqual([
      "Composant Disponibilité Dernière vérification Version",
      "Service d’API Disponible 1.0.0",
    ]);
    expect(text(page)).toContain(
      "Espace de stockage Utilisé 39 gigaoctets Disponible 161 gigaoctets",
    );
    expect(text(page)).toContain("Aucune alerte en cours.");
  });

  it("signal the failure of a scheduled backup as an alert under way, with its motive, and name the component unavailable [WF-ADM-0170-A]", async () => {
    server.answers = { ...server.answers, "GET /system/status": "system_status_backup_failed" };
    const page = rendered(await SystemStatusPage());
    expect(rows(page, "Alertes en cours")).toEqual([
      "Niveau Alerte Depuis",
      "Alerte Échec de la sauvegarde planifiée",
      "Alerte Composant indisponible Stockage des fichiers",
    ]);
    expect(rows(page, "Dernières opérations")[2]).toBe(
      "Sauvegarde Échouée Un composant du service est indisponible. Composant indisponible : Stockage des fichiers.",
    );
    expect(rows(page, "Composants")).toContain("Stockage des fichiers Indisponible");
  });
});

describe("the backups", () => {
  it("title the tab with the function", async () => {
    expect((await backupsMetadata()).title).toBe("Sauvegarde et restauration — Waterfall");
  });

  it("present each backup with its date, its size and its verification [WF-ADM-0150-A]", async () => {
    const page = rendered(await BackupsPage(searched()));
    const backups = rows(page, "Sauvegardes");
    expect(backups).toHaveLength(9);
    expect(backups.slice(0, 2)).toEqual([
      "Date Taille Vérification Déclenchement Conservation",
      "1,2 gigaoctet Vérifiée Planifiée",
    ]);
    expect(backups[8]).toBe("900 mégaoctets Vérifiée Manuelle Marquée à conserver");
    expect(instants(page)[0]).toBe("2026-03-16T01:00:00Z");
    expect(text(page)).toContain("8 sauvegardes");
  });

  it("present their schedule and retention, and start neither a backup nor a restoration", async () => {
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Planification État Active Fréquence Quotidienne Heure 01:00, heure de la plateforme Rétention 7 sauvegardes conservées",
    );
    expect(buttons(page)).toEqual([]);
    expect(links(page)).toEqual([]);
  });

  it("name the day of a weekly schedule", async () => {
    server.answers = { ...server.answers, "GET /backup-schedule": "backup_schedule_weekly" };
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Fréquence Hebdomadaire Jour Dimanche Heure 02:30, heure de la plateforme Rétention 4 sauvegardes conservées",
    );
  });

  it("say there is none yet, once", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_empty" };
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toMatch(/Sauvegardes Aucune sauvegarde\.$/);
    expect(page).not.toContain('<table aria-label="Sauvegardes"');
  });

  it("say a page asked beyond the end of the list is no empty list, and lead back to its last page", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_beyond" };
    const page = rendered(await BackupsPage(searched({ offset: "50" })));
    expect(queriesOf("GET /backups")).toEqual([{ offset: "50" }]);
    expect(text(page)).not.toContain("Aucune sauvegarde.");
    expect(page).not.toContain('<table aria-label="Sauvegardes"');
    expect(text(page)).toContain(
      "8 sauvegardes Cette page est au-delà de la fin de la liste. Page précédente",
    );
    expect(links(page)).toEqual(["/admin/backups"]);
  });
});
