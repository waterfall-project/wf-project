// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The history of the revisions of a project (FBS-4.1, US-0210), in the order the server gives
 * it: each revision by its version name — the draft, which has none yet, as the current
 * revision —, its status, whether it is the reference, when it was marked, its reference year, the
 * revision it is a copy of, the inflation rate and the win probability it keeps — those of its
 * marking when it is marked (WF-REV-0070) —, and its description (WF-REV-0090). Its name shows it on the screen of the revisions — its commands, its structures,
 * its proposal of rates —, the one shown marked as current; a link opens it, its planning and its
 * estimate as they were (WF-REV-0070). Each marked revision that lists `designate_reference` offers
 * the designation of the reference as a command of its row (WF-REV-0040, US-2370): available, or
 * unavailable and naming in its tooltip the conditions it lacks — the refusal of a correction no
 * longer permitted, of a revision without task or line of estimate (WF-CYC-0030). Each marked
 * revision but the one read offers « Comparer à la révision lue » (US-2370): a menu of the grids of
 * the planning, of the estimate and of the remaining to commit the user may read, which leads to the
 * one chosen, the revision of the row as its base.
 */
import { ArrowUpRight, GitBranch, Star } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { CreateRevisionCommand, DesignateCommand } from "@/components/commands/revision-commands";
import type { Project } from "@/components/context/reading";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListCard, ListTable } from "@/components/projects/project-tables";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatPercent } from "@/i18n/format";
import { contextQuery, type ProjectContext } from "@/navigation/context";
import {
  functionHref,
  functionOf,
  type NavigationFunction,
  readableGroups,
} from "@/navigation/functions";

import { type ComparisonGrid, CompareCommand } from "./compare-command";

type PermissionCode = components["schemas"]["PermissionCode"];

/** What names a revision: its version name, and its status when it has none. */
export type NamedRevision = Pick<
  components["schemas"]["Revision"],
  "revision_id" | "version_name" | "status"
>;

/** A revision of the history, with the commands it lists. */
export type HistoryRevision = NamedRevision &
  Pick<
    components["schemas"]["Revision"],
    | "available_commands"
    | "is_reference"
    | "marked_at"
    | "reference_year"
    | "description"
    | "source_version_name"
    | "inflation_rate"
    | "win_probability"
  >;

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
  /** Every revision of the project, read whole (`readEveryPage`). */
  readonly revisions: readonly HistoryRevision[];
  /** The context of the screen: the revision it shows, and the filters its links carry on. */
  readonly context: ProjectContext;
  /** The counter of the project as the page read it, which the designation of the reference carries. */
  readonly projectLockVersion: number;
  /** The permissions of the session, which the grids « Comparer à la révision lue » offers follow. */
  readonly permissions: readonly PermissionCode[];
  /**
   * The opening of the current revision, as the project lists it, which the card offers as its
   * principal command; none, and the card offers none (the caller may not exercise it).
   */
  readonly creation?: RevisionCreation | undefined;
}

/** What opening the current revision takes: the offer of the project, and its name. */
export interface RevisionCreation {
  readonly offer: CommandOffer;
  readonly project: Pick<Project, "project_id" | "label">;
}

/**
 * The opening of the current revision of a project, when the project lists it — available, or
 * naming what it lacks (WF-IHM-0090) —; `undefined` when the caller may not exercise it.
 */
export function revisionCreation(project: Project): RevisionCreation | undefined {
  const offer = findOffer(project.available_commands, "create_revision");
  return offer === undefined ? undefined : { offer, project };
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

/** The grids that compare, in the order of the FBS: the planning, the estimate, the remaining. */
const COMPARING = ["planning", "estimate", "remaining"] as const;

/**
 * The grids a session may read that compare, each at the address of the revision read with a
 * revision as its base (US-2330); none when no revision is read, which no grid can be opened in.
 */
function comparisonGrids(
  context: ProjectContext,
  base: string,
  permissions: readonly PermissionCode[],
  name: (label: NavigationFunction["label"]) => string,
): ComparisonGrid[] {
  const readable = new Set(
    readableGroups(permissions).flatMap((group) => group.functions.map((fn) => fn.permission)),
  );
  return COMPARING.filter((permission) => readable.has(permission)).flatMap((permission) => {
    const fn = functionOf(permission);
    const href = functionHref(fn, { ...context, base });
    return href === undefined ? [] : [{ key: permission, label: name(fn.label), href }];
  });
}

/** A row of the history. */
function HistoryRow({
  revision,
  context,
  projectLockVersion,
  permissions,
}: {
  readonly revision: HistoryRevision;
  readonly context: ProjectContext;
  readonly projectLockVersion: number;
  readonly permissions: readonly PermissionCode[];
}) {
  const t = useTranslations("revisionScreen.history");
  const status = useTranslations("enums.RevisionStatus");
  const locale = useLocale();
  const name = useRevisionName()(revision);
  const links = revisionLinks(context, revision.revision_id);
  const current = revision.revision_id === context.revisionId;
  const designation = findOffer(revision.available_commands, "designate_reference");
  const global = useTranslations();
  // A marked revision other than the one read, which a grid the user may read can be compared to.
  const grids =
    revision.status === "marked" && !current
      ? comparisonGrids(context, revision.revision_id, permissions, (label) => global(label))
      : [];
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
      <TableCell className={`${CELL} tabular-nums`}>{revision.reference_year}</TableCell>
      <TableCell className={CELL}>{revision.source_version_name ?? t("noSource")}</TableCell>
      <TableCell className={`${CELL} tabular-nums`}>
        {formatPercent(revision.inflation_rate, locale)}
      </TableCell>
      <TableCell className={`${CELL} tabular-nums`}>
        {formatPercent(revision.win_probability, locale)}
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
      <TableCell className={`${CELL} whitespace-normal`}>
        {grids.length === 0 ? null : (
          <CompareCommand
            label={t("compare")}
            name={t("compareRevision", { name })}
            grids={grids}
          />
        )}
        {revision.status === "marked" && designation !== undefined ? (
          <DesignateCommand
            offer={designation}
            revision={{
              projectId: context.projectId,
              revisionId: revision.revision_id,
              name,
            }}
            projectLockVersion={projectLockVersion}
            names={{ [revision.revision_id]: name }}
          />
        ) : null}
      </TableCell>
    </TableRow>
  );
}

/** Render the history of the revisions of a project, or that it has none. */
export function RevisionHistory({
  revisions,
  context,
  projectLockVersion,
  permissions,
  creation,
}: RevisionHistoryProps) {
  const t = useTranslations("revisionScreen.history");
  return (
    <ListCard
      title={t("title")}
      icon={GitBranch}
      empty={revisions.length === 0 ? t("none") : undefined}
      principal={
        creation === undefined
          ? undefined
          : {
              does: "create",
              command: (variant) => (
                <CreateRevisionCommand
                  offer={creation.offer}
                  projectId={creation.project.project_id}
                  names={{ [creation.project.project_id]: creation.project.label }}
                  variant={variant}
                />
              ),
            }
      }
    >
      <ListTable
        label={t("title")}
        columns={[
          t("version"),
          t("status"),
          t("markedAt"),
          t("referenceYear"),
          t("source"),
          t("inflationRate"),
          t("winProbability"),
          t("description"),
          t("consult"),
          t("commands"),
        ]}
      >
        {revisions.map((revision) => (
          <HistoryRow
            key={revision.revision_id}
            revision={revision}
            context={context}
            projectLockVersion={projectLockVersion}
            permissions={permissions}
          />
        ))}
      </ListTable>
    </ListCard>
  );
}
