// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

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
// The path of the screen rendered, which the links of the client components keep.
const shown = vi.hoisted(() => ({ path: "/admin/users" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => shown.path,
  useSearchParams: () => new URLSearchParams(),
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

/** The headings of the columns a grid of a page sorts: those whose header holds a button. */
function sortable(markup: string, table: string): string[] {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === table,
  );
  const head = /<thead[^>]*>(.*?)<\/thead>/.exec(found?.[2] ?? "")?.[1] ?? "";
  return [...head.matchAll(/<th[^>]*>(.*?)<\/th>/g)]
    .filter((header) => (header[1] ?? "").includes("<button"))
    .map((header) => text(header[1] ?? ""));
}

/** The names of the buttons of a page. */
function buttons(markup: string): string[] {
  return [...markup.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((match) => text(match[1] ?? ""));
}

beforeEach(() => {
  shown.path = "/admin/users";
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /users": "users",
    "GET /reference/org-nodes": "org_nodes",
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

  it("present each account with its origin, its roles and its node as the server names them, deactivated ones listed, on a grid sorted by each of its columns [WF-IHM-0060-A]", async () => {
    // A session that may not modify the accounts: no column of commands.
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const page = rendered(await UsersPage(searched()));
    expect(rows(page, "Comptes utilisateurs")).toEqual([
      "Nom Prénom Adresse électronique Origine Rôles d’habilitation Rattachement État",
      "Bernard Dominique dominique.bernard@example.com Importé de l’annuaire Manager Aucun Actif",
      "Lefèvre Sacha sacha.lefevre@example.com Créé par le fournisseur d’identité Aucun rôle Aucun Actif",
      "Martin Camille camille.martin@example.com Créé dans Waterfall Direction de projet Aucun Actif",
      "Moreau Alix alix.moreau@example.com Créé dans Waterfall Chef de projet Bureau d'études électricité Désactivé",
      "Petit Lucas lucas.petit@example.com Créé dans Waterfall Chiffreur Aucun Actif",
      "Roux Inès ines.roux@example.com Créé dans Waterfall Pilotage de projet Aucun Actif",
      "Vidal Noé noe.vidal@example.com Créé dans Waterfall Auditeur Aucun Actif",
      "7 comptes",
    ]);
    expect(sortable(page, "Comptes utilisateurs")).toEqual([
      "Nom",
      "Prénom",
      "Adresse électronique",
      "Origine",
      "Rôles d’habilitation",
      "Rattachement",
      "État",
    ]);
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
    expect(page).not.toContain("<nav");
  });

  it("offer the filters of the origins and of the node, the nodes in the order of the tree", async () => {
    const page = text(rendered(await UsersPage(searched())));
    expect(page).toContain(
      "Toutes les origines Créé dans Waterfall Importé de l’annuaire Créé par le fournisseur d’identité",
    );
    expect(page).toContain("Nœud d’organisation Tous les nœuds DT · Direction technique");
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{}]);
  });

  it("ask the server for the sort, the search, the filters and the page the address names, under the names of the contract", async () => {
    await UsersPage(
      searched({
        sort_by: "org_node",
        sort_order: "desc",
        search: "Mor",
        origins: "identity_provider,local,unknown",
        org_node_id: "01926f3a-7c00-7000-8000-000000000471",
        offset: "50",
      }),
    );
    expect(queriesOf("GET /users")).toEqual([
      {
        include_inactive: "true",
        offset: "50",
        search: "Mor",
        origins: "local,identity_provider",
        org_node_id: "01926f3a-7c00-7000-8000-000000000471",
        sort_by: "org_node",
        sort_order: "desc",
      },
    ]);
  });

  it("ask no sort, no filter and the first page of an address whose values no server could take", async () => {
    await UsersPage(
      searched({ sort_by: "avatar", origins: "nowhere", org_node_id: "a.b", offset: "-3" }),
    );
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
  });

  it("stand without a node to choose when the tree of the organisation is not found", async () => {
    server.answers = { ...server.answers, "GET /reference/org-nodes": NOT_FOUND };
    const page = text(rendered(await UsersPage(searched())));
    expect(page).toContain("Nœud d’organisation Tous les nœuds Tous les rôles Administrateur");
    expect(page).toContain("Comptes actifs Comptes désactivés Colonnes Nom");
  });

  it("ask the server for the access roles the address names among those it gives, an identifier of none not asked [WF-IHM-0130-A]", async () => {
    const manager = "01926f3a-7c00-7000-8000-000000000702";
    const chief = "01926f3a-7c00-7000-8000-000000000703";
    server.answers = { ...server.answers, "GET /users": "users_by_access_role" };
    const page = text(
      rendered(
        await UsersPage(
          searched({
            access_role_ids: `${manager},01926f3a-7c00-7000-8000-000000000799,${chief},a.b`,
          }),
        ),
      ),
    );
    expect(queriesOf("GET /users")).toEqual([
      { include_inactive: "true", access_role_ids: `${chief},${manager}` },
    ]);
    expect(page).toContain("2 comptes");
  });

  it("ask the server for the state the address names, the deactivated accounts alone said as the server reads them [WF-IHM-0130-A]", async () => {
    server.answers = { ...server.answers, "GET /users": "users_inactive" };
    const page = text(rendered(await UsersPage(searched({ is_active: "false" }))));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true", is_active: "false" }]);
    expect(page).toContain("Moreau Alix alix.moreau@example.com");
    expect(page).toContain("1 compte");
    server.clients = [];
    await UsersPage(searched({ is_active: "maybe" }));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
  });

  it("offer no filter by access role to a session that may not read the roles, and ask none", async () => {
    server.answers = { ...server.answers, "GET /access-roles": NOT_FOUND };
    const page = text(
      rendered(
        await UsersPage(searched({ access_role_ids: "01926f3a-7c00-7000-8000-000000000702" })),
      ),
    );
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
    expect(page).not.toContain("Tous les rôles");
    expect(page).toContain("Nœud d’organisation Tous les nœuds");
  });

  it("offer to delete no account [WF-ADM-0060-A]; to a session that may modify the accounts, offer to create a local account, and to modify, deactivate or reactivate each and attribute its roles", async () => {
    const page = rendered(await UsersPage(searched()));
    expect(text(page)).not.toMatch(/Supprimer/);
    expect(buttons(page)).toContain("Créer un compte local");
    expect(rows(page, "Comptes utilisateurs")[0]).toBe(
      "Nom Prénom Adresse électronique Origine Rôles d’habilitation Rattachement État Modifier Activation Attribution des rôles",
    );
    expect(page).toContain('aria-label="Réactiver «\u00a0Alix Moreau\u00a0»"');
    expect(page).toContain('aria-label="Désactiver «\u00a0Camille Martin\u00a0»"');
    expect(page).toContain('aria-label="Attribuer les rôles de «\u00a0Inès Roux\u00a0»"');
  });

  it("offer no command of the accounts to a session that may not modify them", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const page = rendered(await UsersPage(searched()));
    expect(
      buttons(page).filter((name) =>
        /Supprimer|Désactiver|Réactiver|Créer|Modifier|Attribuer/.test(name),
      ),
    ).toEqual([]);
  });

  it("ask the deactivated accounts too, and read an address that hid them as the active ones alone, which the choice says", async () => {
    const page = rendered(await UsersPage(searched({ include_inactive: "false", offset: "2" })));
    expect(queriesOf("GET /users")).toEqual([
      { include_inactive: "true", offset: "2", is_active: "true" },
    ]);
    expect(page).toMatch(/<option value="true" selected="">Comptes actifs<\/option>/);
    expect(page).not.toContain("les désactivés</a>");
    server.clients = [];
    await UsersPage(searched({ include_inactive: "maybe" }));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true" }]);
  });

  it("ask the page the address names, and lead back to the one before it", async () => {
    server.answers = {
      ...server.answers,
      "GET /users": "users_page",
      "GET /me": "me_estimator",
    };
    const page = rendered(await UsersPage(searched({ offset: "2" })));
    expect(queriesOf("GET /users")).toEqual([{ include_inactive: "true", offset: "2" }]);
    expect(rows(page, "Comptes utilisateurs").slice(1)).toEqual([
      "Martin Camille camille.martin@example.com Créé dans Waterfall Direction de projet Aucun Actif",
      "Moreau Alix alix.moreau@example.com Créé dans Waterfall Chef de projet Bureau d'études électricité Désactivé",
      "7 comptes",
    ]);
    // The pages before and after: the state of the accounts is a choice, no link.
    expect(links(page)).toEqual(["/admin/users", "/admin/users?offset=4"]);
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

  it("present each role, predefined or composed, with how many accounts hold it, on a grid sorted by each of its columns [WF-IHM-0060-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const page = rendered(await AccessRolesPage(searched()));
    expect(rows(page, "Rôles d’habilitation")).toEqual([
      "Libellé Nature Comptes porteurs",
      "Administrateur Prédéfini 0",
      "Auditeur Composé 1",
      "Chef de projet Prédéfini 1",
      "Chiffreur Composé 1",
      "Direction de projet Composé 1",
      "Manager Prédéfini 1",
      "Pilotage de projet Composé 1",
      "7 rôles",
    ]);
    expect(sortable(page, "Rôles d’habilitation")).toEqual([
      "Libellé",
      "Nature",
      "Comptes porteurs",
    ]);
    expect(queriesOf("GET /access-roles")).toEqual([{}]);
  });

  it("ask the server for the search and the sort the address names, and every role for the matrix", async () => {
    await AccessRolesPage(
      searched({ search: "Chef", sort_by: "holder_count", sort_order: "desc" }),
    );
    expect(queriesOf("GET /access-roles")).toEqual([
      { search: "Chef", sort_by: "holder_count", sort_order: "desc" },
      {},
    ]);
  });

  it("ask the server for the kind and the bounds of the holders the address names, and every role for the matrix [WF-IHM-0130-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /access-roles": ["access_roles_unheld", "access_roles"],
    };
    const page = rendered(
      await AccessRolesPage(searched({ is_predefined: "true", holder_count_max: "0" })),
    );
    expect(queriesOf("GET /access-roles")).toEqual([
      { is_predefined: "true", holder_count_max: "0" },
      {},
    ]);
    expect(rows(page, "Rôles d’habilitation").slice(1)).toEqual([
      "Administrateur Prédéfini 0 Modifier Supprimer",
      "1 rôle",
    ]);
    // The matrix holds every role, whatever the grid asks.
    expect(rows(page, "Permissions par fonction")[0]).toContain("Pilotage de projet");
  });

  it("ask no bound that is no count, nor a kind that is none", async () => {
    await AccessRolesPage(
      searched({ is_predefined: "yes", holder_count_min: "-1", holder_count_max: "1.5" }),
    );
    expect(queriesOf("GET /access-roles")).toEqual([{}]);
  });

  it("say at its field the bound the API refuses, the grid unread, the matrix of every role kept", async () => {
    server.answers = {
      ...server.answers,
      "GET /access-roles": [
        { problem: example("access_roles_bounds_inverted") as Problem & { status: 422 } },
        "access_roles",
      ],
    };
    const page = rendered(
      await AccessRolesPage(searched({ holder_count_min: "2", holder_count_max: "1" })),
    );
    expect(page).not.toContain('aria-label="Rôles d’habilitation" role="grid"');
    expect(text(page)).toContain(text(CATALOGUES.fr.reference.boundsRefused));
    expect(text(page)).toContain("La borne supérieure ne peut précéder la borne inférieure, 2.");
    expect(rows(page, "Permissions par fonction")[0]).toContain("Pilotage de projet");
  });

  it("offer to a session that may modify the roles the commands to create one, and to modify and delete each", async () => {
    const page = rendered(await AccessRolesPage(searched()));
    expect(rows(page, "Rôles d’habilitation")[0]).toBe(
      "Libellé Nature Comptes porteurs Modifier Supprimer",
    );
    expect(buttons(page)).toContain("Créer un rôle");
    expect(page).toContain('aria-label="Supprimer «\u00a0Chiffreur\u00a0»"');
    expect(page).toContain('aria-label="Modifier «\u00a0Manager\u00a0»"');
  });

  it("present the permissions of the catalogue in its order, under the function of the second level each covers, and whether each role holds it", async () => {
    const matrix = rows(rendered(await AccessRolesPage(searched())), "Permissions par fonction");
    // A header, forty-eight permissions of the functions, the consultation of the journal of
    // audit, eight irreversible and two structuring.
    expect(matrix).toHaveLength(60);
    // Named by the catalogue, never by a code of the FBS (#518).
    expect(matrix).toContain(
      "Journal d’audit Consulter le journal d’audit Accordée Accordée Non accordée Non accordée Accordée Non accordée Non accordée",
    );
    expect(matrix.slice(0, 3)).toEqual([
      "Fonction Permission Administrateur Auditeur Chef de projet Chiffreur Direction de projet Manager Pilotage de projet",
      "Gestion des utilisateurs Consulter les utilisateurs Accordée Non accordée Non accordée Non accordée Accordée Non accordée Non accordée",
      "Modifier les utilisateurs Accordée Non accordée Non accordée Non accordée Accordée Non accordée Non accordée",
    ]);
    expect(matrix).toContain(
      "Paramètres de coûts Consulter les paramètres de coûts Non accordée Non accordée Accordée Accordée Accordée Accordée Accordée",
    );
    expect(matrix.slice(-11)).toEqual([
      "Modifier le cycle de vie du projet Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Action irréversible Marquer une révision Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Abandonner une révision en cours Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Désigner la révision de référence Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Fusionner un différentiel Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Clore un projet : terminé, perdu ou abandonné Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Déclarer la survenance d’un risque Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Exclure des lignes de coût réel Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Restaurer la plateforme Accordée Non accordée Non accordée Non accordée Accordée Non accordée Non accordée",
      "Permission structurante Créer un projet Non accordée Non accordée Accordée Non accordée Accordée Non accordée Accordée",
      "Consulter tous les projets Non accordée Non accordée Non accordée Non accordée Accordée Accordée Non accordée",
    ]);
  });

  it("offer to create no permission, nor any command of the roles to a session that may not modify them [WF-ADM-0100-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    const page = rendered(await AccessRolesPage(searched()));
    expect(buttons(page).filter((name) => /Créer|Modifier|Supprimer/.test(name))).toEqual([]);
    expect(links(page)).toEqual([]);
  });
});

