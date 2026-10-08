// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The journal of audit (FBS-1.5, WF-SEC-0030), outside any project: a page of the inscriptions the
 * server retains, each with its date, its author, its action, its object and its project as the
 * inscription keeps them — the object and the project links where the session may consult them
 * (WF-ADM-0110) —, on a dense grid read only, sorted by date, the most recent first unless the
 * address asks otherwise, filtered and paged by the server as the address asks, under the names of
 * the contract (`from`, `to`, `user_id`, `actor_kind`, `actions`, `project_id`, `object_kind`,
 * `object_id`, `sort_order`, `offset`). The journal of a project terminated long ago is read by the
 * same filter as that of a project in progress. Nothing modifies nor deletes an inscription: the
 * screen offers no command.
 *
 * The screen is the consultation of the journal (`audit_log.read`): a session without it finds it
 * not found, as an address that leads nowhere (WF-ADM-0110). The authors are offered from the
 * accounts, for a session that may read them (`users.read`); the projects, from those the session
 * may open (`listProjects`), which its links lead to. A period that ends before it starts, which
 * the API refuses (422), is said in place of the inscriptions, the filters kept to be changed; any
 * other read the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";

import { readEveryPage } from "@/api/every-page";
import { type Problem, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  AUDIT_LIST,
  type AuditFilters,
  auditQuery,
  narrows,
  readAuditFilters,
} from "@/components/audit/audit-address";
import {
  AUDIT_GRID_KEY,
  AUDIT_SORTS,
  type AuditEvent,
  type AuditPage,
  type AuditSort,
  NEWEST_FIRST,
} from "@/components/audit/audit-columns";
import {
  type AuthorChoice,
  AuditFilterBar,
  type ProjectChoice,
} from "@/components/audit/audit-filters";
import { AuditGrid } from "@/components/audit/audit-grid";
import { ListPages } from "@/components/grid/list-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, type GridSort, readGridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { PROJECT_STATES } from "@/navigation/home";
import { problemMessage } from "@/i18n/problem";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { type Permission, requestSession, type Session } from "@/session/request";

import { screenMetadata } from "../../title";

/** The refusal of filters the server cannot apply — a period inverted (`listAuditEvents`, 422). */
const FILTERS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.auditLog");
}

/** The title of the screen, and how many inscriptions the filters retain. */
function AuditHeader({ count }: { readonly count: number | undefined }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.auditLog")}
      icon={FUNCTION_ICONS.audit_log}
      density={FUNCTION_DENSITY.audit_log}
      subtitle={count === undefined ? undefined : t("admin.auditLog.count", { count })}
    />
  );
}

/**
 * The accounts that may have acted, by their names, deactivated ones included (WF-ADM-0060): every
 * page of them, for a session that may read them; none otherwise.
 */
async function readAuthors(permissions: readonly Permission[]): Promise<AuthorChoice[]> {
  if (!permissions.includes("users.read")) {
    return [];
  }
  const users = await readEveryPage("listUsers", (page) =>
    serverClient().GET("/users", {
      params: { query: { ...page, include_inactive: true, sort_by: "last_name" } },
    }),
  );
  return users.map((user) => ({
    id: user.user_id,
    firstName: user.first_name,
    lastName: user.last_name,
  }));
}

/** The projects the session may open, in every state: every page of them. */
async function readProjects(): Promise<ProjectChoice[]> {
  const projects = await readEveryPage("listProjects", (page) =>
    serverClient().GET("/projects", {
      params: { query: { ...page, states: [...PROJECT_STATES], sort_by: "code" } },
    }),
  );
  return projects.map((project) => ({
    id: project.project_id,
    code: project.code,
    label: project.label,
  }));
}

/**
 * The names the inscriptions shown give what the address names: the author, the project, the
 * object whose history is asked — for a filter whose choices do not offer it.
 */
function namedBy(events: readonly AuditEvent[], filters: AuditFilters) {
  const actor = events.find((event) => event.actor.user_id === filters.user)?.actor;
  const project = events.find((event) => event.project?.project_id === filters.project)?.project;
  const object = events.find((event) => event.object.object_id === filters.object)?.object;
  return {
    user: actor?.display_name,
    project: project ?? undefined,
    object: object === undefined ? undefined : { label: object.label, kind: object.kind },
  };
}

