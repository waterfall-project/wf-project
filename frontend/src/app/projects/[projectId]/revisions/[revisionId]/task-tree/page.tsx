// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The task tree of a revision (FBS-4.3.5, WF-PLA-0110, US-0220), a leaf of the planning with a
 * screen of its own, whose head leads here in the same context: the banner of its reading context
 * (WF-IHM-0020), the depth to show, chosen by links that write the address (`depth`), and the tree
 * of the summaries of the main structure under the root of the project, read and never entered
 * (`TaskTree`). The tasks are read as the grid of the planning reads them — the tasks alone,
 * restricted to the filtered sub-project (`grid-screen.ts`) —, the server selecting the summaries
 * down to the depth asked (`summaries_only`, `max_level`, #463), the tree keeping them once more
 * against the fake back (`summaryTree`); of each the fields the tree reads. The levels to choose
 * are those the structure has, as the server says them (`meta.summary_depth`, #494).
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { ContextBanner } from "@/components/context/context-banner";
import { FUNCTION_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import {
  depthHref,
  depthShown,
  readDepth,
  summaryTree,
  type TreeNode,
} from "@/components/tree/summaries";
import { TaskTree } from "@/components/tree/task-tree";
import { buttonVariants } from "@/components/ui/button";
import { type PageSearchParams, searchQuery } from "@/navigation/context";

import { screenMetadata } from "../../../../../title";
import { gridAddress, readGridScreen } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the leaf, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.taskTree", projectId);
}

/** What the tree reads of a node, beyond what every reading of the structure reads: its parent. */
const TREE_FIELDS = { node: ["parent_id"], task: [], line: [] } as const;

/** The depths the tree may show, each a link to it, the one shown marked as the current one. */
function Depths({
  levels,
  depth,
  href,
}: {
  readonly levels: number;
  readonly depth: number;
  readonly href: (depth: number) => string;
}) {
  const t = useTranslations("taskTree");
  if (levels === 0) {
    return null;
  }
  return (
    <nav aria-label={t("depths")} className="flex flex-wrap items-center gap-1 text-sm">
      {Array.from({ length: levels }, (_, at) => at + 1).map((level) => (
        <Link
          key={level}
          href={href(level)}
          aria-current={level === depth ? "true" : undefined}
          className={buttonVariants({
            variant: level === depth ? "default" : "outline",
            size: "sm",
          })}
        >
          {t("depth", { level })}
        </Link>
      ))}
    </nav>
  );
}

/** The head of the screen, the depths and the tree. */
function TaskTreeScreen({
  project,
  nodes,
  levels,
  depth,
  href,
}: {
  readonly project: string;
  readonly nodes: readonly TreeNode[];
  readonly levels: number;
  readonly depth: number;
  readonly href: (depth: number) => string;
}) {
  const t = useTranslations();
  return (
    <Screen density={FUNCTION_DENSITY.planning}>
      <PageHeader
        title={t("functions.taskTree")}
        icon={LEAF_ICONS["FBS-4.3.5"]}
        density={FUNCTION_DENSITY.planning}
        subtitle={t("taskTree.summary")}
        actions={<Depths levels={levels} depth={depth} href={href} />}
      />
      <TaskTree name={t("taskTree.name")} project={project} nodes={nodes} />
      {levels === 0 ? (
        <p className="text-sm text-muted-foreground">{t("taskTree.noSummary")}</p>
      ) : null}
    </Screen>
  );
}

/** Render the task tree of the main structure of a revision. */
export default async function TaskTreePage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "task-tree");
  const asked = readDepth(at.address);
  const screen = await readGridScreen(at, {
    key: "task_tree",
    sortable: [],
    kinds: ["task"],
    narrowed: { summaries_only: true, max_level: asked },
    fields: TREE_FIELDS,
  });
  const levels = screen.summaryDepth;
  const depth = depthShown(levels, asked);
  const query = searchQuery(search);
  return (
    <>
      <ContextBanner reading={screen.reading} />
      <TaskTreeScreen
        project={screen.reading.project.label}
        nodes={summaryTree(screen.nodes.items, depth)}
        levels={levels}
        depth={depth}
        href={(level) => depthHref(at.pathname, query, level)}
      />
    </>
  );
}
