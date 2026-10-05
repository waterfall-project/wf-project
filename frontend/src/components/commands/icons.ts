// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The icon of each command of a project and of a revision, a form of Lucide shown before its
 * name (charter, guide « Charte graphique »). Tables typed on the commands of the contract: a
 * command the contract adds has no icon until it is given one here, and the typing says so.
 * `commandIcon` draws one, hidden from a screen reader beside the name of the command.
 */
import {
  Ban,
  Calculator,
  CalendarRange,
  CircleCheckBig,
  CircleX,
  FileDown,
  FileUp,
  FlagTriangleRight,
  GitBranchPlus,
  GitMerge,
  Hourglass,
  ListTree,
  ListX,
  type LucideIcon,
  Pencil,
  ShieldAlert,
  Stamp,
  Star,
  UserPlus,
} from "lucide-react";

import { createElement, type ReactElement } from "react";

import type { components } from "@/api/generated/schema";

/** The icon of each command of a project. */
export const PROJECT_COMMAND_ICONS: Readonly<
  Record<components["schemas"]["ProjectCommand"], LucideIcon>
> = {
  update: Pencil,
  manage_contributors: UserPlus,
  create_revision: GitBranchPlus,
  complete: CircleCheckBig,
  lose: CircleX,
  abandon: Ban,
  edit_risks: ShieldAlert,
  declare_risk_occurrence: FlagTriangleRight,
  import_actual_costs: FileUp,
  exclude_cost_lines: ListX,
  // An import of a kind: the icon of the command that modifies the same content.
  import_planning: CalendarRange,
  import_estimate: Calculator,
  import_remaining: Hourglass,
};

/** The icon of each command of a revision. */
export const REVISION_COMMAND_ICONS: Readonly<
  Record<components["schemas"]["RevisionCommand"], LucideIcon>
> = {
  edit_planning: CalendarRange,
  edit_estimate: Calculator,
  edit_remaining: Hourglass,
  create_structure: ListTree,
  merge_structure: GitMerge,
  mark: Stamp,
  designate_reference: Star,
  abandon: Ban,
  // The exports, which the screen of the exchanges offers in one request, share its icon.
  export_planning: FileDown,
  export_estimate: FileDown,
  export_remaining: FileDown,
  export_task_tree_image: FileDown,
};

/** The icon of a command, drawn before its name and hidden from a screen reader. */
export function commandIcon(icon: LucideIcon): ReactElement {
  return createElement(icon, { "aria-hidden": true });
}
