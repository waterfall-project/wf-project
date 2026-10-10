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
// The session of the contract, some of its permissions withdrawn for a test: no example lacks the
// modification of the backups alone, and one would ripple through the accounts, the roles and the
// journal of the witness.
const withdrawn = vi.hoisted(() => ({ permissions: [] as string[] }));
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            permissions: session.permissions.filter(
              (permission) => !withdrawn.permissions.includes(permission),
            ),
          };
    },
  };
});
// The tracker of the shell, which the command that starts a backup hands its task over to.
vi.mock("@/components/tasks/task-tracker", () => ({
  useTrackTask: () => () => undefined,
  afterReveal: () => () => undefined,
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
  withdrawn.permissions = [];
  shown.path = "/admin/users";
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /users": "users",
    "GET /reference/org-nodes": "org_nodes",
    "GET /access-roles": "access_roles",
    "GET /permissions": "permissions",
    "GET /system/status": "system_status",
    "GET /backups": "backups",
    "GET /backup-schedule": "backup_schedule",
    "GET /external-backup-locations": "external_backup_locations",
  };
});

describe("the accounts", () => {
  it("title the tab with the function", async () => {
    expect((await usersMetadata()).title).toBe("Gestion des utilisateurs — Waterfall");
  });

  it("present each account with its origin, its roles and its node as the server names them, deactivated ones listed, on a grid sorted by each of its columns [WF-IHM-0060-A]", async () => {
    // A session that may not modify the accounts: no column of commands.
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const page = rendered(await UsersPage(searched()));
    expect(rows(page, "Comptes utilisateurs")).toEqual([
      "Nom Prénom Adresse électronique Origine Rôles d’habilitation Rattachement État",
      "Bernard Dominique dominique.bernard@example.com Importé de l’annuaire Manager Aucun Actif",
      "Lefèvre Sacha sacha.lefevre@example.com Créé par le fournisseur d’identité Aucun rôle Atelier de câblage Actif",
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
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
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
      "GET /session": "session_estimator",
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
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
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
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
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

/** The sort the server gives the backups unasked, which the page asks when the address says nothing. */
const NEWEST_BACKUPS = { sort_by: "taken_at", sort_order: "desc" };

describe("the backups", () => {
  it("title the tab with the function", async () => {
    expect((await backupsMetadata()).title).toBe("Sauvegarde et restauration — Waterfall");
  });

  it("present each backup with its date, its size and its verification [WF-ADM-0150-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": "session_estimator",
      "GET /backups": "backups_reader",
    };
    const page = rendered(await BackupsPage(searched()));
    const backups = rows(page, "Sauvegardes");
    expect(backups).toHaveLength(10);
    expect(backups.slice(0, 2)).toEqual([
      "Date Taille Vérification Déclenchement Conservation",
      "1,2 gigaoctet Vérifiée Planifiée",
    ]);
    expect(backups[8]).toBe("900 mégaoctets Vérifiée Manuelle Marquée à conserver");
    // The totals row: how many the server retained, never a count of the page.
    expect(backups[9]).toBe("8 sauvegardes");
    expect(instants(page)[0]).toBe("2026-06-03T01:00:00Z");
  });

  it("ask the most recent first unasked, and the column of the contract the address sorts by, each both ways [WF-IHM-0060-A]", async () => {
    const page = rendered(await BackupsPage(searched()));
    expect(sortable(page, "Sauvegardes")).toEqual([
      "Date",
      "Taille",
      "Vérification",
      "Déclenchement",
      "Conservation",
    ]);
    expect(page).toContain('aria-sort="descending"');
    expect(queriesOf("GET /backups")).toEqual([NEWEST_BACKUPS]);
    server.clients = [];
    server.answers = { ...server.answers, "GET /backups": "backups_by_size" };
    const bySize = rendered(await BackupsPage(searched({ sort_by: "size_bytes" })));
    expect(queriesOf("GET /backups")).toEqual([{ sort_by: "size_bytes", sort_order: "asc" }]);
    // The rows as the server ordered them: the lightest, the manual one of January, first.
    expect(rows(bySize, "Sauvegardes")[1]).toContain("900 mégaoctets Vérifiée Manuelle");
    server.clients = [];
    await BackupsPage(searched({ sort_by: "verification", sort_order: "desc" }));
    await BackupsPage(searched({ sort_by: "origin" }));
    await BackupsPage(searched({ sort_by: "is_retained", sort_order: "desc" }));
    await BackupsPage(searched({ sort_by: "label" }));
    expect(queriesOf("GET /backups")).toEqual([
      { sort_by: "verification", sort_order: "desc" },
      { sort_by: "origin", sort_order: "asc" },
      { sort_by: "is_retained", sort_order: "desc" },
      NEWEST_BACKUPS,
    ]);
  });

  it("ask the server for the filters and the page the address names, under the names of the contract, and offer each filter [WF-IHM-0130-A]", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_period" };
    const page = rendered(
      await BackupsPage(
        searched({
          from: "2026-05-31T22:00:00Z",
          to: "2026-06-30T22:00:00Z",
          origins: "scheduled,manual,nothing",
          verifications: "failed,passed",
          is_retained: "false",
          size_bytes_min: "1000000000",
          size_bytes_max: "1300000000",
          offset: "50",
        }),
      ),
    );
    expect(queriesOf("GET /backups")).toEqual([
      {
        ...NEWEST_BACKUPS,
        offset: "50",
        from: "2026-05-31T22:00:00Z",
        to: "2026-06-30T22:00:00Z",
        origins: "manual,scheduled",
        verifications: "passed,failed",
        is_retained: "false",
        size_bytes_min: "1000000000",
        size_bytes_max: "1300000000",
      },
    ]);
    // The totals row counts what the server retained of the filtered list.
    expect(rows(page, "Sauvegardes").at(-1)).toBe("3 sauvegardes");
    expect(page).toContain('aria-label="Période des sauvegardes"');
    expect(page).toContain('aria-label="Filtrer par déclenchement"');
    expect(page).toContain('aria-label="Filtrer par vérification"');
    expect(page).toContain('aria-label="Bornes des sauvegardes"');
    expect(page).toContain('<option value="false" selected="">Soumises à la rotation</option>');
    expect(text(page)).toContain("Conservation Toutes les sauvegardes Marquées à conserver");
  });

  it("ask nothing of an address whose values no server could take", async () => {
    await BackupsPage(
      searched({
        from: "yesterday",
        to: "2026-13-45T25:00Z",
        origins: "cloud",
        verifications: "maybe",
        is_retained: "1",
        size_bytes_min: "-1",
        size_bytes_max: "1.5",
        offset: "-3",
      }),
    );
    expect(queriesOf("GET /backups")).toEqual([NEWEST_BACKUPS]);
  });

  it("say a period the API refuses at the field of its end, the list unread and the filters kept to be changed [WF-IHM-0130-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /backups": {
        problem: example("backups_period_inverted") as Problem & { status: 422 },
      },
    };
    const page = rendered(
      await BackupsPage(searched({ from: "2026-06-03T14:00:00Z", to: "2026-06-01T00:00:00Z" })),
    );
    expect(text(page)).toContain("La liste n’est pas lue : le serveur refuse la période demandée.");
    expect(page).not.toContain("<table");
    expect(page).toContain('aria-label="Période des sauvegardes"');
    const fields = page.match(/<input[^>]*type="date"[^>]*>/g) ?? [];
    expect(fields.map((field) => field.includes('aria-invalid="true"'))).toEqual([false, true]);
    expect(text(page)).toContain("La fin de la période ne peut précéder son début.");
    // The command that starts a backup is offered all the same; the pages of a list unread are not.
    expect(buttons(page)).toContain("Sauvegarder maintenant");
    expect(text(page)).not.toContain("Page précédente");
  });

  it("say a size at most below the least the API refuses at its field, the least named [WF-IHM-0130-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /backups": {
        problem: example("backups_bounds_inverted") as Problem & { status: 422 },
      },
    };
    const page = rendered(
      await BackupsPage(searched({ size_bytes_min: "1300000000", size_bytes_max: "1000000000" })),
    );
    expect(text(page)).toContain(
      "La liste n’est pas lue : le serveur refuse les bornes demandées.",
    );
    expect(page).not.toContain("<table");
    const fields = page.match(/<input[^>]*inputMode="decimal"[^>]*>/g) ?? [];
    expect(fields.map((field) => field.includes('aria-invalid="true"'))).toEqual([false, true]);
    // Both bounds keep what was asked, to be changed where the API refused them.
    expect(fields.map((field) => /value="(\d*)"/.exec(field)?.[1])).toEqual([
      "1300000000",
      "1000000000",
    ]);
    expect(text(page)).toContain(
      "La borne supérieure ne peut précéder la borne inférieure, 1 300 000 000.",
    );
  });

  it("offer a session that may modify the backups to start one, and on each backup the commands it lists, none that deletes [WF-ADM-0100-A]", async () => {
    shown.path = "/admin/backups";
    const page = rendered(await BackupsPage(searched()));
    expect(rows(page, "Sauvegardes")[0]).toBe(
      "Date Taille Vérification Déclenchement Conservation Téléchargement Restauration",
    );
    expect(buttons(page).filter((name) => name === "Sauvegarder maintenant")).toHaveLength(1);
    expect(buttons(page).filter((name) => name === "Conserver")).toHaveLength(7);
    expect(buttons(page).filter((name) => name === "Ne plus conserver")).toHaveLength(1);
    expect(buttons(page).filter((name) => name === "Restaurer")).toHaveLength(8);
    expect(links(page)).toContain(
      "/admin/backups/01926f3a-7c00-7000-8000-000000000907/content?from=%2Fadmin%2Fbackups",
    );
    expect(text(page)).not.toMatch(/Supprimer/);
    expect(text(page)).toContain("Maquette : le service simulé répond à chaque écriture");
    // The schedule set by its form, from the locations the installation declares (EP-14/L43d).
    expect(buttons(page).filter((name) => name === "Modifier la planification")).toHaveLength(1);
    expect(queriesOf("GET /external-backup-locations")).toEqual([{}]);
  });

  it("offer no command of the backups to a session whose backups list none, nor say the fake back keeps nothing, and no start to one that may not modify them [WF-IHM-0090-A]", async () => {
    withdrawn.permissions = ["backups.write"];
    server.answers = { ...server.answers, "GET /backups": "backups_reader" };
    const page = rendered(await BackupsPage(searched()));
    expect(rows(page, "Sauvegardes")[0]).toBe(
      "Date Taille Vérification Déclenchement Conservation",
    );
    expect(text(page)).toContain(
      "Planification État Active Fréquence Quotidienne Heure 01:00 UTC Rétention 7 sauvegardes conservées",
    );
    // The filters and the choice of the columns alone: readings, which write nothing of the
    // backups — no start, no marking, no restoration.
    expect(buttons(page)).toEqual([
      "Filtrer",
      "Tous les déclenchements",
      "Manuelle",
      "Planifiée",
      "Toutes les vérifications",
      "Vérification en attente",
      "Vérifiée",
      "Vérification échouée",
      "Filtrer",
      "Colonnes",
      "Date",
      "Taille",
      "Vérification",
      "Déclenchement",
      "Conservation",
    ]);
    expect(links(page)).toEqual([]);
    expect(text(page)).not.toContain("Maquette");
    // No form of the schedule, and no reading of the locations it alone needs.
    expect(queriesOf("GET /external-backup-locations")).toEqual([]);
  });

  it("present the restoration unavailable on each backup while a backup runs, as the backups list it [WF-IHM-0090-A]", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_during_backup" };
    const page = rendered(await BackupsPage(searched()));
    const restores = [...page.matchAll(/<button[^>]*aria-label="Restaurer[^"]*"[^>]*>/g)].map(
      (match) => match[0],
    );
    expect(restores).toHaveLength(8);
    expect(restores.every((button) => button.includes('aria-disabled="true"'))).toBe(true);
    expect(text(page)).toContain("Condition non remplie : aucune sauvegarde en cours.");
    expect(links(page)).toHaveLength(8);
  });

  it("say above the list the refusal of a download the route came back with", async () => {
    shown.path = "/admin/backups";
    const page = rendered(
      await BackupsPage(
        searched({
          refused_backup: "01926f3a-7c00-7000-8000-000000000907",
          refusal: "403:PERMISSION_MISSING",
        }),
      ),
    );
    expect(page).toContain('role="alert"');
    expect(text(page)).toContain("Vous n’avez pas la permission nécessaire. Fermer l’avis");
    expect(queriesOf("GET /backups")).toEqual([NEWEST_BACKUPS]);
  });

  it("present the external copy of the scheduled backups, the location by the name the installation declares", async () => {
    // The screen reads the copy the schedule sets, by the name of its location.
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

  it("say there is none yet, once, and offer to start one all the same; a filter that retains none keeps the filters", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_empty" };
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toMatch(/Sauvegardes Sauvegarder maintenant Aucune sauvegarde\.$/);
    expect(page).not.toContain('aria-label="Sauvegardes" role="grid"');
    expect(buttons(page)).toEqual(["Modifier la planification", "Sauvegarder maintenant"]);
    const narrowed = rendered(await BackupsPage(searched({ origins: "manual" })));
    expect(text(narrowed)).not.toContain("Aucune sauvegarde.");
    expect(narrowed).toContain('aria-label="Filtrer par déclenchement"');
    expect(text(narrowed)).toMatch(/Taille \(octets\) min\. max\. Filtrer Aucune sauvegarde$/);
  });

  it("say a page asked beyond the end of the list is no empty list, and lead back to its last page", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_beyond" };
    shown.path = "/admin/backups";
    const page = rendered(await BackupsPage(searched({ offset: "50" })));
    expect(queriesOf("GET /backups")).toEqual([{ ...NEWEST_BACKUPS, offset: "50" }]);
    expect(text(page)).not.toContain("Aucune sauvegarde.");
    expect(page).not.toContain('role="grid"');
    expect(text(page)).toContain(
      "8 sauvegardes Cette page est au-delà de la fin de la liste. Page précédente",
    );
    expect(links(page)).toEqual(["/admin/backups"]);
  });
});
