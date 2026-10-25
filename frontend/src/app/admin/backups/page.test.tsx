// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the backups (FBS-1.4, US-0250, US-0440, EP-14/L42h), rendered by the server against
 * the fake back: the list on the dense grid, its sort, its filters and its pages, the commands each
 * backup lists, the schedule and its form, the deposit of a backup of another installation, and the
 * refusal of a download the route came back with. Out of the tests of the other screens of the
 * administration (`../pages.test.tsx`), which it shares the readers of the markup with
 * (`@/test/markup`).
 */
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { buttons, instants, links, rows, sortable, text } from "@/test/markup";
import { queryOfCall } from "@/test/queries";

import BackupsPage, { generateMetadata as backupsMetadata } from "./page";

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
const shown = vi.hoisted(() => ({ path: "/admin/backups" }));

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => shown.path,
  useSearchParams: () => new URLSearchParams(),
}));
// The session of the contract, some of its permissions withdrawn for a test: no example lacks the
// modification of the backups alone, and one would ripple through the accounts, the roles and the
// journal of the witness.
// The sizes of pages the account keeps, set for a test.
const kept = vi.hoisted((): { grids: Record<string, { page_size: number }> } => ({ grids: {} }));
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
            display_preferences: {
              ...session.display_preferences,
              grids: { ...session.display_preferences?.grids, ...kept.grids },
            },
            permissions: session.permissions.filter(
              (permission) => !withdrawn.permissions.includes(permission),
            ),
          };
    },
  };
});
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

/** Render the screen of the backups in French, within the shell that follows the tasks. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>{page as ReactNode}</TaskTracker>
    </NextIntlClientProvider>,
  );
}

/** The search parameters of an address. */
function searched(search: PageSearchParams = {}) {
  return { searchParams: Promise.resolve(search) };
}

/** The queries of the calls the page made to an operation. */
function queriesOf(route: string) {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => queryOfCall(call.query));
}

beforeEach(() => {
  kept.grids = {};
  withdrawn.permissions = [];
  shown.path = "/admin/backups";
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /backups": "backups",
    "GET /backup-schedule": "backup_schedule",
    "GET /external-backup-locations": "external_backup_locations",
  };
});

const NEWEST_BACKUPS = { sort_by: "taken_at", sort_order: "desc" };

describe("the backups", () => {
  it("title the tab with the function", async () => {
    expect((await backupsMetadata()).title).toBe("Sauvegarde et restauration — Waterfall");
  });

  it("present each backup with its date, its size and its verification [WF-ADM-0150-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_auditor",
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
    // Wired to the service of EP-03, the screen says nothing of the fake back.
    expect(text(page)).not.toContain("Maquette");
    // The schedule set by its form, from the locations the installation declares (EP-14/L43d).
    expect(buttons(page).filter((name) => name === "Modifier la planification")).toHaveLength(1);
    expect(queriesOf("GET /external-backup-locations")).toEqual([{}]);
  });

  it("offer no command of the backups to a session whose backups list none, and no start to one that may not modify them [WF-IHM-0090-A]", async () => {
    withdrawn.permissions = ["backups.write", "platform_restore"];
    server.answers = { ...server.answers, "GET /backups": "backups_reader" };
    const page = rendered(await BackupsPage(searched()));
    expect(rows(page, "Sauvegardes")[0]).toBe(
      "Date Taille Vérification Déclenchement Conservation",
    );
    expect(text(page)).toContain(
      "Planification État Active Fréquence Quotidienne Heure 01:00 UTC Rétention 7 sauvegardes conservées",
    );
    // The filters and the choice of the columns alone: readings, which write nothing of the
    // backups — no start, no marking, no restoration, no deposit.
    expect(buttons(page)).toEqual([
      "Aide",
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

  it("list the backups and offer their commands without the schedule nor the locations the API does not find [WF-ADM-0150-A]", async () => {
    // The service answers 404 to the schedule and to the locations until it serves them (EP-13).
    server.answers = {
      ...server.answers,
      "GET /backup-schedule": NOT_FOUND,
      "GET /external-backup-locations": NOT_FOUND,
    };
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).not.toContain("Planification");
    expect(rows(page, "Sauvegardes")[1]).toContain("1,2 gigaoctet Vérifiée Planifiée");
    expect(buttons(page)).toContain("Sauvegarder maintenant");
    expect(buttons(page)).toContain("Déposer");
    expect(links(page)).toHaveLength(8);
  });

  it("present the download and the restoration of a backup not verified unavailable, with the condition it lacks, as the backups list it [WF-IHM-0090-A]", async () => {
    server.answers = { ...server.answers, "GET /backups": "backups_unverified" };
    const page = rendered(await BackupsPage(searched()));
    const restores = [...page.matchAll(/<button[^>]*aria-label="Restaurer[^"]*"[^>]*>/g)].map(
      (match) => match[0],
    );
    expect(restores.map((button) => button.includes('aria-disabled="true"'))).toEqual([
      true,
      true,
      false,
    ]);
    expect(text(page)).toContain("Condition non remplie : sauvegarde vérifiée.");
    // The verified one alone is downloaded, by the route of the front that hands it on.
    expect(links(page)).toEqual([
      "/admin/backups/01926f3a-7c00-7000-8000-000000000906/content?from=%2Fadmin%2Fbackups",
    ]);
  });

  it("offer the deposit of a backup of another installation to a session that may restore the platform, and none to one that may not [WF-ADM-0100-A]", async () => {
    const page = rendered(await BackupsPage(searched()));
    expect(text(page)).toContain(
      "Restaurer une sauvegarde d’une autre installation Déposez l’archive d’une sauvegarde",
    );
    expect(page).toContain('aria-label="Restaurer une sauvegarde d’une autre installation"');
    withdrawn.permissions = ["platform_restore"];
    const withheld = rendered(await BackupsPage(searched()));
    expect(text(withheld)).not.toContain("Restaurer une sauvegarde d’une autre installation");
    expect(buttons(withheld)).not.toContain("Déposer");
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
    expect(text(page)).toMatch(
      /Sauvegardes Sauvegarder maintenant Aucune sauvegarde\. Restaurer une sauvegarde d’une autre installation/,
    );
    expect(text(page).split("Aucune sauvegarde").length - 1).toBe(1);
    expect(page).not.toContain('aria-label="Sauvegardes" role="grid"');
    expect(buttons(page)).toEqual([
      "Aide",
      "Modifier la planification",
      "Sauvegarder maintenant",
      "Déposer",
    ]);
    const narrowed = rendered(await BackupsPage(searched({ origins: "manual" })));
    expect(text(narrowed)).not.toContain("Aucune sauvegarde.");
    expect(narrowed).toContain('aria-label="Filtrer par déclenchement"');
    expect(text(narrowed)).toMatch(
      /Taille \(octets\) min\. max\. Filtrer Aucune sauvegarde Restaurer une sauvegarde/,
    );
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

describe("the backups, the size of the pages", () => {
  it.each([
    ["no preference", {}, "50"],
    ["a page size of 25", { limit: "25" }, "25"],
  ])("sends %s as the limit of its reading [WF-IHM-0060-A]", async (_name, search, limit) => {
    await BackupsPage(searched(search));
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /backups");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe(limit);
  });

  it("reads the page size kept by the account when the address asks none [WF-IHM-0060-A]", async () => {
    kept.grids = { backups: { page_size: 25 } };
    await BackupsPage(searched({}));
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /backups");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe("25");
  });
});
