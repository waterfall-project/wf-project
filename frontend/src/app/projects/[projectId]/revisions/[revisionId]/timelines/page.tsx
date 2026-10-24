// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The timelines of a project (FBS-4.3.1, WF-PLA-0140, US-0220), a leaf of the planning with a
 * screen of its own, whose head leads here in the same context: the banner of its reading context
 * (WF-IHM-0020); the named timelines of the project (`listTimelines`), each a link that writes the
 * address (`timeline`) — the first when the address names none the project has —; and the tasks of
 * the revision inscribed to the one shown, drawn as a frieze in the lanes the account keeps for it
 * (`TimelineChart`, `DisplayPreferences.timelines`), exported with the date its dates were
 * calculated at (`meta.scheduled_at`). The timelines are created and deleted as the project lists
 * `manage_timelines` (`TimelineChoice`, EP-14/L44f), the screen saying then that the fake back
 * keeps none of it (`MockupNotice`), and the tasks of a timeline deleted giving way with it
 * (`TimelineBody`); the inscriptions are read, never entered here. The tasks are read
 * as the grid of the planning reads them — the tasks alone, restricted to the filtered sub-project
 * (`grid-screen.ts`) —, the server selecting those inscribed to the timeline shown (`timeline_id`,
 * #463), once the timelines read say which it is, the screen keeping them once more against the
 * fake back (`inscribedTo`); of each the fields the timeline reads, their inscriptions among them.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import { inscribedTo, type TimelineTask } from "@/components/gantt/timeline";
import type { ChartProvenance } from "@/components/chart/chart";
import { TimelineChart } from "@/components/gantt/timeline-chart";
import {
  TimelineBody,
  TimelineChoice,
  TimelineDeletions,
} from "@/components/gantt/timeline-commands";
import { FUNCTION_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, searchQuery } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress, readGridScreen } from "../grid-screen";
import type { RevisionParams } from "../page";

/** A named timeline of a project. */
type Timeline = components["schemas"]["Timeline"];

/** The parameter of the address the timeline shown goes by. */
const TIMELINE = "timeline";

/** Title the tab with the leaf, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.timelines", projectId);
}

/** What a timeline reads of a task, beyond what every reading of the structure reads. */
const TIMELINE_FIELDS = {
  node: [],
  task: ["start", "finish", "is_critical", "tracking"],
  line: [],
} as const;

/** The project and the revision the exported image names; the current one has no version name. */
function provenanceOf(reading: ProjectReading, current: string): ChartProvenance {
  return {
    project: reading.project.label,
    code: reading.project.code ?? reading.project.project_id,
    revision: reading.revision?.version_name ?? current,
  };
}

/**
 * What the frieze of the timeline shown needs besides its tasks: the reading context, which scopes
 * its zoom and names the project and the revision in its exported image, the lanes the account keeps
 * for it, and the instant the dates of the structure were last calculated at.
 */
interface TimelineDrawing {
  readonly reading: ProjectReading;
  readonly kept: Readonly<Record<string, number>> | undefined;
  /** None when the project has no timeline: no task is read. */
  readonly scheduledAt: string | undefined;
}

/**
 * The head of the screen — the timelines and their commands, as the project lists `manage_timelines`
 * —, and the tasks of the one shown, drawn here and given way once it is deleted (`TimelineBody`).
 */
