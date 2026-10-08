// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the journal of audit (FBS-1.5, WF-SEC-0030), as the address carries them, under
 * the names of the contract (`listAuditEvents`): the period — `from` included, `to` excluded, two
 * instants —, the author (`user_id`), whether an account or the platform acted (`actor_kind`), the
 * actions (`actions`, a list), the project (`project_id`), and the nature and the identifier of the
 * object (`object_kind`, `object_id`) — the history of one object. The page reads them and asks the
 * API with them; a filter chosen only changes the address, back to the first page. The server
 * filters, never the front (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { components, operations } from "@/api/generated/schema";
import { readValues } from "@/components/grid/filters";
import { CONTRACT_ADDRESS, OFFSET, pagedList } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";
import type { PagedList } from "@/navigation/pages";

/** An action the journal records, as the contract names it. */
export type AuditAction = components["schemas"]["AuditAction"];

/** Who acted: an account, or the platform. */
export type AuditActorKind = components["schemas"]["AuditActorKind"];

/** The nature of the object of an inscription. */
export type AuditObjectKind = components["schemas"]["AuditObjectKind"];

/** What the page asks `listAuditEvents`, besides nothing: the query of the contract. */
export type AuditQuery = NonNullable<operations["listAuditEvents"]["parameters"]["query"]>;

/** The parameters of the address, as the contract names them. */
export const FROM = "from";
export const TO = "to";
export const USER = "user_id";
export const ACTOR_KIND = "actor_kind";
export const ACTIONS = "actions";
export const PROJECT = "project_id";
export const OBJECT_KIND = "object_kind";
export const OBJECT = "object_id";

/** The parameter of the page of the journal, which every filter takes back to its first. */
export const AUDIT_PAGE = OFFSET;

/** The journal, its sort and every filter of it. */
export const AUDIT_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  FROM,
  TO,
  USER,
  ACTOR_KIND,
  ACTIONS,
  PROJECT,
  OBJECT_KIND,
  OBJECT,
);

/**
 * Each value of an enumeration of the contract, in its order: a record typed on the enumeration, so
 * that a value the contract adds is a fault of typing until it is listed here.
 */
const EVERY_ACTION: Readonly<Record<AuditAction, null>> = {
  revision_mark: null,
  reference_designate: null,
  amendment_merge: null,
  risk_occurrence: null,
  project_exit: null,
  cost_line_exclude: null,
  cost_line_reinstate: null,
  import_apply: null,
  user_create: null,
  user_update: null,
  user_deactivate: null,
  user_reactivate: null,
  password_link_create: null,
  access_role_create: null,
  access_role_update: null,
  access_role_delete: null,
  user_access_roles_set: null,
  backup: null,
  restore: null,
};
const EVERY_ACTOR_KIND: Readonly<Record<AuditActorKind, null>> = { user: null, platform: null };
const EVERY_OBJECT_KIND: Readonly<Record<AuditObjectKind, null>> = {
  project: null,
  revision: null,
  cost_structure: null,
  risk: null,
  cost_line: null,
  import: null,
  user: null,
  access_role: null,
  backup: null,
  external_backup_upload: null,
};

/** The actions of the contract, in its order: that of WF-SEC-0030. */
export const AUDIT_ACTIONS = Object.keys(EVERY_ACTION) as readonly AuditAction[];

/** The authors of the contract, in its order. */
export const ACTOR_KINDS = Object.keys(EVERY_ACTOR_KIND) as readonly AuditActorKind[];

/** The natures of the objects of the contract, in its order. */
export const OBJECT_KINDS = Object.keys(EVERY_OBJECT_KIND) as readonly AuditObjectKind[];

/** The filters of the journal the address asks, each as the contract takes it, or none. */
export interface AuditFilters {
  readonly from: string | undefined;
  readonly to: string | undefined;
  readonly user: string | undefined;
  /** The authors the address names: none, or both, is every author. */
  readonly actorKinds: readonly AuditActorKind[];
  /** The actions the address names, in the order of the contract: none is every action. */
  readonly actions: readonly AuditAction[];
  readonly project: string | undefined;
  readonly objectKind: AuditObjectKind | undefined;
  readonly object: string | undefined;
}

/** An identifier as the contract writes it (`Uuid`): the API refuses any other. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** An identifier the address names under a parameter, if the API may take it. */
function uuidOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && UUID.test(value) ? value : undefined;
}

/**
 * An instant as the contract writes it (`date-time` of RFC 3339): the date, the time, the zone —
 * each field caught to be bounded.
 */
const INSTANT =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(?:Z|[+-](\d{2}):(\d{2}))$/;

