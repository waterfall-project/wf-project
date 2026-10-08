// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the dense grid of the journal of audit (FBS-1.5, WF-SEC-0030), alone on its
 * screen, with the key of its settings in the account (WF-ADM-0040): each inscription with its
 * date, its author, its action, the nature and the label of its object, its project and the
 * correlation of the request that produced it — every name as the inscription keeps it, that of the
 * moment of the action —, and the link to the history of its object. Read only: no cell is entered,
 * and nothing modifies nor deletes an inscription.
 *
 * The server sorts the inscriptions by their dates alone, both ways, the most recent first unless
 * asked otherwise (`sort_order`): the date is the one column sorted, and its sort is never lifted —
 * the header goes from one direction to the other. The grid writes it in the address as every grid
 * does (`sort_by=occurred_at`), and the page sends the API its direction alone, the contract having
 * no column to name.
 *
 * The object and the project are links where the session may consult them (WF-ADM-0110): a project
 * the session may open — one `listProjects` lists —, and of its objects a revision, which has an
 * address; a risk, a line of cost or an import is addressed in a revision the inscription does not
 * name, and an account, a role or a backup has no screen of its own: their names stand alone.
 *
 * Neither server nor client: the page reads the key and the column sorted; the grid, in the
 * browser, the rest — the functions that read a row never cross to the server.
 */
import { History } from "lucide-react";

import type { components } from "@/api/generated/schema";
import type { GridConfig } from "@/components/grid/columns";
import type { GridSort } from "@/components/grid/query";
import { LocalTime } from "@/components/local-time";

import {
  ActionCell,
  ActorCell,
  HistoryCell,
  ObjectCell,
  ObjectKindCell,
  ProjectCell,
} from "./audit-cells";

/** An inscription of the journal, as the contract gives it. */
export type AuditEvent = components["schemas"]["AuditEvent"];

/** Where a page stands in the inscriptions the server retained: their number, the totals row's. */
export type AuditPage = components["schemas"]["PaginationMeta"];

/** The one column the server sorts the journal by: the date of the inscriptions. */
export type AuditSort = "occurred_at";

/** The key of the settings of the grid in the account: stable. */
export const AUDIT_GRID_KEY = "audit_log";

/** The columns the grid sorts: the date alone. */
export const AUDIT_SORTS: readonly AuditSort[] = ["occurred_at"];

/** The sort of the journal unasked, as the server gives it: the most recent first. */
export const NEWEST_FIRST: GridSort<AuditSort> = { column: "occurred_at", order: "desc" };

/** The address of a project the session may open, or none. */
function projectHref(projectId: string, openable: ReadonlySet<string>): string | undefined {
  return openable.has(projectId) ? `/projects/${projectId}` : undefined;
}

/**
 * The address of the object of an inscription, when it has one and the session may consult it:
 * a project it may open, a revision of such a project.
 */
function objectHref(event: AuditEvent, openable: ReadonlySet<string>): string | undefined {
  const { kind, object_id: id } = event.object;
  if (kind === "project") {
    return projectHref(id, openable);
  }
  const project = event.project;
  if (kind !== "revision" || project === null || !openable.has(project.project_id)) {
    return undefined;
  }
  return `/projects/${project.project_id}/revisions/${id}`;
}

/**
 * The grid of the journal, its links leading to what the session may consult: the projects it may
 * open, by their identifiers.
 */
export function auditGrid(
  openable: ReadonlySet<string>,
): GridConfig<AuditEvent, AuditSort, AuditPage> {
  return {
    key: AUDIT_GRID_KEY,
    name: "auditLog",
    searched: false,
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
        value: (event) => event.occurred_at,
        render: (event) => <LocalTime value={event.occurred_at} />,
      },
      {
        key: "actor",
        label: "author",
        format: "text",
        width: 180,
        value: (event) => event.actor.display_name ?? event.actor.kind,
        render: (event) => <ActorCell actor={event.actor} />,
      },
      {
        key: "action",
        label: "auditAction",
        format: "text",
        width: 250,
        value: (event) => event.action,
        render: (event) => <ActionCell action={event.action} />,
      },
      {
        key: "object_kind",
        label: "objectKind",
        format: "text",
        width: 170,
        value: (event) => event.object.kind,
        render: (event) => <ObjectKindCell kind={event.object.kind} />,
      },
      {
        key: "object",
        label: "auditObject",
        format: "text",
        width: 260,
        value: (event) => event.object.label,
        render: (event) => <ObjectCell object={event.object} href={objectHref(event, openable)} />,
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
        value: (event) => event.project?.code,
        render: (event) => (
          <ProjectCell
            project={event.project}
            href={
              event.project === null ? undefined : projectHref(event.project.project_id, openable)
            }
          />
        ),
      },
      {
        key: "correlation",
        label: "correlation",
        format: "text",
        width: 300,
        value: (event) => event.correlation_id,
      },
    ],
  };
}
