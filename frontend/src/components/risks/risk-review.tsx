// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Réexaminer », in the detail of a risk (US-0520, WF-RIS-0010, WF-RIS-0020): the act by which the
 * user confirms or modifies the probability and the state of a risk, dated of the day it is made. The
 * command follows `review` as the risk lists it — absent, nothing; unavailable, described by the
 * conditions it lacks, `risk_not_occurred` for a risk occurred, from which no transition goes —; its
 * form is opened like the others of the risk (`risk-dialog.tsx`).
 *
 * The form starts from the probability and the state the risk holds, so that pressing the button
 * with no change is a confirmation, which the API dates and adds to the history of the reviews. The
 * states it offers are those the contract lets a review retain (`RiskReviewWrite.state`): identified
 * and dismissed, a risk dismissed coming back to identified. A risk dismissed whose category of
 * provision is no longer active (`provision_cost_category_is_active`) is asked another for its return,
 * among the active ones, when there is more than one — one alone is retained without being asked —,
 * and only if the state retained is identified. The probability is entered as a percentage and sent
 * as the ratio of the contract; a refusal by field is said at its field, in percentages; any other —
 * a risk occurred (409), the return refused for want of an active category or of a task, the version
 * stale (412) — is told under the form (`ReferenceForm`), which stays open.
 *
 * The write under way and the answer are those of the commands of the risk (`RiskCommands`), which
 * outlive the detail: this command only tells them.
 */
"use client";

import { RefreshCw } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { reviewRisk } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { findOffer } from "@/components/commands/offer";
import { useSaid } from "@/components/notices/said";
import { ANOTHER_OBJECT } from "@/components/reference/commands";
import { inPercent } from "@/components/reference/in-percent";
import { Reactivations } from "@/components/reference/reactivation";
import { type Draft, type FormField, ReferenceForm } from "@/components/reference/reference-form";
import { editablePercent, percentRatio } from "@/i18n/format";

import type { ProvisionOptions } from "./provision-choices";
import { OpensForm, Status, useRiskDialog } from "./risk-dialog";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** The state a review retains, as the contract names it. */
type Retained = components["schemas"]["RiskReviewWrite"]["state"];

/**
 * Every state a review may retain, in the order of the contract: one the contract adds fails the type
 * check until it is here.
 */
const EVERY_RETAINED: Readonly<Record<Retained, number>> = { identified: 0, dismissed: 1 };

/** The states a review may retain. */
const RETAINED = Object.keys(EVERY_RETAINED) as readonly Retained[];

/** The probability, entered as a percentage: the pointer a refusal names it by. */
const PROBABILITY: ReadonlySet<string> = new Set(["/probability"]);

/** The name of the field that asks the category of the provision of a return, and its pointer. */
const CATEGORY = "provision_cost_category_id";

/** The state a risk is reviewed from: the one it holds. */
function heldState(risk: Risk): Retained {
  return risk.state === "dismissed" ? "dismissed" : "identified";
}

/** The state a form retained: one of the states it offers, never anything else. */
function retainedOf(value: string | undefined): Retained {
  return RETAINED.find((state) => state === value) ?? "identified";
}

/** The form of the review of a risk, in a dialog over its detail. */
function ReviewForm({
  projectId,
  risk,
  categories,
  onDone,
  onWriting,
  onClose,
  onClosed,
}: {
  readonly projectId: string;
  readonly risk: Risk;
  /** The active categories of the type provision for risks, among which a return is asked one. */
  readonly categories: ProvisionOptions["categories"];
  readonly onDone: (answer: Risk) => void;
  readonly onWriting: (writing: boolean) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("riskForm");
  const states = useTranslations("enums.RiskState");
  const detail = useTranslations("risks.detail");
  const locale = useLocale();
  // The category is asked of a risk dismissed whose own is no longer active, when the return has more
  // than one to choose: with one alone the server retains it, with none it refuses the return.
  const asks = risk.state === "dismissed" && !risk.provision_cost_category_is_active;
  const choices = categories.length > 1 && asks ? categories : undefined;
  const fields: FormField[] = [
    { name: "probability", label: t("probability"), control: "number", required: true },
    {
      name: "state",
      label: t("retainedState"),
      control: "choice",
      required: true,
      choices: RETAINED.map((state): readonly [string, string] => [state, states(state)]),
    },
    ...(choices === undefined
      ? []
      : [
          {
            name: CATEGORY,
            label: detail("provisionLine.category"),
            control: "choice",
            required: (draft: Draft) => draft.state === "identified",
            note: t("categoryOnReturn"),
            choices: choices.map(({ id, label }): readonly [string, string] => [id, label]),
          } satisfies FormField,
        ]),
  ];
  const ask = (values: Draft): Promise<Outcome<Risk>> => {
    const { probability = "0", state, [CATEGORY]: category = "" } = values;
    const retained = retainedOf(state);
    // The category is the return's alone: a review that does not return to identified sends none.
    const returning = choices !== undefined && retained === "identified" && category !== "";
    return reviewRisk(projectId, risk.risk_id, {
      probability: percentRatio(probability),
      state: retained,
      lock_version: risk.lock_version,
      ...(returning ? { [CATEGORY]: category } : {}),
    });
  };
  return (
    <ReferenceForm<Risk>
      kind="risk"
      title={t("reviewTitle", { name: risk.label })}
      hint={t("reviewHint")}
      creating={false}
      submit={t("review")}
      fields={fields}
      initial={{
        probability: editablePercent(risk.probability, locale),
        state: heldState(risk),
      }}
      subject={risk.label}
      ask={ask}
      target={`review risk ${risk.risk_id}`}
      answering={(answer) =>
        answer.kind === "done" && answer.data.risk_id !== risk.risk_id
          ? ANOTHER_OBJECT
          : inPercent(answer, PROBABILITY)
      }
      onDone={onDone}
      onWriting={onWriting}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}

/**
 * « Réexaminer » of the risk shown: its dialog and its status are its own, and end with it.
 */
export function ReviewRisk({
  projectId,
  risk,
  options,
  writing,
  onWriting,
  onAnswered,
}: {
  readonly projectId: string;
  readonly risk: Risk;
  /** What the provision is chosen among; read while the risk lists `review` available. */
  readonly options: ProvisionOptions | undefined;
  readonly writing: boolean;
  readonly onWriting: (writing: boolean) => void;
  readonly onAnswered: (answer: Risk) => void;
}) {
  const t = useTranslations("riskForm");
  const helps = useTranslations("commands");
  const dialog = useRiskDialog({ writing, setWriting: onWriting });
  const [said, say] = useSaid();
  const { open, current } = dialog;
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <Status said={said} />
        <OpensForm
          offer={findOffer(risk.available_commands, "review")}
          label={t("review")}
          help={helps("reviewRisk.help")}
          icon={<RefreshCw aria-hidden="true" />}
          writing={dialog.writing}
          trigger={dialog.trigger}
          onOpen={dialog.opening}
        />
      </div>
      {open === undefined ? null : (
        <ReviewForm
          key={open}
          projectId={projectId}
          risk={risk}
          categories={options?.categories ?? []}
          onDone={(answer) => {
            onAnswered(answer);
            say(t("reviewed", { name: answer.label }), { object: answer.label });
            if (current.current === open) {
              dialog.close();
            }
          }}
          onWriting={dialog.setWriting}
          onClose={dialog.close}
          onClosed={() => dialog.trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}
