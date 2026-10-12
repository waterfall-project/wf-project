// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the dense grid of the journal of audit (FBS-1.5, WF-SEC-0030), alone on its
 * screen, with the key of its settings in the account (WF-ADM-0040): each inscription with its
 * date, its author, its action, the nature and the label of its object, its project and the
 * correlation of the request that produced it — every name as the inscription keeps it, that of the
 * moment of the action —, and the link to the history of its object. Read only: no cell is entered,
 * and nothing modifies nor deletes an inscription. The server searches the inscriptions on the label
 * of their object (`search`).
 *
 * The server sorts the inscriptions both ways on each of their columns (WF-IHM-0060) — the action
 * and the nature in the order of their enumeration, not of their words —, by their dates unasked,
 * the most recent first. The journal is always sorted by one of them: its sort is never lifted — a
 * header goes from one direction to the other —, and the date header asks the most recent first,
 * as the server gives them unasked: from another sort, it takes the journal back to its order
 * unasked.
 *
 * The object and the project are links where the session may consult them (WF-ADM-0110): a project
 * the session may open — one `listProjects` lists —, and of its objects a revision, which has an
 * address, and an object that lives in a revision, in the revision the inscription names
 * (`AuditObject.revision`) — a risk, in the risks of the revision, its detail open; the import of a
 * planning, an estimate or a remaining to commit, in its exchanges, its report shown; the
 * differential of an amendment, among the cost structures the screen of the revisions shows of the
 * revision —; a line of actual cost and the import of actual costs
 * belong to the project and to no revision, and an account, a role or a backup has no screen of its
 * own: their names stand alone. The correlation is a link to the inscriptions of its request alone.
 *
 * Neither server nor client: the page reads the key and the column sorted; the grid, in the
 * browser, the rest — the functions that read a row never cross to the server.
 */
import { History } from "lucide-react";

import type { components } from "@/api/generated/schema";
import { type GridConfig, sortColumns } from "@/components/grid/columns";
import type { GridSort } from "@/components/grid/query";
import { importHref } from "@/components/exchanges/offers";
import { LocalTime } from "@/components/local-time";
import { RISK } from "@/components/risks/address";
import { REVISION_PARAMETER } from "@/navigation/context";
import { type FunctionPermission, readableGroups } from "@/navigation/functions";

import type { AuditSort } from "./audit-address";
export type { AuditSort };
import {
  ActionCell,
  ActorCell,
  CorrelationCell,
  HistoryCell,
  ObjectCell,
  ObjectKindCell,
  ProjectCell,
} from "./audit-cells";

/** An inscription of the journal, as the contract gives it. */
export type AuditEvent = components["schemas"]["AuditEvent"];

/** Where a page stands in the inscriptions the server retained: their number, the totals row's. */
export type AuditPage = components["schemas"]["PaginationMeta"];

/** A permission of the catalogue, as the session carries it. */
type PermissionCode = components["schemas"]["PermissionCode"];

/** The key of the settings of the grid in the account: stable. */
export const AUDIT_GRID_KEY = "audit_log";

/** The sort of the journal unasked, as the server gives it: the most recent first. */
export const NEWEST_FIRST: GridSort<AuditSort> = { column: "occurred_at", order: "desc" };

/**
 * What the session may consult of the projects, which says where the links of the grid lead
 * (WF-ADM-0110): the projects it may open, by their identifiers; the functions of a project it may
 * read, by their permissions; and whether it may read a function of a revision at all, which the
 * address of a revision leads to.
 */
export interface AuditReach {
  readonly openable: readonly string[];
  readonly functions: readonly FunctionPermission[];
  readonly revision: boolean;
}

/** What a session of these permissions may read of a project, given the projects it may open. */
export function auditReach(
  permissions: readonly PermissionCode[],
  openable: readonly string[],
): AuditReach {
  const readable = readableGroups(permissions).flatMap((group) => group.functions);
  return {
    openable,
    functions: [...new Set(readable.map((fn) => fn.permission))],
    revision: readable.some((fn) => fn.scope === "revision"),
  };
}

/** The address of a project the session may open, or none. */
function projectHref(projectId: string, reach: AuditReach): string | undefined {
  return reach.openable.includes(projectId) ? `/projects/${projectId}` : undefined;
}

