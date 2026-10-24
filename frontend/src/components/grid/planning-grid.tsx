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
 * the revision the structure belongs to. Given the hours of a day of the installation, the Gantt
 * zooms down to the worked hours; given where it comes from, it is exported as an image (`gantt`).
 *
 * Where the planning may be entered, the cells of a task are written by `updateTaskFacet`, each
 * alone (US-0470): its label, its description, its mode, its duration with its unit, the dates of a
 * manual task, its attachment — and its predecessors, the whole list at once, by `setPredecessors`,
 * the tasks it redates taking their place with it —; a refusal is said at its cell by the reason of
 * its field — a loop of links, naming its tasks, the task
 * that bears the item already, those the write would move out of the subtree of its lot
 * (WF-PLA-0170, EP-14/L44d), a date the server computes. In the empty grid, the skeleton
 * is offered as the revision lists it (`generate_skeleton`, WF-PRJ-0030): unavailable, with its
 * condition, once the structure bears a task; generated, its tasks fill the grid as long as the
 * version the structure moved on to is more recent than the one read — a page read anew that reads it
 * prevails —, and the screen says so where the command stood, the focus there.
 */
"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { generatePlanningSkeleton, setPredecessors, updateTaskFacet } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import {
  type GanttExported,
  GanttLegend,
  GanttRows,
  GanttZoomItems,
} from "@/components/gantt/gantt";
import { useNoteMessage } from "@/components/notices/message-history";
import { useShownProjectLabel } from "@/components/shell/shown-project";

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
  withDifference,
} from "./nodes";
import {
  PLANNING_FIELDS,
  type PlanningAttachment,
  planningGrid,
  type PlanningNode,
  type PlanningWrites,
} from "./planning";
import type { BreakdownItem } from "./planning-attachment";
import type { GridQuery } from "./query";
import type { ChoiceOption, RowChoices } from "./row-choices";
import type { GridPreferences } from "./settings";
import { useStructureGestures } from "./structure-gestures";
import { useStructureVersion } from "./structure-version";
import type { RowCommands } from "./undo-commands";

/** What the grid of the planning shows. */
export interface PlanningGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<PlanningNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  /**
   * The version of the structure read with the page, which the writes of the grid go on from and
   * the skeleton generated moves on: always given, never guessed (#819.7).
   */
  readonly structureVersion: number;
  /**
   * What the reading asked of the nodes besides their fields and their sort, as it was sent — the
   * search, a sub-project —: the rows above those it retains unfold.
   */
  readonly filters: NodeFilters;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
  /**
   * Whether the main structure read lists `edit_planning` available (`GridScreen.commands`): its
   * grid places undo and redo, which act on the entries of the planning once EP-06 keeps them;
   * none, and it places none.
   */
  readonly undoable?: boolean | undefined;
  /**
   * Whether the structure lists `edit_planning` available: the cells of the tasks are entered
   * (US-0470), and the tasks created and deleted from the grid (US-0460). Not, and the grid is read
   * only, offering no gesture of structure.
   */
  readonly editable?: boolean | undefined;
  /**
   * The posts and the lots of the work breakdown read whole, which the attachment of a task is chosen
   * among, given where the planning may be entered; none, and the attachment is read only.
   */
  readonly breakdown?: readonly BreakdownItem[] | undefined;
  /** What the revision offers of the skeleton (`generate_skeleton`); none, it does not list it. */
  readonly skeleton?: CommandOffer | undefined;
  /**
   * The timelines of the project: they name the inscriptions of the tasks (the column « Chronologies »)
   * and are the boxes of the submenu of the cells (US-0480). None when the API refused the list, and
   * the grid then names no timeline and offers no submenu.
   */
  readonly timelines?: readonly ChoiceOption[] | undefined;
  /**
   * What the project lists of `manage_timelines`, which creates a timeline from the submenu of the
   * cells; none, and the submenu does not offer it.
   */
  readonly timelineCreation?: CommandOffer | undefined;
  /**
   * Whether the structure read is a differential, whose nodes bear the difference the server marks:
   * the grid then has its column of marks (US-0500).
   */
  readonly differential?: boolean | undefined;
  /**
   * What the Gantt reads besides the rows: the graduations of hours of a day (`hoursOfDay`), and
   * where it comes from, which its exported image names. None, it stops at days and is not
   * exported.
   */
  readonly gantt?: PlanningGantt | undefined;
}

