// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of an import in calendar gap (WF-INTF-0080, WF-PLA-0160): keep the durations, the
 * default, or keep the dates, offered before the application and only when the report bears a
 * calendar gap — `duration_rule` of the report says the option now in force. Changing it asks the
 * API to analyse the import again (`setImportDurationRule`): the import comes back `analysing`
 * (202), its task goes to the tracker of the shell, and the screen is read anew at once; the rule
 * already in force changes nothing, but the screen is read anew (200), as it may be stale.
 * A refusal is told under the choice, kept by this component, which stays mounted when the screen
 * read anew drops the choice; a 409, the import having moved on, reads the screen anew. The project
 * stays unchanged until the confirmation.
 *
 * The end of the analysis of an import — the one a new rule queues as the one its opening queued —
 * reads the screen anew, whichever way it ends, a failed analysis showing as any failed analysis
 * does. It is followed from the task of the import the screen reads while it is `analysing`
 * (`task`), so that it is still followed once the screen was left and come back to, or the page
 * reloaded; the task a 202 has just handed over is followed until the screen read anew says it.
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { type ImportDurationRule, setFileImportDurationRule } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import {
  useTrackTask,
  useWhenTaskFails,
  useWhenTaskSucceeds,
} from "@/components/tasks/task-tracker";

const RULES: readonly ImportDurationRule[] = ["keep_durations", "keep_dates"];

/** The import, the rule in force, and whether the choice is offered. */
export interface DurationRuleProps {
  readonly projectId: string;
  readonly importId: string;
  readonly filename: string;
  /** The rule the report was computed under; none when the report bears no calendar gap. */
  readonly rule: ImportDurationRule | undefined;
  /** Whether the import still awaits its decision, which the choice precedes. */
  readonly awaiting: boolean;
  /** The task that analyses the import, while the screen reads it `analysing`. */
  readonly task?: string | undefined;
}

/** Read the screen anew once the analysis of the import has ended, whichever way. */
function FollowAnalysis({ taskId }: { readonly taskId: string }) {
  const router = useRouter();
  const reread = () => {
    router.refresh();
  };
  useWhenTaskSucceeds(taskId, reread);
  useWhenTaskFails(taskId, reread);
  return null;
}

/**
 * Offer the choice of the rule, and follow the analysis of the import, the one a change of rule
 * starts included. The tracker of the shell is needed only once there is a choice to offer or a
 * task to follow.
 */
export function DurationRule(props: DurationRuleProps) {
  // The task a 202 handed over, until the screen read anew carries it as `task`.
  const [analysis, setAnalysis] = useState<string>();
  if (props.task !== undefined && analysis !== undefined) {
    // The screen has taken over: its task is the one followed, whichever it is, and the one a 202
    // handed over is forgotten, lest it be followed again, its end already read, once the import
    // is read analysed.
    setAnalysis(undefined);
  }
  const followed = props.task ?? analysis;
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  return (
    <>
      {props.rule === undefined || !props.awaiting ? null : (
        <Choice {...props} rule={props.rule} onAnalysing={setAnalysis} onOutcome={setOutcome} />
      )}
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      {followed === undefined ? null : <FollowAnalysis taskId={followed} />}
    </>
  );
}

/** The choice of the rule, the one in force checked. */
function Choice({
  projectId,
  importId,
  filename,
  rule,
  onAnalysing,
  onOutcome,
}: DurationRuleProps & {
  readonly rule: ImportDurationRule;
  readonly onAnalysing: (taskId: string) => void;
  readonly onOutcome: (outcome: Outcome<unknown> | undefined) => void;
}) {
  const t = useTranslations("exchanges.report.durationRule");
  const enums = useTranslations("enums.ImportDurationRule");
  const router = useRouter();
  const track = useTrackTask();
  const name = useId();
  const [busy, setBusy] = useState(false);
  const reread = () => {
    router.refresh();
  };

  const choose = (asked: ImportDurationRule) => {
    if (busy || asked === rule) {
      return;
    }
    setBusy(true);
    onOutcome(undefined);
    void setFileImportDurationRule(projectId, importId, asked)
      .catch(rejected)
      .then((result) => {
        setBusy(false);
        if (result.kind === "done") {
          // 202: the import is analysing again, followed to its end; 200: the rule is already
          // in force, nothing changes, and the screen is read anew in case it was stale.
          if (result.data.status === "analysing") {
            track(result.data.task, { subject: filename });
            onAnalysing(result.data.task.task_id);
          }
          reread();
          return;
        }
        onOutcome(result);
        if (result.kind === "conflict") {
          reread();
        }
      });
  };

  return (
    <fieldset aria-busy={busy} className="space-y-1 text-sm">
      <legend className="text-sm font-semibold">{t("legend")}</legend>
      {RULES.map((each) => (
        <label key={each} className="flex items-start gap-2">
          <input
            type="radio"
            name={name}
            value={each}
            checked={rule === each}
            onChange={() => {
              choose(each);
            }}
            className="mt-1"
          />
          <span>{t("option", { rule: enums(each), hint: t(`hint.${each}`) })}</span>
        </label>
      ))}
    </fieldset>
  );
}
