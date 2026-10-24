// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A timeline drawn as a frieze (FBS-4.3.1, WF-PLA-0140, US-0530, #1068), apart from the Gantt: on
 * the axis of time of the Gantt, at its levels and its zoom (`GanttRows`, `GanttAxis`), each task
 * inscribed is a rectangle from its start to its finish that holds its name — cut short when the
 * rectangle is too narrow, whole in its tooltip and in its accessible name —, and each milestone a
 * vertical line across the frieze, its name and its date at the foot. The dates are those the API
 * gives; nothing is scheduled here.
 *
 * The rectangles lie in lanes (`lanes.ts`): stacked automatically, in the order of the plan, unless
 * the user placed them, and moved from lane to lane by dragging them with the mouse, or by Alt and
 * the up and down arrows on the rectangle the keyboard is on. A move into a lane where the rectangle
 * would overlap another is refused, said, and nothing moves; Escape gives up a drag. The lanes are a display preference of
 * each user, by timeline (`DisplayPreferences.timelines`, WF-ADM-0040), recorded after a pause as the
 * settings of a grid are; moving a lane modifies no task.
 *
 * The frieze is one stop of the keyboard, named after the timeline, which moves among its rectangles
 * by the left and right arrows (`aria-activedescendant`), the axis scrolling to keep it in view; each rectangle and each milestone is named
 * by its task, its dates and its lane, and the table under the frieze reads the same (WF-IHM-0100).
 */
"use client";

import { Rows3 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  type KeyboardEvent,
  type PointerEvent,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import type { components } from "@/api/generated/schema";
import { updateTimelinePreferences } from "@/api/actions/preferences";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useKeptWriter } from "@/components/grid/settings";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import { GanttAxis, GanttRows, percent, useGanttView, zoomCommands } from "./gantt";
import {
  type LaneMove,
  laneCount,
  type LaneSpan,
  keptLanes,
  movedBy,
  movedTo,
  sentLanes,
  stackLanes,
} from "./lanes";
import { finishTime, startTime } from "./layout";
import type { TimelineTask } from "./timeline";

/** The lanes of a timeline, as the account keeps them. */
type TimelinePreferences = components["schemas"]["TimelinePreferences"];

/** The height of a lane, and the room a rectangle leaves above and below itself in it, in pixels. */
const LANE = 32;
const INSET = 4;

/** The height of the foot of the frieze, where the milestones are named. */
const FOOT = 36;

/** The width a name of a milestone takes at most, centred on its line. */
const MILESTONE_NAME = 128;

/**
 * Where the name of a milestone stands against its line, `at` pixels into an axis of `room`: centred
 * on it, but held within the frame near the edges — written inwards, from the line.
 */
function nameAnchor(at: number, room: number): { readonly shift: number; readonly align: string } {
  if (at < MILESTONE_NAME / 2) {
    return { shift: 0, align: "text-left" };
  }
  if (room - at < MILESTONE_NAME / 2) {
    return { shift: -MILESTONE_NAME, align: "text-right" };
  }
  return { shift: -MILESTONE_NAME / 2, align: "text-center" };
}

/** What the frieze draws of a task: its rectangle or its line, and how it is named. */
interface Drawn {
  readonly id: string;
  readonly label: string;
  readonly from: number;
  readonly to: number;
  readonly start: string;
  readonly finish: string;
}

/** The rectangles and the milestones of the tasks that have dates, in the order of the plan. */
function drawnOf(tasks: readonly TimelineTask[], locale: Locale) {
  const rectangles: Drawn[] = [];
  const milestones: Drawn[] = [];
  for (const node of tasks) {
    const task = node.task;
    if (task?.start == null || task.finish == null) {
      continue;
    }
    const drawn = {
      id: node.node_id,
      label: task.label,
      from: startTime(task.start),
      to: finishTime(task.finish),
      start: formatPlanningDate(task.start.date, locale, "short"),
      finish: formatPlanningDate(task.finish.date, locale, "short"),
    };
    (task.is_milestone ? milestones : rectangles).push(drawn);
  }
  return { rectangles, milestones };
}

/** What the frieze is given: its timeline, its tasks, the lanes kept. */
export interface TimelineChartProps {
  /** The name of the timeline. */
  readonly name: string;
  /** The identifier of the timeline, which its lanes are kept under. */
  readonly timeline: string;
  /** The tasks inscribed to it, in the order of the plan. */
  readonly tasks: readonly TimelineTask[];
  /** The lanes the account kept for it; none, stacked automatically. */
  readonly kept: Readonly<Record<string, number>> | undefined;
  /** The scope the level of the zoom is kept under for the session. */
  readonly scope: string;
}

