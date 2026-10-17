// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The audit columns of the tables of the accounts and of the access roles (WF-DAT-0070, US-0360/L4,
 * #936): « Créé le », « Créé par », « Modifié le » and « Modifié par », as the contract gives them
 * (`audit`), each sorted by the server under the name of its field (WF-IHM-0060). An instant shows in
 * the local time of the workstation (`LocalTime`); an author by the name the row keeps of the
 * account — kept after its deactivation, the neutral label once it is anonymised (WF-ADM-0060) —, or
 * the platform by its own label (`ActorCell`).
 *
 * Neither server nor client: the pages read the columns sorted, the grids the rest.
 */
import type { components } from "@/api/generated/schema";
import { ActorCell } from "@/components/audit/audit-cells";
import type { GridColumn } from "@/components/grid/columns";
import { LocalTime } from "@/components/local-time";

type Audit = components["schemas"]["Audit"];

/** The columns of the contract the audit columns are sorted by, the same for both lists. */
export type AuditSort = "created_at" | "created_by" | "updated_at" | "updated_by";

/** The width of a column of instants, and of a column of authors. */
const INSTANT_WIDTH = 168;
const AUTHOR_WIDTH = 180;

/** The four audit columns of a grid of rows that carry their audit. */
export function auditColumns<Row extends { readonly audit: Audit }, Totals>(): GridColumn<
  Row,
  AuditSort,
  Totals
>[] {
  /** The column of an instant of the audit. */
  const instant = (
    field: "created_at" | "updated_at",
    label: "createdAt" | "updatedAt",
  ): GridColumn<Row, AuditSort, Totals> => ({
    key: field,
    label,
    format: "text",
    width: INSTANT_WIDTH,
    contract: field,
    value: (row) => row.audit[field],
    render: (row) => <LocalTime value={row.audit[field]} />,
  });
  /** The column of an author of the audit. */
  const author = (
    field: "created_by" | "updated_by",
    label: "createdBy" | "updatedBy",
  ): GridColumn<Row, AuditSort, Totals> => ({
    key: field,
    label,
    format: "text",
    width: AUTHOR_WIDTH,
    contract: field,
    value: (row) => row.audit[field].display_name ?? row.audit[field].kind,
    render: (row) => <ActorCell actor={row.audit[field]} />,
  });
  return [
    instant("created_at", "createdAt"),
    author("created_by", "createdBy"),
    instant("updated_at", "updatedAt"),
    author("updated_by", "updatedBy"),
  ];
}