/** A page of the journal, as the contract gives it. */
interface Journal {
  readonly items: readonly AuditEvent[];
  readonly meta: AuditPage;
}

/**
 * A page of the inscriptions the filters retain, in the direction of the sort asked, from the place
 * the address asks; or the envelope of the filters the API refuses (422).
 */
async function readJournal(
  filters: AuditFilters,
  order: GridSort<AuditSort>["order"] | undefined,
  offset: number | undefined,
): Promise<{ readonly journal: Journal } | { readonly refused: Problem }> {
  const read = await readOrRefused("listAuditEvents", FILTERS_REFUSED, () =>
    serverClient().GET("/audit-events", { params: { query: auditQuery(filters, order, offset) } }),
  );
  return read.kind === "read" ? { journal: read.data } : { refused: read.problem };
}

/**
 * Whether the API refuses a period that ends before it starts — the end pointed at as out of range,
 * as the contract declares it —, rather than another of the filters.
 */
function refusesPeriod(problem: Problem): boolean {
  return (problem.fields ?? []).some(
    (field) => field.pointer === "/query/to" && field.code === "VALUE_OUT_OF_RANGE",
  );
}

/** Why the screen reads no inscription, in place of them: the filters above stay to be changed. */
function Refused({ problem }: { readonly problem: Problem }) {
  const t = useTranslations("admin.auditLog");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <p className="text-sm text-muted-foreground">
      {refusesPeriod(problem) ? t("periodRefused") : problemMessage(problem, { locale, messages })}
    </p>
  );
}

/**
 * The inscriptions of the page on their grid, and the way through the pages; or, in their place,
 * that the journal holds none, nothing narrowing it.
 */
function Inscriptions({
  journal,
  narrowed,
  query,
  preferences,
  openable,
}: {
  readonly journal: Journal;
  readonly narrowed: boolean;
  readonly query: GridQuery<AuditSort>;
  readonly preferences: GridPreferences | undefined;
  readonly openable: readonly string[];
}) {
  const t = useTranslations("admin.auditLog");
  if (journal.meta.total === 0 && !narrowed) {
    return <p className="text-sm text-muted-foreground">{t("none")}</p>;
  }
  return (
    <>
      <AuditGrid
        events={journal.items}
        page={journal.meta}
        query={query}
        preferences={preferences}
        openable={openable}
      />
      <ListPages
        list={AUDIT_LIST}
        texts="admin.pages"
        page={journal.meta}
        shown={journal.items.length}
      />
    </>
  );
}

/**
 * What the session reads of the journal: its permissions, and the settings it keeps for the grid;
 * not found to a session that may not consult the journal (WF-ADM-0110).
 */
function consultation(session: Session | undefined) {
  const permissions = session?.permissions ?? [];
  if (!permissions.includes("audit_log.read")) {
    notFound();
  }
  return {
    permissions,
    preferences: session?.user.display_preferences?.grids?.[AUDIT_GRID_KEY] ?? undefined,
  };
}

/** Render the page of the journal the address asks for, its filters, its grid and its pages. */
export default async function AuditLogPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const { permissions, preferences } = consultation(session);
  // The address is the truth; then the sort the account keeps; then the server's: newest first.
  const query = readGridQuery(search, AUDIT_SORTS, preferences?.sort ?? NEWEST_FIRST);
  const filters = readAuditFilters(search);
  const [read, users, projects] = await Promise.all([
    readJournal(filters, query.sort?.order, offsetOf(search.get(OFFSET_PARAMETER))),
    readAuthors(permissions),
    readProjects(),
  ]);
  const journal = "journal" in read ? read.journal : undefined;
  return (
    <Screen density={FUNCTION_DENSITY.audit_log} fill>
      {/* The filters, the grid and the pages compose the changes they make to the address. */}
      <PendingAddress>
        <AuditHeader count={journal?.meta.total} />
        <AuditFilterBar
          filters={filters}
          users={users}
          projects={projects}
          named={namedBy(journal?.items ?? [], filters)}
        />
        {"refused" in read ? (
          <Refused problem={read.refused} />
        ) : (
          <Inscriptions
            journal={read.journal}
            narrowed={narrows(filters)}
            query={query}
            preferences={preferences}
            openable={projects.map((project) => project.id)}
          />
        )}
      </PendingAddress>
    </Screen>
  );
}
