// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The timelines of a project (FBS-4.3.1, WF-PLA-0140, US-0220), a leaf of the planning with a
 * screen of its own, whose head leads here in the same context: the banner of its reading context
 * (WF-IHM-0020); the named timelines of the project (`listTimelines`), each a link that writes the
 * address (`timeline`) — the first when the address names none the project has —; and the tasks of
 * the revision inscribed to the one shown, drawn on their axis of time (`TimelineTable`). Read and
 * never entered: neither the timelines nor the inscriptions are changed here. The tasks are read
 * as the grid of the planning reads them — the tasks alone, restricted to the filtered sub-project
 * (`grid-screen.ts`) —, the server selecting those inscribed to the timeline shown (`timeline_id`,
 * #463), once the timelines read say which it is, the screen keeping them once more against the
 * fake back (`inscribedTo`); of each the fields the timeline reads, their inscriptions among them.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import { inscribedTo, type TimelineTask, TimelineTable } from "@/components/gantt/timeline";
import { FUNCTION_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { type PageSearchParams, searchQuery } from "@/navigation/context";

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

/** The timelines of the project, each a link to it, the one shown marked as the current one. */
function Timelines({
  timelines,
  shown,
  href,
}: {
  readonly timelines: readonly Timeline[];
  readonly shown: Timeline | undefined;
  readonly href: (timeline: Timeline) => string;
}) {
  const t = useTranslations("timelines");
  return (
    <nav aria-label={t("choice")} className="flex flex-wrap items-center gap-1 text-sm">
      {timelines.map((timeline) => (
        <Link
          key={timeline.timeline_id}
          href={href(timeline)}
          aria-current={timeline === shown ? "true" : undefined}
          className={buttonVariants({
            variant: timeline === shown ? "default" : "outline",
            size: "sm",
          })}
        >
          {timeline.label}
        </Link>
      ))}
    </nav>
  );
}

/** The head of the screen, the timelines, and the tasks of the one shown. */
function TimelinesScreen({
  timelines,
  shown,
  tasks,
  href,
}: {
  readonly timelines: readonly Timeline[];
  readonly shown: Timeline | undefined;
  readonly tasks: readonly TimelineTask[];
  readonly href: (timeline: Timeline) => string;
}) {
  const t = useTranslations();
  let body = <p className="text-sm text-muted-foreground">{t("timelines.none")}</p>;
  if (shown !== undefined) {
    body =
      tasks.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("timelines.empty")}</p>
      ) : (
        <TimelineTable name={shown.label} tasks={tasks} />
      );
  }
  return (
    <Screen density={FUNCTION_DENSITY.planning}>
      <PageHeader
        title={t("functions.timelines")}
        icon={LEAF_ICONS["FBS-4.3.1"]}
        density={FUNCTION_DENSITY.planning}
        subtitle={t("timelines.summary")}
        actions={
          timelines.length === 0 ? undefined : (
            <Timelines timelines={timelines} shown={shown} href={href} />
          )
        }
      />
      {body}
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
  return { reading: screen.reading, tasks: inscribedTo(screen.nodes.items, shown.timeline_id) };
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
  const [timelines, context] = await Promise.all([
    readOrFail("listTimelines", () =>
      serverClient().GET("/projects/{project_id}/timelines", {
        params: { path: { project_id: revision.projectId } },
      }),
    ),
    readProjectContext(at.pathname, at.context, []),
  ]);
  if (context === "not_found") {
    notFound();
  }
  const asked = at.address.get(TIMELINE);
  const shown = timelines.find((timeline) => timeline.timeline_id === asked) ?? timelines[0];
  const { reading, tasks }: { reading: ProjectReading; tasks: readonly TimelineTask[] } =
    shown === undefined ? { reading: context, tasks: [] } : await readInscribed(at, shown);
  const query = searchQuery(search);
  const href = (timeline: Timeline) => {
    const next = new URLSearchParams(query);
    next.set(TIMELINE, timeline.timeline_id);
    return `${at.pathname}?${next.toString()}`;
  };
  return (
    <>
      <ContextBanner reading={reading} />
      <TimelinesScreen timelines={timelines} shown={shown} tasks={tasks} href={href} />
    </>
  );
}
