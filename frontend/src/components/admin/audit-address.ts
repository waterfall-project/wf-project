// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the accounts and of the access roles read of their address for the audit
 * columns of their tables (WF-DAT-0070, US-0360/L4, #936): each column of dates filtered on a period,
 * each column of authors on its author (WF-IHM-0130), under the names of the contract the two lists
 * share — `created_at_from` and `created_at_to`, `updated_at_from` and `updated_at_to`, two instants,
 * the start included and the end excluded, drawn from local days (`period.ts`, `day`); and
 * `created_by_user_id` or `created_by_kind`, `updated_by_user_id` or `updated_by_kind` — an account,
 * deactivated or anonymised included, or whether an account or the platform wrote the row. A filter
 * chosen only changes the address, and the page reads anew: the server filters, never the front.
 *
 * Pure, and neither server nor client: the pages read, the filters write.
 */
import type { components, operations } from "@/api/generated/schema";
import {
  type Period,
  type PeriodNames,
  type PeriodRefusals,
  readPeriod,
  refusedPeriod,
} from "@/components/grid/period";
import { given, identifierOf } from "@/components/reference/address";
import type { SearchParameters } from "@/navigation/context";

/** Who wrote a row: an account, or the platform — an automatic process (WF-DAT-0070). */
export type ActorKind = components["schemas"]["AuditActorKind"];

/** The kinds of authors of the contract, in its order. */
export const ACTOR_KINDS: readonly ActorKind[] = ["user", "platform"];

/** The two audit columns of dates, and the two of authors, by what they say of a row. */
export type Written = "created" | "updated";

/** The audit columns, from the creation. */
export const WRITTEN: readonly Written[] = ["created", "updated"];

/** The parameters of the period of each column of dates, as the contract names them. */
export const PERIODS: Readonly<Record<Written, PeriodNames>> = {
  created: { from: "created_at_from", to: "created_at_to" },
  updated: { from: "updated_at_from", to: "updated_at_to" },
};

/** The parameters of the author of a column of authors: an account, or a kind of author. */
export interface AuthorNames {
  readonly user: string;
  readonly kind: string;
}

/** The parameters of the author of each column of authors, as the contract names them. */
export const AUTHORS: Readonly<Record<Written, AuthorNames>> = {
  created: { user: "created_by_user_id", kind: "created_by_kind" },
  updated: { user: "updated_by_user_id", kind: "updated_by_kind" },
};

/**
 * The parameters of the audit columns, which the grids of both screens keep with their settings
 * (WF-IHM-0060).
 */
export const AUDIT_FILTERS: readonly string[] = WRITTEN.flatMap((column) => [
  PERIODS[column].from,
  PERIODS[column].to,
  AUTHORS[column].user,
  AUTHORS[column].kind,
]);

/** The author the address filters a column on: an account, or a kind of author; none, any. */
export interface Author {
  readonly user: string | undefined;
  readonly kind: ActorKind | undefined;
}

/** The filters of the audit columns, as the address asks them, and what the API refused of them. */
export interface AuditFilters {
  readonly periods: Readonly<Record<Written, Period>>;
  readonly authors: Readonly<Record<Written, Author>>;
  /** The sides of each period the API refused (422); none when it read the list. */
  readonly refused?: Partial<Record<Written, PeriodRefusals>> | undefined;
  /**
   * The accounts the address chooses as authors that the page does not offer, read by their names
   * (`getUser`) — a deactivated one still named, an anonymised one by the neutral label
   * (WF-ADM-0060); one the API does not find stays chosen by its identifier.
   */
  readonly named?: readonly NamedAuthor[] | undefined;
}

/** An account by its identifier and its names: null once it is anonymised (WF-ADM-0060). */
export type NamedAuthor = Pick<
  components["schemas"]["User"],
  "user_id" | "first_name" | "last_name"
>;

/** A kind of author the address names, if the contract knows it. */
function kindOf(search: SearchParameters, name: string): ActorKind | undefined {
  const value = search.get(name);
  return ACTOR_KINDS.find((kind) => kind === value);
}

/**
 * The filters of the audit columns the address sets: a bound the contract would refuse — an instant
 * that is none —, an identifier of none, a kind it does not know, are not asked.
 */
export function readAuditFilters(search: SearchParameters): AuditFilters {
  const author = (column: Written): Author => ({
    user: identifierOf(search, AUTHORS[column].user),
    kind: kindOf(search, AUTHORS[column].kind),
  });
  return {
    periods: {
      created: readPeriod(search, "day", PERIODS.created),
      updated: readPeriod(search, "day", PERIODS.updated),
    },
    authors: { created: author("created"), updated: author("updated") },
  };
}

/** Whether the filters of the audit columns narrow the list. */
export function auditNarrowed(filters: AuditFilters): boolean {
  return WRITTEN.some(
    (column) =>
      filters.periods[column].from !== undefined ||
      filters.periods[column].to !== undefined ||
      filters.authors[column].user !== undefined ||
      filters.authors[column].kind !== undefined,
  );
}

/** What the filters of the audit columns ask the API, the same for both lists. */
export type AuditQuery = Pick<
  NonNullable<operations["listAccessRoles"]["parameters"]["query"]>,
  | "created_at_from"
  | "created_at_to"
  | "created_by_user_id"
  | "created_by_kind"
  | "updated_at_from"
  | "updated_at_to"
  | "updated_by_user_id"
  | "updated_by_kind"
>;

/** The query of the audit columns, as the address asks it, under the names of the contract. */
export function auditQuery(filters: AuditFilters): AuditQuery {
  const { created, updated } = filters.periods;
  const authors = filters.authors;
  return {
    ...given("created_at_from", created.from),
    ...given("created_at_to", created.to),
    ...given("created_by_user_id", authors.created.user),
    ...given("created_by_kind", authors.created.kind),
    ...given("updated_at_from", updated.from),
    ...given("updated_at_to", updated.to),
    ...given("updated_by_user_id", authors.updated.user),
    ...given("updated_by_kind", authors.updated.kind),
  };
}

/**
 * An account that wrote a row, as a choice of an author: its identifier and the name the row keeps
 * of it — kept after its deactivation, null once it is anonymised (WF-ADM-0060).
 */
export interface AuthorChoice {
  readonly id: string;
  readonly name: string | null;
}

/** The audit columns of a row, as the contract gives them. */
interface Audited {
  readonly audit: components["schemas"]["Audit"];
}

/**
 * The accounts that wrote the rows given — created them or last modified them —, each once, in the
 * order they first appear: the platform, which is no account, is a kind of author of its own.
 */
export function authorsOf(rows: readonly Audited[]): AuthorChoice[] {
  const found = new Map<string, AuthorChoice>();
  for (const { audit } of rows) {
    for (const actor of [audit.created_by, audit.updated_by]) {
      if (actor.user_id !== undefined && !found.has(actor.user_id)) {
        found.set(actor.user_id, { id: actor.user_id, name: actor.display_name ?? null });
      }
    }
  }
  return [...found.values()];
}

/**
 * The accounts the address chooses as authors of either column that are not among those offered,
 * each once: the page reads them by their names (`NamedAuthor`).
 */
export function unofferedAuthors(
  filters: AuditFilters,
  offered: readonly AuthorChoice[],
): string[] {
  const offeredIds = new Set(offered.map((author) => author.id));
  const chosen = WRITTEN.map((column) => filters.authors[column].user);
  return [...new Set(chosen.filter((id): id is string => id !== undefined && !offeredIds.has(id)))];
}

/**
 * The sides of each period the API refused (422, `VALIDATION_FAILED`), as the envelope points at
 * them (`/query/created_at_to`); none when it points at no side of either.
 */
export function refusedAudit(
  fields: readonly components["schemas"]["FieldProblem"][],
): AuditFilters["refused"] {
  const created = refusedPeriod(fields, PERIODS.created);
  const updated = refusedPeriod(fields, PERIODS.updated);
  return created === undefined && updated === undefined
    ? undefined
    : {
        ...(created === undefined ? {} : { created }),
        ...(updated === undefined ? {} : { updated }),
      };
}
