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
 * is read anew, the risk then listing no command of entry. The report of the merge before the
 * confirmation has no source in the contract (#1383): the confirmation says what the declaration does,
 * and shows no report.
 */
"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { declareRiskOccurrence, deleteRisk } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { BackgroundTask, Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { findOffer } from "@/components/commands/offer";
import { DoneNotice } from "@/components/notices/done-notice";
import { Following } from "@/components/tasks/following";

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

/** A declaration handed to the worker: its task, and the command that runs it again. */
interface Declared {
  readonly task: BackgroundTask;
  readonly command: () => Promise<Outcome<BackgroundTask>>;
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
  const helps = useTranslations("commands");
  const [followed, setFollowed] = useState<Declared>();
  const [succeeded, setSucceeded] = useState<{ readonly name: string }>();
  const offer = findOffer(risk.available_commands, "declare_occurrence");
  if (offer === undefined) {
    return null;
  }
  const run = () => declareRiskOccurrence(projectId, risk.risk_id);
  return (
    <div className="space-y-2">
      <ConfirmedCommand
        offer={offer}
        label={t("label")}
        help={helps("project.declare_risk_occurrence.help")}
        icon={commandIcon(PROJECT_COMMAND_ICONS.declare_risk_occurrence)}
        statement={t("statement")}
        submit={t("submit")}
        names={{}}
        subject={risk.label}
        run={run}
        done={() => t("queued", { name: risk.label })}
        onDone={(task) => {
          setFollowed({ task, command: run });
        }}
      />
      {followed === undefined ? null : (
        <Following
          key={followed.task.task_id}
          task={followed.task}
          subject={risk.label}
          command={followed.command}
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
