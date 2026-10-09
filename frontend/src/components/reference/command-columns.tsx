// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The columns the grids of the reference data give their commands (EP-02/L43): the state of each
 * object and the command that changes it, as the server lists it (`StateCell`), and, for a session
 * that may modify the function of the grid, the modification of each row in a column of its own.
 *
 * Neither server nor client: the configurations of the grids read it, in the browser.
 */
import type { GridColumn } from "@/components/grid/columns";

import { type Conflict, ModifyCommand, type ReferenceCommands, StateCell } from "./commands";
import type { ActivationTarget, ReferenceObject } from "./kinds";

/** What the column of the state reads of an object: its state, what its command needs and names. */
export interface StateRead {
  readonly active: boolean;
  readonly target: ActivationTarget;
  readonly name: string;
  readonly commands: ReferenceCommands;
  /** The object a refusal of its reactivation may name; none when the row knows none. */
  readonly conflict?: Conflict | undefined;
}

/** The widths of the column of the state and its command, and of that of the modification. */
const STATE_WIDTH = 190;
const MODIFY_WIDTH = 110;

/**
 * The column of the state of an object and its command as the server lists it, and, for a session
 * that may modify the function of the grid (`editable`), the column of its modification.
 */
export function commandColumns<Row extends ReferenceObject, Sort extends string>(
  editable: boolean,
  read: (row: Row) => StateRead,
  contract: Sort | undefined,
): GridColumn<Row, Sort, null>[] {
  const state: GridColumn<Row, Sort, null> = {
    key: "state",
    label: "state",
    format: "text",
    width: STATE_WIDTH,
    ...(contract === undefined ? {} : { contract }),
    value: (row) => (read(row).active ? "active" : "inactive"),
    render: (row) => <StateCell {...read(row)} />,
  };
  const modify: GridColumn<Row, Sort, null> = {
    key: "modify",
    label: "modify",
    format: "text",
    width: MODIFY_WIDTH,
    value: () => null,
    render: (row) => <ModifyCommand row={row} />,
  };
  return editable ? [state, modify] : [state];
}