function TimelinesScreen({
  project,
  offer,
  timelines,
  shown,
  tasks,
  hrefs,
  drawing,
}: {
  readonly project: string;
  readonly offer: CommandOffer | undefined;
  readonly timelines: readonly Timeline[];
  readonly shown: Timeline | undefined;
  readonly tasks: readonly TimelineTask[];
  readonly hrefs: Readonly<Record<string, string>>;
  readonly drawing: TimelineDrawing;
}) {
  const t = useTranslations();
  let body: ReactNode = null;
  if (shown !== undefined && drawing.scheduledAt !== undefined) {
    body =
      tasks.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("timelines.empty")}</p>
      ) : (
        <TimelineChart
          key={shown.timeline_id}
          name={shown.label}
          timeline={shown.timeline_id}
          tasks={tasks}
          kept={drawing.kept}
          provenance={provenanceOf(drawing.reading, t("contextBanner.currentRevision"))}
          scheduledAt={drawing.scheduledAt}
          scope={`timelines:${drawing.reading.revision?.revision_id ?? project}`}
        />
      );
  }
  return (
    <Screen density={FUNCTION_DENSITY.planning}>
      <TimelineDeletions>
        <PageHeader
          title={t("functions.timelines")}
          icon={LEAF_ICONS["FBS-4.3.1"]}
          density={FUNCTION_DENSITY.planning}
          subtitle={t("timelines.summary")}
          actions={
            timelines.length === 0 && offer === undefined ? undefined : (
              <TimelineChoice
                project={project}
                offer={offer}
                timelines={timelines}
                shown={shown?.timeline_id}
                hrefs={hrefs}
              />
            )
          }
        />
        {offer?.is_available === true ? <MockupNotice /> : null}
        <TimelineBody timelines={timelines} shown={shown?.timeline_id}>
          {body}
        </TimelineBody>
      </TimelineDeletions>
    </Screen>
  );
}

/**
 * The tasks of the revision inscribed to the timeline shown, which the server selects
 * (`timeline_id`) and the screen keeps once more (`inscribedTo`), and the reading context they are
 * read in, which shows the filtered sub-project they are read for.
 */
async function readInscribed(at: GridAddress, shown: Timeline) {
  const screen = await readGridScreen(at, {
    key: "timelines",
    sortable: [],
    kinds: ["task"],
    narrowed: { timeline_id: shown.timeline_id },
    fields: TIMELINE_FIELDS,
  });
  return {
    reading: screen.reading,
    tasks: inscribedTo(screen.nodes.items, shown.timeline_id),
    scheduledAt: screen.scheduledAt,
  };
}

/** Render the timelines of a project, and the tasks of the revision inscribed to the one shown. */
export default async function TimelinesPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "timelines");
  // The reading context is read with the timelines: a project without a timeline reads no task,
  // and its banner shows no filter, none of its reads taking one (#302).
  const [timelines, context, session] = await Promise.all([
    readOrFail("listTimelines", () =>
      serverClient().GET("/projects/{project_id}/timelines", {
        params: { path: { project_id: revision.projectId } },
      }),
    ),
    readProjectContext(at.pathname, at.context, []),
    requestSession(),
  ]);
  if (context === "not_found") {
    notFound();
  }
  const asked = at.address.get(TIMELINE);
  const shown = timelines.find((timeline) => timeline.timeline_id === asked) ?? timelines[0];
  const {
    reading,
    tasks,
    scheduledAt,
  }: { reading: ProjectReading; tasks: readonly TimelineTask[]; scheduledAt: string | undefined } =
    shown === undefined
      ? { reading: context, tasks: [], scheduledAt: undefined }
      : await readInscribed(at, shown);
  const kept =
    shown === undefined
      ? undefined
      : (session?.display_preferences?.timelines?.[shown.timeline_id]?.lanes ?? undefined);
  const query = searchQuery(search);
  const href = (timeline: Timeline) => {
    const next = new URLSearchParams(query);
    next.set(TIMELINE, timeline.timeline_id);
    return `${at.pathname}?${next.toString()}`;
  };
  return (
    <>
      <ContextBanner reading={reading} />
      <TimelinesScreen
        project={revision.projectId}
        offer={findOffer(context.project.available_commands, "manage_timelines")}
        timelines={timelines}
        shown={shown}
        tasks={tasks}
        hrefs={Object.fromEntries(
          timelines.map((timeline) => [timeline.timeline_id, href(timeline)]),
        )}
        drawing={{ reading, kept, scheduledAt }}
      />
    </>
  );
}