/** The days of a month of a year, the last of February included in a leap year. */
function daysIn(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/** The lowest value of each field of an instant after its year, from the month to the zone. */
const LOWEST = [1, 1, 0, 0, 0, 0, 0];

/**
 * Whether a text is an instant the contract takes: its form, and each field within its bounds —
 * a month of the year, a day of that month, an hour up to 23, minutes and seconds up to 59, a
 * zone of 23 hours and 59 minutes at most.
 */
function isInstant(value: string): boolean {
  const fields = INSTANT.exec(value);
  if (fields === null) {
    return false;
  }
  // A field the text leaves out — the seconds, the zone of `Z` — is nought.
  const [year = 0, ...rest] = fields
    .slice(1)
    .map((field: string | undefined) => Number(field ?? 0));
  const highest = [12, daysIn(year, rest[0] ?? 0), 23, 59, 59, 23, 59];
  return rest.every((field, at) => field >= (LOWEST[at] ?? 0) && field <= (highest[at] ?? 0));
}

/** An instant the address names under a parameter, if the API may take it. */
function instantOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && isInstant(value) ? value : undefined;
}

/**
 * Read the filters the address asks of the journal: what the contract would refuse — an instant
 * that is none, an identifier no server knows, a value of no enumeration — is not asked.
 */
export function readAuditFilters(search: SearchParameters): AuditFilters {
  const kind = search.get(OBJECT_KIND);
  return {
    from: instantOf(search, FROM),
    to: instantOf(search, TO),
    user: uuidOf(search, USER),
    actorKinds: readValues(search, ACTOR_KIND, ACTOR_KINDS),
    actions: readValues(search, ACTIONS, AUDIT_ACTIONS),
    project: uuidOf(search, PROJECT),
    objectKind: OBJECT_KINDS.find((each) => each === kind),
    object: uuidOf(search, OBJECT),
  };
}

/** Whether the filters narrow the journal: an empty journal so narrowed is no empty journal. */
export function narrows(filters: AuditFilters): boolean {
  return (
    filters.from !== undefined ||
    filters.to !== undefined ||
    filters.user !== undefined ||
    filters.actorKinds.length === 1 ||
    filters.actions.length > 0 ||
    filters.project !== undefined ||
    filters.objectKind !== undefined ||
    filters.object !== undefined
  );
}

/**
 * The query of the contract for the filters, the direction of the sort of the dates and the page:
 * only what narrows is sent — one author kind, not both —, the server's defaults standing for the
 * rest: the most recent first, the first page.
 */
export function auditQuery(
  filters: AuditFilters,
  order: AuditQuery["sort_order"],
  offset: number | undefined,
): AuditQuery {
  const [actorKind, other] = filters.actorKinds;
  return {
    ...(offset === undefined ? {} : { offset }),
    ...(filters.from === undefined ? {} : { from: filters.from }),
    ...(filters.to === undefined ? {} : { to: filters.to }),
    ...(filters.user === undefined ? {} : { user_id: filters.user }),
    ...(actorKind === undefined || other !== undefined ? {} : { actor_kind: actorKind }),
    ...(filters.actions.length === 0 ? {} : { actions: [...filters.actions] }),
    ...(filters.project === undefined ? {} : { project_id: filters.project }),
    ...(filters.objectKind === undefined ? {} : { object_kind: filters.objectKind }),
    ...(filters.object === undefined ? {} : { object_id: filters.object }),
    ...(order === undefined ? {} : { sort_order: order }),
  };
}

/**
 * The address of the same screen with some filters set — or lifted, for none —, the rest of its
 * query kept, back to the first page of the journal.
 */
export function auditHref(
  pathname: string,
  query: URLSearchParams,
  changes: Readonly<Record<string, string | undefined>>,
): string {
  const next = new URLSearchParams(query);
  next.delete(AUDIT_PAGE);
  for (const [name, value] of Object.entries(changes)) {
    if (value === undefined || value === "") {
      next.delete(name);
    } else {
      next.set(name, value);
    }
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/**
 * The address of the history of an object: the journal filtered on its nature and its identifier,
 * every other filter lifted — its whole history, whoever acted, whatever the action, the project
 * or the period (decision of the review of EP-02/L41e) —, its sort kept, back to its first page.
 */
export function historyHref(
  pathname: string,
  query: URLSearchParams,
  object: { readonly kind: AuditObjectKind; readonly object_id: string },
): string {
  return auditHref(pathname, query, {
    [FROM]: undefined,
    [TO]: undefined,
    [USER]: undefined,
    [ACTOR_KIND]: undefined,
    [ACTIONS]: undefined,
    [PROJECT]: undefined,
    [OBJECT_KIND]: object.kind,
    [OBJECT]: object.object_id,
  });
}