/** What the Gantt of the planning reads besides its rows. */
export interface PlanningGantt {
  readonly hoursPerDay: number | undefined;
  readonly exported: GanttExported;
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
 * page —, noted in the history of the messages.
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
  const sentence =
    generated === undefined
      ? undefined
      : t("planningGrid.skeletonGenerated", { tasks: generated.rows.totals.task_count });
  useNoteMessage(
    generated,
    sentence === undefined ? undefined : { tone: "success", sentence },
    useShownProjectLabel(),
  );
  if (sentence !== undefined) {
    return (
      <p ref={told} role="status" tabIndex={-1} className="text-sm outline-none">
        {sentence}
      </p>
    );
  }
  return (
    <Command
      offer={offer}
      label={t("enums.RevisionCommand.generate_skeleton")}
      help={t("commands.revision.generate_skeleton.help")}
      icon={commandIcon(REVISION_COMMAND_ICONS.generate_skeleton)}
      action={generate}
    />
  );
}

/**
 * The task a row number names (WF-PLA-0030), among the rows the grid read: the row of that number —
 * a task — or, for a task a search left out, the predecessor of a row read that has that number, whose
 * number the API gives in the numbering of the whole structure. None for a number no row read names.
 */
function taskOfRow(rows: readonly PlanningNode[], number: number): string | undefined {
  const own = rows.find((node) => node.row_number === number && node.task != null);
  if (own !== undefined) {
    return own.node_id;
  }
  for (const node of rows) {
    const found = node.predecessors?.find((link) => link.predecessor_row_number === number);
    if (found !== undefined) {
      return found.predecessor_node_id;
    }
  }
  return undefined;
}

/**
 * The task a row number names among the rows the grid reads (`taskOfRow`): one function for the life
 * of the grid, reading the rows of the reading committed last — the entry asks it in an event
 * handler, never while rendering — so that a reading anew does not build the configuration anew.
 */
function useTaskOfRow(rows: readonly PlanningNode[]): (number: number) => string | undefined {
  const read = useRef(rows);
  useLayoutEffect(() => {
    read.current = rows;
  }, [rows]);
  return useCallback((number) => taskOfRow(read.current, number), []);
}