/**
 * The screen of an object that lives in a revision, in that revision, where the session may read its
 * function: a risk, in the risks of the revision, its detail open (`risks.read`); the import of a
 * planning, an estimate or a remaining to commit, in the exchanges of the revision, its report shown
 * (`planning.read`); the differential of an amendment, among the cost structures of the revision, on
 * the screen of the revisions read in it (`revisions.read`). Otherwise the revision itself, which
 * leads to the first of its functions the session may read; none when it may read none.
 */
function inRevision(
  project: string,
  revision: string,
  object: AuditEvent["object"],
  reach: AuditReach,
): string | undefined {
  const path = `/projects/${project}/revisions`;
  const reads = (permission: FunctionPermission) => reach.functions.includes(permission);
  if (object.kind === "risk" && reads("risks")) {
    return `${path}/${revision}/risks?${new URLSearchParams({ [RISK]: object.object_id }).toString()}`;
  }
  if (object.kind === "import" && reads("planning")) {
    return importHref(`${path}/${revision}/exchanges`, object.object_id);
  }
  if (object.kind === "cost_structure" && reads("revisions")) {
    return `${path}?${new URLSearchParams({ [REVISION_PARAMETER]: revision }).toString()}`;
  }
  return reach.revision ? `${path}/${revision}` : undefined;
}

/**
 * The address of the object of an inscription, when it has one and the session may consult it:
 * a project it may open; a revision of such a project, or the screen of an object that lives in a
 * revision of it, in the revision the inscription names (`AuditObject.revision`).
 */
function objectHref(event: AuditEvent, reach: AuditReach): string | undefined {
  const { object, project } = event;
  if (object.kind === "project") {
    return projectHref(object.object_id, reach);
  }
  if (project === null || !reach.openable.includes(project.project_id)) {
    return undefined;
  }
  if (object.kind === "revision") {
    return reach.revision
      ? `/projects/${project.project_id}/revisions/${object.object_id}`
      : undefined;
  }
  return object.revision === null
    ? undefined
    : inRevision(project.project_id, object.revision.revision_id, object, reach);
}

/** The grid of the journal, its links leading to what the session may consult. */
export function auditGrid(reach: AuditReach): GridConfig<AuditEvent, AuditSort, AuditPage> {
  return {
    key: AUDIT_GRID_KEY,
    name: "auditLog",
    searched: true,
    lifts: false,
    rowKey: (event) => event.audit_event_id,
    columns: [
      {
        key: "occurred_at",
        label: "occurredAt",
        format: "text",
        width: 180,
        pinned: true,
        contract: "occurred_at",
        descendingFirst: true,
        value: (event) => event.occurred_at,
        render: (event) => <LocalTime value={event.occurred_at} />,
      },
      {
        key: "actor",
        label: "author",
        format: "text",
        width: 180,
        contract: "actor",
        value: (event) => event.actor.display_name ?? event.actor.kind,
        render: (event) => <ActorCell actor={event.actor} />,
      },
      {
        key: "action",
        label: "auditAction",
        format: "text",
        width: 250,
        contract: "action",
        value: (event) => event.action,
        render: (event) => <ActionCell action={event.action} />,
      },
      {
        key: "object_kind",
        label: "objectKind",
        format: "text",
        width: 170,
        contract: "object_kind",
        value: (event) => event.object.kind,
        render: (event) => <ObjectKindCell kind={event.object.kind} />,
      },
      {
        key: "object",
        label: "auditObject",
        format: "text",
        width: 260,
        contract: "object_label",
        value: (event) => event.object.label,
        render: (event) => <ObjectCell object={event.object} href={objectHref(event, reach)} />,
      },
      {
        key: "history",
        label: "objectHistory",
        format: "text",
        align: "center",
        width: 56,
        icon: History,
        value: () => null,
        render: (event) => <HistoryCell object={event.object} />,
      },
      {
        key: "project",
        label: "project",
        format: "text",
        width: 300,
        contract: "project",
        value: (event) => event.project?.code,
        render: (event) => (
          <ProjectCell
            project={event.project}
            href={event.project === null ? undefined : projectHref(event.project.project_id, reach)}
          />
        ),
      },
      {
        key: "correlation",
        label: "correlation",
        format: "text",
        width: 300,
        contract: "correlation_id",
        value: (event) => event.correlation_id,
        render: (event) => <CorrelationCell correlation={event.correlation_id} />,
      },
    ],
  };
}

/** The columns of the contract the server sorts the journal by. */
export const AUDIT_SORTS = sortColumns(auditGrid({ openable: [], functions: [], revision: false }));