describe("the codes of the FBS", () => {
  it("are shown nowhere on the screen of the roles: no text of it holds one", async () => {
    const page = rendered(await AccessRolesPage(searched()));
    // The texts of the page, between its tags; an attribute may keep a code as an internal key.
    const texts = [...page.matchAll(/>([^<]+)</g)].map((match) => match[1] ?? "");
    expect(texts.length).toBeGreaterThan(100);
    expect(texts.filter((each) => each.includes("FBS-"))).toEqual([]);
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
      "Copie externe de la sauvegarde Réussie",
      "Test de restauration Réussie",
    ]);
    expect(instants(page)).toEqual(
      expect.arrayContaining([
        "2026-06-03T02:00:00Z",
        "2026-06-03T01:00:00Z",
        "2026-06-03T01:14:00Z",
        "2026-06-01T03:00:00Z",
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

  it("name the component of an alert that names one, and the space of a storage nearly full [WF-OBS-0030-A]", async () => {
    server.answers = { ...server.answers, "GET /system/status": "system_status_backup_failed" };
    let page = rendered(await SystemStatusPage());
    expect(rows(page, "Alertes en cours")).toContain(
      "Alerte Composant indisponible Stockage des fichiers",
    );
    server.answers = { ...server.answers, "GET /system/status": "system_status_storage_full" };
    page = rendered(await SystemStatusPage());
    expect(rows(page, "Alertes en cours")).toEqual([
      "Niveau Alerte Depuis",
      "Vigilance Stockage presque plein 205 gigaoctets employés, 9 gigaoctets libres",
    ]);
  });

  it("signal the failure of a scheduled backup as an alert under way, with its motive [WF-ADM-0170-A]", async () => {
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

  it("signal the failure of the external copy of a scheduled backup as an alert under way, with its location and its motive [WF-ADM-0170-A]", async () => {
    // Un échec planifié, de sauvegarde ou de copie, apparaît comme alerte sur l'écran d'état.
    server.answers = { ...server.answers, "GET /system/status": "system_status_copy_failed" };
    const page = rendered(await SystemStatusPage());
    expect(rows(page, "Alertes en cours")).toEqual([
      "Niveau Alerte Depuis",
      "Alerte Échec de la copie externe d’une sauvegarde planifiée secours-lyon : Espace épuisé",
    ]);
    expect(rows(page, "Dernières opérations").slice(2, 4)).toEqual([
      "Sauvegarde Réussie",
      "Copie externe de la sauvegarde Échouée",
    ]);
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
    expect(instants(page)[0]).toBe("2026-06-03T01:00:00Z");
    expect(text(page)).toContain("8 sauvegardes");
  });

  it("present their schedule and retention, and start neither a backup nor a restoration", async () => {
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Planification État Active Fréquence Quotidienne Heure 01:00 UTC Rétention 7 sauvegardes conservées",
    );
    expect(buttons(page)).toEqual([]);
    expect(links(page)).toEqual([]);
  });

  it("present the external copy of the scheduled backups, the location by the name the installation declares", async () => {
    // The screen reads the copy the schedule sets; the form comes with the commands (#519).
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Copie externe Vers secours-lyon, dossier waterfall/sauvegardes — 30 copies gardées",
    );
  });

  it("name the day of a weekly schedule, and say it has no external copy", async () => {
    server.answers = { ...server.answers, "GET /backup-schedule": "backup_schedule_weekly" };
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Fréquence Hebdomadaire Jour Dimanche Heure 02:30 UTC Rétention 4 sauvegardes conservées Copie externe Aucune",
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
    shown.path = "/admin/backups";
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