/** Render the grid of the planning, its totals counting the tasks the answer retained. */
export function PlanningGrid({
  nodes,
  structure,
  structureVersion,
  filters,
  query,
  preferences,
  undoable,
  editable,
  breakdown,
  skeleton,
  timelines,
  timelineCreation,
  differential,
  gantt,
}: PlanningGridProps) {
  const t = useTranslations("planningGrid");
  const kinds = useTranslations("enums.WorkBreakdownKind");
  const modes = useTranslations("enums.SchedulingMode");
  const units = useTranslations("enums.DurationUnit");
  const lagUnits = useTranslations("enums.LagUnit");
  // The skeleton generated, for the structure it was generated on: a grid of another structure — a
  // revision left while it was generated — never shows it.
  const [generated, setGenerated] = useState<Generated>();
  const ours = generated?.structure === structure.structure_id ? generated : undefined;
  // One account of the writes of the structure: the version they moved it on to, whichever write
  // moved it, and those under way, which the gestures wait for.
  const account = useStructureVersion(structure.structure_id, structureVersion);
  const { version, reach } = account;
  const filled = ours !== undefined && ours.version > structureVersion ? ours.rows : undefined;
  const shown = filled ?? nodes;
  const taskOf = useTaskOfRow(shown.items);
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, shown.items),
    [structure, shown.items],
  );
  // The totals of the structure a write answers are those of the reading when it narrows nothing
  // but the kinds it renders, which leave the totals as they are.
  const whole = Object.keys(nodeNarrowing(filters)).length === 0;
  const read = useMemo(() => {
    if (editable !== true) {
      return planningGrid(undefined, timelines);
    }
    const attachment: PlanningAttachment | undefined =
      breakdown === undefined
        ? undefined
        : {
            items: new Map(breakdown.map((item) => [item.id, item])),
            choices: () =>
              breakdown.map((item) => ({
                id: item.id,
                label: item.label,
                code: kinds(item.kind),
                active: true,
              })),
          };
    // What a write of a node answers, as the grid reads it; the version the structure moved on to is
    // told the account.
    const answered = (outcome: Outcome<NodesWritten>) => {
      if (outcome.kind !== "done") {
        return outcome;
      }
      reach(outcome.data.structure_lock_version);
      return { kind: "done" as const, data: nodesWritten(outcome.data, PLANNING_FIELDS, whole) };
    };
    const writes: PlanningWrites = {
      // The field entered and the version of the node read, nothing else (#178).
      task: async (node, change) =>
        answered(
          await updateTaskFacet(structure, node.node_id, {
            ...change,
            lock_version: node.lock_version,
          }),
        ),
      // The links of the task in place of its own, with the version of the node read: the rows the
      // server answers, the tasks the links redate with them, take the place of the rows read.
      predecessors: {
        code: (link) => t("linkCode", { link }),
        suffix: (unit) => lagUnits(unit),
        resolve: taskOf,
        write: async (node, predecessors) =>
          answered(
            await setPredecessors(structure, node.node_id, {
              predecessors: [...predecessors],
              lock_version: node.lock_version,
            }),
          ),
      },
      modes: (mode) => modes(mode),
      suffix: (unit) => units(unit),
      written: (value, unit) => t("duration", { value, unit: units(unit) }),
      attachment,
    };
    return planningGrid(writes, timelines);
  }, [
    editable,
    breakdown,
    kinds,
    modes,
    units,
    lagUnits,
    t,
    structure,
    whole,
    reach,
    timelines,
    taskOf,
  ]);
  const config = useMemo(() => withDifference(read, differential), [read, differential]);
  // The skeleton moves the structure on as any write of the grid does: counted in the account, the
  // gestures wait for it (#1224). The command calls it in its transition, which would hold the count
  // back until the answer: the write is sent, and counted, once out of it.
  const generate = (): Promise<Outcome<NodesWritten>> => {
    const asked = structure.structure_id;
    const send = async (): Promise<Outcome<NodesWritten>> => {
      const outcome = await generatePlanningSkeleton(structure.project_id, structure.revision_id);
      if (outcome.kind === "done") {
        reach(outcome.data.structure_lock_version);
        const written = nodesWritten(outcome.data, PLANNING_FIELDS, true);
        setGenerated({
          structure: asked,
          rows: { items: written.rows, totals: outcome.data.totals },
          version: outcome.data.structure_lock_version,
        });
      }
      return outcome;
    };
    return Promise.resolve().then(() => {
      const write = send();
      account.writing(write);
      return write;
    });
  };
  // The timelines a task is inscribed to are chosen where the planning may be entered, among those the
  // project lists.
  const choices = useMemo<RowChoices<PlanningNode> | undefined>(
    () =>
      timelines === undefined
        ? undefined
        : {
            tracking: {
              project: structure.project_id,
              timelines,
              creation: timelineCreation,
              entries: (node) => node.task?.tracking ?? [],
            },
            written: (written) => nodesWritten(written, PLANNING_FIELDS, whole),
          },
    [timelines, timelineCreation, structure.project_id, whole],
  );
  const gestures = useStructureGestures<PlanningNode>(
    editable === true
      ? {
          structure,
          tasks: true,
          lines: false,
          categories: undefined,
          rows: shown.items,
          version,
        }
      : undefined,
    account,
    choices,
  );
  // The zoom of the Gantt in the menu of a cell too, after the gestures, as its buttons in the header
  // of the Gantt (`GanttZoom`).
  const zoomed: RowCommands<PlanningNode> =
    gestures === undefined
      ? { bar: () => null, menu: () => <GanttZoomItems separated={false} /> }
      : {
          ...gestures,
          menu: (row, opened) => (
            <>
              {gestures.menu(row, opened)}
              <GanttZoomItems separated />
            </>
          ),
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
        commands={zoomed}
        around={(rows, table) => (
          <GanttRows
            rows={rows}
            scope={`${config.key}:${structure.revision_id}`}
            hoursPerDay={gantt?.hoursPerDay}
            exported={gantt?.exported}
          >
            {table}
            <GanttLegend />
          </GanttRows>
        )}
      />
    </>
  );
}
