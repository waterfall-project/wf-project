// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The update of an amendment, or of the own estimate of a risk, in arrears (US-2640, US-3050, US-3140,
 * #4034), from the grid of its structure: the main structure has received writes since its base, and
 * the merge of an amendment is not offered before it carries them. The command opens a confirmation in the page, which
 * first reads the report of the update (`getStructureRebaseReport`) and presents it — what the main
 * structure received and the update carries into the differential, `added`, `updated`, `removed`;
 * what the differential keeps, `kept`, with the fields it keeps; the motives that refuse it, with
 * which the update cannot be confirmed —, then confirms with the two counters the report read
 * (`rebaseCostStructure`) — an own estimate shows the severity and the provision recomputed besides —; the page is read anew, the grid with it. A report gone stale (412) offers
 * to read it anew. Abandoning sends nothing: the report is a read.
 *
 * The front computes nothing of the report: the differences are in the order received, the counts are
 * the lengths of what the server rendered.
 */
"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { readRebaseReport, rebaseStructure } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, STRUCTURE_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";

import { type RebaseNature, ReportBody, type Report } from "./rebase-report";

/** The structure an update is about — an amendment or the own estimate of a risk —, and where it is. */
export interface RebasedStructure {
  readonly projectId: string;
  readonly revisionId: string;
  readonly structureId: string;
  readonly label: string;
  readonly nature: RebaseNature;
}

const HEADING = "text-sm font-semibold";

/** What the form shows of the report, read when it opens and read anew on demand. */
function ReportPanel({
  structure,
  attempt,
  report,
  onRead,
  names,
}: {
  readonly structure: RebasedStructure;
  readonly attempt: number;
  readonly report: Outcome<Report> | undefined;
  readonly onRead: (report: Outcome<Report> | undefined) => void;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("rebaseReport");
  const { projectId, revisionId, structureId } = structure;
  useEffect(() => {
    let current = true;
    onRead(undefined);
    void readRebaseReport(projectId, revisionId, structureId).then((read) => {
      if (current) {
        onRead(read);
      }
    });
    return () => {
      current = false;
    };
  }, [projectId, revisionId, structureId, attempt, onRead]);
  return (
    <section aria-label={t("title")} aria-busy={report === undefined} className="space-y-2">
      <h2 className={HEADING}>{t("title")}</h2>
      {report === undefined ? <p role="status">{t("reading")}</p> : null}
      {report?.kind === "done" ? (
        <ReportBody report={report.data} nature={structure.nature} />
      ) : null}
      {report !== undefined && report.kind !== "done" ? (
        <OutcomeNotice
          outcome={report}
          names={names}
          subject={structure.label}
          onClear={() => {
            onRead(undefined);
          }}
        />
      ) : null}
    </section>
  );
}

/** Offer the update of the amendment or the own estimate a grid reads, when its structure lists `rebase` available. */
export function RebaseStructureCommand({
  offer,
  structure,
  names,
}: {
  readonly offer: CommandOffer;
  readonly structure: RebasedStructure;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("rebaseReport");
  const helps = useTranslations("commands");
  const own = structure.nature === "risk";
  const [report, setReport] = useState<Outcome<Report>>();
  const [attempt, setAttempt] = useState(0);
  const read = report?.kind === "done" ? report.data : undefined;
  const onRead = useCallback((next: Outcome<Report> | undefined) => {
    setReport(next);
  }, []);
  const { projectId, revisionId, structureId } = structure;
  const run = () =>
    read === undefined
      ? Promise.reject(new Error("the update is confirmed once its report is read"))
      : rebaseStructure(projectId, revisionId, structureId, {
          mainStructureLockVersion: read.main_structure_lock_version,
          structureLockVersion: read.structure_lock_version,
        });
  return (
    <ConfirmedCommand
      offer={offer}
      label={t(own ? "labelOwn" : "label")}
      help={helps(own ? "structure.rebaseOwn.help" : "structure.rebase.help")}
      icon={commandIcon(STRUCTURE_COMMAND_ICONS.rebase)}
      statement={t(own ? "statementOwn" : "statement")}
      submit={t("submit")}
      ready={read?.refusals.length === 0}
      names={names}
      subject={structure.label}
      run={run}
      done={() => t(own ? "doneOwn" : "done", { label: structure.label })}
      reread={{
        label: t("reread"),
        run: () => {
          setAttempt(attempt + 1);
        },
      }}
    >
      <ReportPanel
        structure={structure}
        attempt={attempt}
        report={report}
        onRead={onRead}
        names={names}
      />
    </ConfirmedCommand>
  );
}