/** Render a timeline as a frieze, on the axis of the Gantt, at its level of zoom. */
export function TimelineChart(props: TimelineChartProps) {
  return (
    <GanttRows rows={props.tasks} scope={props.scope}>
      <Frieze {...props} />
    </GanttRows>
  );
}

/** What a move says, or nothing for one that changes nothing. */
function said(
  t: ReturnType<typeof useTranslations<"timelines.chart">>,
  move: LaneMove,
  task: Drawn,
  from: number,
  labelOf: (id: string) => string,
): string | undefined {
  switch (move.kind) {
    case "moved":
      return t("moved", { task: task.label, lane: move.lane + 1 });
    case "overlap":
      return t("overlap", {
        task: task.label,
        other: labelOf(move.with),
        lane: move.lane + 1,
        from: from + 1,
      });
    case "edge":
      return t(move.edge, { task: task.label });
    case "stayed":
      return undefined;
  }
}

/** The frieze, in the Gantt around it: its commands, its axis, its drawing, its table. */
function Frieze({ name, timeline, tasks, kept }: TimelineChartProps) {
  const t = useTranslations("timelines.chart");
  const tz = useTranslations("gantt");
  const commands = useTranslations("commands");
  const tg = useTranslations("grid.columns");
  const locale = useLocale();
  const view = useGanttView();
  const drawn = useMemo(() => drawnOf(tasks, locale), [tasks, locale]);
  const spans: readonly LaneSpan[] = drawn.rectangles;
  const [placed, setPlaced] = useState(kept);
  const lanes = useMemo(() => stackLanes(spans, placed), [spans, placed]);
  const count = laneCount(lanes);
  const [chosen, setActive] = useState(spans[0]?.id);
  // The rectangle the keyboard is on, the first when the one chosen is no longer among the tasks.
  const active = spans.some((span) => span.id === chosen) ? chosen : spans[0]?.id;
  const [drag, setDrag] = useState<{ readonly id: string; readonly lane: number }>();
  // What was said last, counted: the same sentence said twice is replaced in the live region, and
  // so read again.
  const [message, setMessage] = useState<{ readonly text: string; readonly count: number }>();
  const writer = useKeptWriter<TimelinePreferences | null>(timeline, updateTimelinePreferences);
  const ids = useId();
  const frame = useRef<HTMLDivElement>(null);
  const drawing = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = frame.current;
    if (element === null) {
      return undefined;
    }
    const size = new ResizeObserver(() => {
      setWidth(element.clientWidth);
    });
    size.observe(element);
    setWidth(element.clientWidth);
    return () => {
      size.disconnect();
    };
  }, []);

  const labelOf = (id: string) => drawn.rectangles.find((each) => each.id === id)?.label ?? id;
  const say = (text: string) => {
    setMessage((last) => ({ text, count: (last?.count ?? 0) + 1 }));
  };
  // Scroll the axis to bring a rectangle into the frame, so that the focus stays seen.
  const show = (id: string | undefined) => {
    const span = spans.find((each) => each.id === id);
    if (view !== undefined && span !== undefined) {
      view.reveal(view.layout.at(span.from), view.layout.at(span.to));
    }
  };
  const apply = (id: string, move: LaneMove) => {
    const task = drawn.rectangles.find((each) => each.id === id);
    if (task === undefined) {
      return;
    }
    const sentence = said(t, move, task, lanes.get(id) ?? 0, labelOf);
    if (sentence !== undefined) {
      say(sentence);
    }
    if (move.kind === "moved") {
      const recorded = keptLanes(spans, move.lanes, id, placed);
      setPlaced(recorded);
      writer.record({ lanes: sentLanes(recorded) });
    }
  };
  const restack = () => {
    setPlaced(undefined);
    writer.record(null);
    say(t("restacked"));
  };
  const laneAt = (clientY: number) =>
    Math.floor((clientY - (drawing.current?.getBoundingClientRect().top ?? 0)) / LANE);

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape" && drag !== undefined) {
      // A drag given up: the rectangle goes back to its lane, and nothing is written.
      event.preventDefault();
      setDrag(undefined);
    } else {
      moveByKey(event);
    }
  };
  const moveByKey = (event: KeyboardEvent) => {
    const at = spans.findIndex((span) => span.id === active);
    if (at === -1) {
      return;
    }
    const step = { ArrowUp: -1, ArrowDown: 1 }[event.key] as -1 | 1 | undefined;
    if (event.altKey && step !== undefined) {
      event.preventDefault();
      apply(spans[at]?.id ?? "", movedBy(spans, lanes, spans[at]?.id ?? "", step));
      show(active);
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }
    const next = {
      ArrowLeft: at - 1,
      ArrowRight: at + 1,
      Home: 0,
      End: spans.length - 1,
    }[event.key];
    if (next !== undefined) {
      event.preventDefault();
      const reached = spans[Math.min(Math.max(next, 0), spans.length - 1)]?.id;
      setActive(reached);
      show(reached);
    }
  };
  const pointer = (id: string) => ({
    onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      frame.current?.focus();
      setActive(id);
      setDrag({ id, lane: lanes.get(id) ?? 0 });
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
      if (drag?.id === id) {
        setDrag({ id, lane: Math.min(Math.max(laneAt(event.clientY), 0), count) });
      }
    },
    onPointerUp: (event: PointerEvent<HTMLDivElement>) => {
      if (drag?.id === id) {
        setDrag(undefined);
        apply(id, movedTo(spans, lanes, id, laneAt(event.clientY)));
      }
    },
    onPointerCancel: () => {
      setDrag(undefined);
    },
  });

  if (view === undefined) {
    return null;
  }
  const shownLanes = Math.max(count + (drag === undefined ? 0 : 1), 1);
  const foot = drawn.milestones.length === 0 ? 0 : FOOT;
  const height = shownLanes * LANE + foot;
  const refused =
    drag !== undefined && movedTo(spans, lanes, drag.id, drag.lane).kind === "overlap";
  const laneName = (id: string) => (lanes.get(id) ?? 0) + 1;

  return (
    <figure aria-labelledby={`${ids}caption`} className="space-y-2">
      <figcaption className="flex flex-wrap items-start justify-between gap-2">
        <span id={`${ids}caption`} className="font-medium">
          {name}
        </span>
        <span className="flex flex-wrap gap-2">
          <span role="group" aria-label={t("zoom")} className="flex gap-1">
            {zoomCommands(view).map((command) => (
              <CommandTooltip
                key={command.key}
                label={tz(command.key)}
                help={commands(`${command.key}.help`)}
                keys={command.keys}
                unavailable={command.offered ? undefined : commands(`${command.key}.unavailable`)}
              >
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className={`size-8 ${UNAVAILABLE}`}
                  aria-label={tz(command.key)}
                  onClick={() => {
                    if (command.offered) {
                      view.zoomTo(command.step);
                    }
                  }}
                >
                  {command.icon}
                </Button>
              </CommandTooltip>
            ))}
          </span>
          <CommandTooltip
            label={t("restack")}
            help={commands("restack.help")}
            unavailable={placed === undefined ? commands("restack.unavailable") : undefined}
          >
            <Button
              type="button"
              variant="outline"
              size="sm"
              className={UNAVAILABLE}
              onClick={() => {
                if (placed !== undefined) {
                  restack();
                }
              }}
            >
              <Rows3 aria-hidden="true" />
              {t("restack")}
            </Button>
          </CommandTooltip>
        </span>
      </figcaption>
      <p id={`${ids}hint`} className="text-xs text-muted-foreground">
        {t("hint")}
      </p>
      <div className="rounded-md border">
        <div className="relative h-9 border-b">
          <GanttAxis width={Math.max(width, 0)} />
        </div>
        <div className="px-2">
          <div
            ref={frame}
            role="group"
            tabIndex={0}
            aria-label={t("name", { name })}
            aria-describedby={`${ids}hint`}
            aria-activedescendant={active === undefined ? undefined : `${ids}${active}`}
            data-gantt=""
            data-timeline=""
            className="group relative overflow-hidden focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
            onKeyDown={onKeyDown}
          >
            <svg
              ref={drawing}
              className="block overflow-visible"
              style={{
                width: view.width ?? "100%",
                height,
                transform:
                  view.width === undefined ? undefined : `translateX(-${String(view.offset)}px)`,
              }}
            >
              {view.lower.map((tick) => (
                <line
                  key={tick}
                  x1={percent(view.layout.at(tick))}
                  x2={percent(view.layout.at(tick))}
                  y1="0"
                  y2={shownLanes * LANE}
                  className="stroke-border"
                />
              ))}
              {Array.from({ length: shownLanes - 1 }, (_, lane) => (
                <line
                  key={lane}
                  x1="0"
                  x2="100%"
                  y1={(lane + 1) * LANE}
                  y2={(lane + 1) * LANE}
                  className="stroke-border"
                  strokeDasharray="2 4"
                />
              ))}
              {drawn.milestones.map((each) => {
                // The name is centred on its line, but held within the frame near its edges.
                const { shift, align } = nameAnchor(
                  view.layout.at(each.to) * (view.width ?? width),
                  view.width ?? width,
                );
                return (
                  <svg
                    key={each.id}
                    x={percent(view.layout.at(each.to))}
                    overflow="visible"
                    role="img"
                    aria-label={t("milestone", { task: each.label, date: each.finish })}
                  >
                    <title>{each.label}</title>
                    <line
                      x1="0"
                      x2="0"
                      y1="0"
                      y2={shownLanes * LANE}
                      className="stroke-foreground"
                      strokeDasharray="4 3"
                    />
                    <foreignObject
                      x={shift}
                      y={shownLanes * LANE + 2}
                      width={MILESTONE_NAME}
                      height={FOOT - 4}
                    >
                      <div className={`truncate ${align} text-[10px] leading-4 text-foreground`}>
                        {each.label}
                      </div>
                      <div className={`${align} text-[10px] leading-4 text-muted-foreground`}>
                        {each.finish}
                      </div>
                    </foreignObject>
                  </svg>
                );
              })}
              {drawn.rectangles.map((each) => {
                const dragged = drag?.id === each.id;
                const lane = dragged ? drag.lane : (lanes.get(each.id) ?? 0);
                return (
                  <foreignObject
                    key={each.id}
                    x={percent(view.layout.at(each.from))}
                    y={lane * LANE + INSET}
                    width={percent(
                      Math.max(view.layout.at(each.to) - view.layout.at(each.from), 0),
                    )}
                    height={LANE - 2 * INSET}
                    className="overflow-visible"
                  >
                    <div
                      id={`${ids}${each.id}`}
                      role="img"
                      aria-label={t("task", {
                        task: each.label,
                        start: each.start,
                        finish: each.finish,
                        lane: laneName(each.id),
                      })}
                      title={each.label}
                      data-active={each.id === active}
                      className={`h-full min-w-2 cursor-grab touch-none truncate rounded-sm border bg-secondary px-1 text-xs leading-[22px] text-secondary-foreground select-none group-focus-visible:data-[active=true]:ring-2 group-focus-visible:data-[active=true]:ring-ring ${
                        dragged && refused ? "border-dashed border-destructive" : "border-primary"
                      }`}
                      {...pointer(each.id)}
                    >
                      {each.label}
                    </div>
                  </foreignObject>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
      <p role="status" aria-live="polite" className="min-h-5 text-sm">
        {message === undefined ? null : <span key={message.count}>{message.text}</span>}
      </p>
      <OutcomeNotice outcome={writer.outcome} onClear={writer.clear} dismissible />
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">{t("table")}</summary>
        <Table
          aria-label={t("table")}
          list={t("table")}
          container={{ className: "mt-2 w-fit max-w-full rounded-md border" }}
          className="text-xs tabular-nums"
        >
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-right">
                {tg("rowNumber")}
              </TableHead>
              <TableHead scope="col">{tg("label")}</TableHead>
              <TableHead scope="col">{tg("startDate")}</TableHead>
              <TableHead scope="col">{tg("finishDate")}</TableHead>
              <TableHead scope="col">{t("lane")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((node) => {
              const row = [...drawn.rectangles, ...drawn.milestones].find(
                (each) => each.id === node.node_id,
              );
              let lane = t("undrawn");
              if (node.task?.is_milestone === true) {
                lane = t("milestoneLane");
              } else if (row !== undefined) {
                lane = String(laneName(row.id));
              }
              return (
                <TableRow key={node.node_id}>
                  <TableCell className="text-right text-muted-foreground">
                    {node.row_number}
                  </TableCell>
                  <TableCell>{node.task?.label}</TableCell>
                  <TableCell>{row?.start}</TableCell>
                  <TableCell>{row?.finish}</TableCell>
                  <TableCell>{lane}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </details>
    </figure>
  );
}
