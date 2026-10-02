// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The history of the revisions of a project (FBS-4.1, US-0210), in the order the server gives
 * it: each revision by its version name — the draft, which has none yet, as the current
 * revision —, its status, whether it is the reference, when it was marked, and its description
 * (WF-REV-0090). Its name shows it on the screen of the revisions — its commands, its structures,
 * its proposal of rates —, the one shown marked as current; a link opens it, its planning and its
 * estimate as they were (WF-REV-0070). Nothing is offered to create or modify: those forms belong
 * to the epic of their domain.
 */
import { ArrowUpRight, GitBranch, Star } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListSection, ListTable } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import { contextQuery, type ProjectContext } from "@/navigation/context";

/** What names a revision: its version name, and its status when it has none. */
export type NamedRevision = Pick<
  components["schemas"]["Revision"],
  "revision_id" | "version_name" | "status"
>;

/** A revision of the history. */
export type HistoryRevision = NamedRevision &
  Pick<components["schemas"]["Revision"], "is_reference" | "marked_at" | "description">;

/**
 * How a screen names a revision: by its version name; without one, the draft as the current
 * revision, and anything else by its status.
 */
export function useRevisionName(): (revision: NamedRevision) => string {
  const t = useTranslations();
  return (revision) =>
    revision.version_name ??
    (revision.status === "draft"
      ? t("contextBanner.currentRevision")
      : t(`enums.RevisionStatus.${revision.status}`));
}

/** The history, and the context of the screen whose links it leads to. */
export interface RevisionHistoryProps {
  readonly revisions: readonly HistoryRevision[];
  /** How many revisions the project has, which the server counts: more than shown is said. */
  readonly total: number;
  /** The context of the screen: the revision it shows, and the filters its links carry on. */
  readonly context: ProjectContext;
}

/** The addresses a revision of the history leads to: shown on this screen, or opened. */
function revisionLinks(context: ProjectContext, revisionId: string) {
  const at = { ...context, revisionId };
  const revisions = `/projects/${context.projectId}/revisions`;
  return {
    shown: `${revisions}${contextQuery(at, true)}`,
    opened: `${revisions}/${revisionId}${contextQuery(at, false)}`,
  };
}

/** A row of the history. */
function HistoryRow({
  revision,
  context,
}: {
  readonly revision: HistoryRevision;
  readonly context: ProjectContext;
}) {
  const t = useTranslations("revisionScreen.history");
  const status = useTranslations("enums.RevisionStatus");
  const name = useRevisionName()(revision);
  const links = revisionLinks(context, revision.revision_id);
  const current = revision.revision_id === context.revisionId;
  return (
    <TableRow>
      <TableCell className={CELL}>
        <span className="inline-flex items-center gap-1.5">
          <GitBranch aria-hidden="true" className={ICON} />
          <Link
            href={links.shown}
            aria-current={current ? "page" : undefined}
            className="underline-offset-4 hover:underline aria-[current=page]:font-semibold"
          >
            {name}
          </Link>
          {revision.is_reference ? (
            <Badge variant="outline">
              <Star aria-hidden="true" />
              {t("reference")}
            </Badge>
          ) : null}
        </span>
      </TableCell>
      <TableCell className={CELL}>
        <Badge>{status(revision.status)}</Badge>
      </TableCell>
      <TableCell className={CELL}>
        {revision.marked_at == null ? t("notMarked") : <LocalTime value={revision.marked_at} />}
      </TableCell>
      <TableCell className={`${CELL} whitespace-normal`}>{revision.description}</TableCell>
      <TableCell className={CELL}>
        <Link
          href={links.opened}
          aria-label={t("openRevision", { name })}
          className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
        >
          <ArrowUpRight aria-hidden="true" className={ICON} />
          {t("open")}
        </Link>
      </TableCell>
    </TableRow>
  );
}

/**
 * Render the history of the revisions of a project, or that it has none; a history the server
 * counts longer than what is shown says so, never truncated in silence.
 */
export function RevisionHistory({ revisions, total, context }: RevisionHistoryProps) {
  const t = useTranslations("revisionScreen.history");
  return (
    <ListSection
      title={t("title")}
      icon={GitBranch}
      empty={revisions.length === 0 ? t("none") : undefined}
    >
      <ListTable
        label={t("title")}
        columns={[t("version"), t("status"), t("markedAt"), t("description"), t("consult")]}
      >
        {revisions.map((revision) => (
          <HistoryRow key={revision.revision_id} revision={revision} context={context} />
        ))}
      </ListTable>
      {total > revisions.length ? (
        <p className="text-sm text-muted-foreground">
          {t("truncated", {
            shown: revisions.length.toString(),
            total: total.toString(),
          })}
        </p>
      ) : null}
    </ListSection>
  );
}
