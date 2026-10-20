// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning in the page: the dense grid — the one component the grid of the
 * estimate renders too —, given its configuration here, on the side of the browser, where the
 * functions of a configuration live. The page hands it data only: the rows of the answer of
 * `listNodes` as the grid reads them (`projectNodes`), the structure they belong to and its version,
 * what the address asked, the settings the session read, the posts and the lots of the work
 * breakdown read whole when the planning may be entered, and what the revision offers of its skeleton.
 * A computed cell asks the server what its value depends on, by the structure and its node. The
 * Gantt, its last column, lays out the rows the grid shows once for all its cells (`GanttRows`) —
 * those the tree leaves unfolded, so that both fold alike (WF-PLA-0090) —; the folds are kept for
 * the revision the structure belongs to.
 *
 * The attachment of a task is entered in its column, written by `updateTaskFacet`, its refusal said at
 * its cell by the reason of its field, naming the task that bears the item already or those the write
 * would move out of the subtree of its lot (WF-PLA-0170, EP-14/L44d). In the empty grid, the skeleton
 * is offered as the revision lists it (`generate_skeleton`, WF-PRJ-0030): unavailable, with its
 * condition, once the structure bears a task; generated, its tasks fill the grid as long as the
 * version the structure moved on to is more recent than the one read — a page read anew that reads it
 * prevails —, and the screen says so where the command stood, the focus there.
 */
"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";

import { generatePlanningSkeleton, updateTaskFacet } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { GanttRows } from "@/components/gantt/gantt";

import { DenseGrid } from "./dense-grid";
import { nodeDependencies } from "./node-dependencies";
import {
  type NodeFilters,
  nodeNarrowing,
  type NodeRows,
  type NodeSortColumn,
  type NodesWritten,
  nodesWritten,
  type StructurePath,
} from "./nodes";
import {
  PLANNING_FIELDS,
  type PlanningAttachment,
  planningGrid,
  type PlanningNode,
} from "./planning";
import { type BreakdownItem, byField } from "./planning-attachment";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";

/** What the grid of the planning shows. */
export interface PlanningGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<PlanningNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  /** The version of the structure read with the page, which the skeleton generated moves on. */
  readonly structureVersion?: number | undefined;
  /**
   * What the reading asked of the nodes besides their fields and their sort, as it was sent — the
   * search, a sub-project —: the rows above those it retains unfold.
   */
  readonly filters: NodeFilters;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
  /**
   * Whether the main structure read lists `edit_planning` available (`GridScreen.commands`): its grid places undo and redo, which
   * act on the entries of the planning once EP-06 keeps them; none, and it places none.
   */
  readonly undoable?: boolean | undefined;
  /**
   * The posts and the lots of the work breakdown read whole, which the attachment of a task is chosen
   * among, given where the planning may be entered; none, and the attachment is read only.
   */
  readonly breakdown?: readonly BreakdownItem[] | undefined;
  /** What the revision offers of the skeleton (`generate_skeleton`); none, it does not list it. */
  readonly skeleton?: CommandOffer | undefined;
}

/** The skeleton generated on a structure: its tasks as the grid reads them, and its version. */
interface Generated {
  readonly structure: string;
  readonly rows: NodeRows<PlanningNode>;
  readonly version: number;
}

/**
 * The skeleton offered in the empty grid, as the revision lists it; once generated, what the screen
 * says in its place, which takes the focus the command had — the command gone, it would fall to the
 * page.
 */
function SkeletonOffer({
  offer,
  generate,
  generated,
}: {
  readonly offer: CommandOffer | undefined;
  readonly generate: () => Promise<Outcome<unknown>>;
  readonly generated: Generated | undefined;
}) {
  const t = useTranslations();
  const told = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    told.current?.focus();
  }, [generated]);
  if (generated !== undefined) {
    return (
      <p ref={told} role="status" tabIndex={-1} className="text-sm outline-none">
        {t("planningGrid.skeletonGenerated", { tasks: generated.rows.totals.task_count })}
      </p>
    );
  }
  return (
    <Command
      offer={offer}
      label={t("enums.RevisionCommand.generate_skeleton")}
      icon={commandIcon(REVISION_COMMAND_ICONS.generate_skeleton)}
      action={generate}
    />
  );
}

/** Render the grid of the planning, its totals counting the tasks the answer retained. */
export function PlanningGrid({
  nodes,
  structure,
  structureVersion = 0,
  filters,
  query,
  preferences,
  undoable,
  breakdown,
  skeleton,
}: PlanningGridProps) {
  const t = useTranslations("planningGrid");
  const kinds = useTranslations("enums.WorkBreakdownKind");
  // The skeleton generated, for the structure it was generated on: a grid of another structure — a
  // revision left while it was generated — never shows it.
  const [generated, setGenerated] = useState<Generated>();
  const ours = generated?.structure === structure.structure_id ? generated : undefined;
  const filled = ours !== undefined && ours.version > structureVersion ? ours.rows : undefined;
  const shown = filled ?? nodes;
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, shown.items),
    [structure, shown.items],
  );
  // The totals of the structure a write answers are those of the reading when it narrows nothing
  // but the kinds it renders, which leave the totals as they are.
  const whole = Object.keys(nodeNarrowing(filters)).length === 0;
  const config = useMemo(() => {
    if (breakdown === undefined) {
      return planningGrid();
    }
    const items = new Map(breakdown.map((item) => [item.id, item]));
    const choices = breakdown.map((item) => ({
      id: item.id,
      label: item.label,
      code: kinds(item.kind),
      active: true,
    }));
    const attachment: PlanningAttachment = {
      items,
      choices: () => choices,
      write: async (node, change) => {
        const outcome = byField(
          await updateTaskFacet(structure, node.node_id, {
            ...change,
            lock_version: node.lock_version,
          }),
        );
        return outcome.kind === "done"
          ? { kind: "done", data: nodesWritten(outcome.data, PLANNING_FIELDS, whole) }
          : outcome;
      },
    };
    return planningGrid(attachment);
  }, [breakdown, kinds, structure, whole]);
  const generate = async (): Promise<Outcome<NodesWritten>> => {
    const asked = structure.structure_id;
    const outcome = await generatePlanningSkeleton(structure.project_id, structure.revision_id);
    if (outcome.kind === "done") {
      const written = nodesWritten(outcome.data, PLANNING_FIELDS, true);
      setGenerated({
        structure: asked,
        rows: { items: written.rows, totals: outcome.data.totals },
        version: outcome.data.structure_lock_version,
      });
    }
    return outcome;
  };
  const offered = nodes.items.length === 0 || ours !== undefined;
  return (
    <>
      {offered && (skeleton !== undefined || ours !== undefined) ? (
        <SkeletonOffer offer={skeleton} generate={generate} generated={ours} />
      ) : null}
      <DenseGrid
        config={config}
        rows={shown.items}
        totals={shown.totals}
        totalsCaption={(totals) => t("totals", { tasks: totals.task_count })}
        query={query}
        preferences={preferences}
        dependencies={dependencies}
        foldScope={structure.revision_id}
        narrowing={nodeNarrowing(filters)}
        undoable={undoable}
        around={(rows, table) => <GanttRows rows={rows}>{table}</GanttRows>}
      />
    </>
  );
}
