// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The two commands of a risk that end it, each asking a confirmation in the page (US-0520,
 * WF-RIS-0020, WF-RIS-0060, WF-IHM-0110): « Supprimer le risque » and « Déclarer survenu ». Each
 * follows the command as the risk lists it — absent, nothing; unavailable, described by the
 * conditions it lacks: `risk_not_cited` for a risk a marked revision cites, which is dismissed rather
 * than deleted, `risk_not_occurred` and `risk_identified` for a risk occurred or dismissed —; the
 * server judges it all the same, and its refusal (`risk_delete_cited`) is told under the confirmation.
 *
 * A risk deleted is gone: the screen leaves its detail for the address without it, the page not being
 * read anew for a risk it can no longer find. A risk declared occurred is handed to the worker, which
 * merges its own estimate into the main structure and withdraws its line of provision (202): the
 * tracker of the shell follows the task (WF-IHM-0080), and once it has succeeded the screen says so and
 * is read anew, the risk then listing no command of entry.
 *
 * « Déclarer survenu » first reads the report of the occurrence (`getRiskOccurrenceReport`, US-0680)
 * and presents it in the confirmation (`occurrence-report.tsx`); it confirms with the counters of the
 * report shown (`declareRiskOccurrence`), and offers it only while the report carries no motive of
 * refusal. A report gone stale (412) offers to read it anew. A task of the worker that failed is not
 * run again from the tracker, which would confirm counters read before: the entry says to start again
 * from the screen of the risk, where the command reads the report anew and shows it.
 */
"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";

import { declareRiskOccurrence, deleteRisk } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { findOffer } from "@/components/commands/offer";
import { DoneNotice } from "@/components/notices/done-notice";
import { Following } from "@/components/tasks/following";

import { type OccurrenceReport, OccurrencePanel } from "./occurrence-report";
import { useRiskNavigation } from "./risk-cells";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** « Supprimer le risque », as the risk lists `delete`; once done, the screen leaves the risk. */
export function DeleteRisk({
  projectId,
  risk,
}: {
  readonly projectId: string;
  readonly risk: Risk;
}) {
  const t = useTranslations("riskDelete");
  const helps = useTranslations("commands");
  const router = useRouter();
  const { href } = useRiskNavigation(undefined);
  const offer = findOffer(risk.available_commands, "delete");
  if (offer === undefined) {
    return null;
  }
  return (
    <ConfirmedCommand
      offer={offer}
      label={t("label")}
      help={helps("deleteRisk.help")}
      icon={<Trash2 aria-hidden="true" />}
      statement={t("statement")}
      submit={t("submit")}
      names={{}}
      subject={risk.label}
      run={() => deleteRisk(projectId, risk.risk_id, risk.lock_version)}
      done={() => t("done", { name: risk.label })}
      onDone={() => {
        router.push(href);
      }}
    />
  );
}

/** « Déclarer survenu », as the risk lists `declare_occurrence`; the tracker follows the task. */
export function DeclareOccurrence({
  projectId,
  risk,
}: {
  readonly projectId: string;
  readonly risk: Risk;
}) {
  const t = useTranslations("riskOccurrence");
  const reading = useTranslations("riskOccurrenceReport");
  const helps = useTranslations("commands");
  const [report, setReport] = useState<Outcome<OccurrenceReport>>();
  const [attempt, setAttempt] = useState(0);
  const [followed, setFollowed] = useState<BackgroundTask>();
  const [succeeded, setSucceeded] = useState<{ readonly name: string }>();
  // Kept as it was read: what the confirmation carries is the report it shows.
  const onRead = useCallback((next: Outcome<OccurrenceReport> | undefined) => {
    setReport(next);
  }, []);
  const offer = findOffer(risk.available_commands, "declare_occurrence");
  if (offer === undefined) {
    return null;
  }
  const read = report?.kind === "done" ? report.data : undefined;
  const run = () =>
    read === undefined
      ? Promise.reject(new Error("the occurrence is confirmed once its report is read"))
      : declareRiskOccurrence(projectId, risk.risk_id, {
          mainStructureLockVersion: read.main_structure_lock_version,
          riskLockVersion: read.risk_lock_version,
          createsCurrentRevision: read.creates_current_revision,
        });
  return (
    <div className="space-y-2">
      <ConfirmedCommand
        offer={offer}
        label={t("label")}
        help={helps("project.declare_risk_occurrence.help")}
        icon={commandIcon(PROJECT_COMMAND_ICONS.declare_risk_occurrence)}
        statement={t("statement")}
        submit={t("submit")}
        ready={read?.refusals.length === 0}
        names={{}}
        subject={risk.label}
        run={run}
        done={() => t("queued", { name: risk.label })}
        onDone={(task) => {
          setFollowed(task);
        }}
        reread={{
          label: reading("reread"),
          run: () => {
            setAttempt(attempt + 1);
          },
        }}
      >
        <OccurrencePanel
          projectId={projectId}
          riskId={risk.risk_id}
          subject={risk.label}
          attempt={attempt}
          report={report}
          onRead={onRead}
          names={{}}
        />
      </ConfirmedCommand>
      {followed === undefined ? null : (
        <Following
          key={followed.task_id}
          task={followed}
          subject={risk.label}
          onSucceeded={() => {
            setSucceeded({ name: risk.label });
          }}
        />
      )}
      <DoneNotice
        title={succeeded === undefined ? undefined : t("succeeded", succeeded)}
        of={succeeded}
        subject={risk.label}
      />
    </div>
  );
}
