// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Kanban of the start of the tasks (FBS-4.5.3, WF-RAE-0030, US-0230), a leaf of the remaining
 * to commit with a screen of its own, whose head leads here in the same context: the banner of its
 * reading context (WF-IHM-0020), which shows no filter — the Kanban takes none —, and the tasks not
 * started, started and completed, as the API gives them (`listStartableTasks`). The API reads them in the
 * revision in progress of the project, whatever revision the address names: a marked revision,
 * whose tasks it would not show, says so and asks nothing, rather than showing the tasks of another
 * revision under its banner. No percentage is entered, no command offered (`Kanban`).
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { Kanban, type StartableTasks } from "@/components/remaining/kanban";
import { FUNCTION_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";

import { screenMetadata } from "../../../../../title";
import { gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the leaf, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.kanban", projectId);
}

/** The head of the screen, and the Kanban — or why a marked revision shows none. */
function KanbanScreen({ tasks }: { readonly tasks: StartableTasks | undefined }) {
  const t = useTranslations();
  return (
    <Screen density={FUNCTION_DENSITY.remaining}>
      <PageHeader
        title={t("functions.kanban")}
        icon={LEAF_ICONS["FBS-4.5.3"]}
        density={FUNCTION_DENSITY.remaining}
        subtitle={t("kanban.summary")}
      />
      {tasks === undefined ? (
        <p className="text-sm text-muted-foreground">{t("kanban.inProgressOnly")}</p>
      ) : (
        <Kanban tasks={tasks} />
      )}
    </Screen>
  );
}

/** Render the Kanban of the start of the tasks of a project. */
export default async function KanbanPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "kanban");
  const reading = await readProjectContext(at.pathname, at.context, []);
  if (reading === "not_found") {
    notFound();
  }
  const tasks =
    reading.revision?.status === "marked"
      ? undefined
      : await readOrFail("listStartableTasks", () =>
          serverClient().GET("/projects/{project_id}/remaining-indicators/startable-tasks", {
            params: { path: { project_id: revision.projectId } },
          }),
        );
  return (
    <>
      <ContextBanner reading={reading} />
      <KanbanScreen tasks={tasks} />
    </>
  );
}
