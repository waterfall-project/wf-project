// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the risks that open the form of a risk (US-0520, WF-IHM-0090): « Identifier un
 * risque » on the screen of the risks, and, in the detail of a risk, « Modifier » with the commands
 * that go with it (`RiskCommands`: « Réexaminer », « Déclarer survenu », « Supprimer le risque »).
 *
 * « Identifier un risque » follows `declare_risk` as the revision lists it: absent, nothing is
 * offered; listed, available or not, it is shown — unavailable, `aria-disabled` and described by the
 * conditions it lacks: the revision marked, a processing under way, no task in the main structure
 * (`at_least_one_task`), no active category of the type provision for risks
 * (`active_provision_category`, WF-RIS-0010) —, a press saying nothing more than the description.
 * The declaration is made by the form (`RiskForm`); the server judges it all the same, and a 409 it
 * opposes is told under the form, which stays open. Once declared, the risk opens its estimate of its
 * own — the structure the server names (`structure_id`) — in the grid of the estimate, where the
 * gestures of the structure apply (WF-RIS-0030, US-0500, US-0460), for a session that may read the
 * estimate; for another, the screen says the risk declared and stays.
 *
 * « Modifier » follows `update` as the risk lists it, and the form `update_provision` for the
 * category, the sub-project and the task of its provision (`RiskForm`). Both commands wait, inactive
 * and saying why, while a write of their form is under way — its dialog closed — (défaut n° 24 de
 * `typescript.md`): a form opened anew would write from the version the answer is about to replace.
 * An answer closes the opening it was sent from, never one opened since, and leads away only from
 * the screen it was sent from. The modification answered is shown by the command and its form while it
 * is newer than the risk read; the page is read anew.
 *
 * Every prop is data, never a function: a server component hands it over (défaut n° 12 de
 * `typescript.md`). The address of the estimate is the base the structure is added to.
 */
"use client";

import { Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type { components } from "@/api/generated/schema";
import { useUnmet } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { STRUCTURE_PARAMETER } from "@/components/context/structure";
import { filterHref } from "@/components/grid/filters";
import { useSaid } from "@/components/notices/said";
import { Reactivations } from "@/components/reference/reactivation";

import type { ProvisionOptions } from "./provision-choices";
import { OpensForm, Status, useRiskDialog } from "./risk-dialog";
import { RiskForm } from "./risk-form";
import { DeclareOccurrence, DeleteRisk } from "./risk-lifecycle";
import { ReviewRisk } from "./risk-review";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** The choices of a provision when the screen read none: the form asks nothing of the provision. */
const NO_OPTIONS: ProvisionOptions = { categories: [], subprojects: [], tasks: [] };

/**
 * The address of the estimate of a structure: the address of the estimate of the revision, its
 * reading context kept, and the structure the server named.
 */
function estimateOf(base: string, structure: string): string {
  const [path = "", query = ""] = base.split("?");
  return filterHref(path, new URLSearchParams(query), STRUCTURE_PARAMETER, structure);
}

/**
 * « Identifier un risque », as `declare_risk` lists it, and its form; once declared, the risk opens
 * its own estimate in the grid of the estimate (`estimate`, none for a session that may not read it).
 */
export function IdentifyRisk({
  projectId,
  offer,
  options,
  estimate,
}: {
  readonly projectId: string;
  /** What the revision lists of `declare_risk`; none, and the command is not offered. */
  readonly offer: CommandOffer | undefined;
  /** What the provision is chosen among; read while the command is available. */
  readonly options: ProvisionOptions | undefined;
  /** The address of the estimate of the revision, the structure of the risk added to it. */
  readonly estimate: string | undefined;
}) {
  const t = useTranslations("riskForm");
  const helps = useTranslations("commands");
  const router = useRouter();
  const dialog = useRiskDialog();
  const [said, say] = useSaid();
  const { open, current, shown } = dialog;
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <Status said={said} />
        <OpensForm
          offer={offer}
          label={t("identify")}
          help={helps("revision.declare_risk.help")}
          icon={commandIcon(REVISION_COMMAND_ICONS.declare_risk)}
          writing={dialog.writing}
          trigger={dialog.trigger}
          onOpen={dialog.opening}
        />
      </div>
      {open === undefined ? null : (
        <RiskForm
          key={open}
          projectId={projectId}
          risk={undefined}
          provisionOpen
          unmet={undefined}
          options={options ?? NO_OPTIONS}
          onDone={(risk) => {
            say(t("identified", { name: risk.label }), { object: risk.label });
            // Closed, and left for the estimate of the risk, if it is still the opening the answer was
            // sent from and the screen is still shown, never a later opening.
            if (current.current !== open) {
              return;
            }
            dialog.close();
            if (shown.current && estimate !== undefined) {
              router.push(estimateOf(estimate, risk.structure_id));
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

/**
 * The commands of the detail of a risk — « Modifier », « Réexaminer », « Déclarer survenu » and
 * « Supprimer le risque » — as the risk lists them. What a write of a risk leaves — that it is under
 * way, the answer it brought — outlives the form and the detail of the risk, by risk, for the
 * modification and the review alike, both writing from the version of the risk: the detail shown
 * again finds the commands waiting, and writes from the version answered, never from the one read
 * before (défaut n° 24 de `typescript.md`). The risk the commands present is the answer while it is
 * newer than the risk read, so that the commands a review changes — a risk dismissed no longer
 * declared occurred — follow it before the page is read anew. The dialogs and the statuses are those
 * of the risk shown alone.
 */
export function RiskCommands({
  projectId,
  risk,
  options,
}: {
  readonly projectId: string;
  readonly risk: Risk;
  /** What the provision is chosen among; read while the risk lists `update` or `review` available. */
  readonly options: ProvisionOptions | undefined;
}) {
  const [writes, setWrites] = useState<Readonly<Record<string, Write>>>({});
  const id = risk.risk_id;
  const write = writes[id];
  const answered = write?.answered;
  const shown =
    answered !== undefined && answered.lock_version > risk.lock_version ? answered : risk;
  const onWriting = (writing: boolean) => {
    setWrites((before) => ({ ...before, [id]: { ...before[id], writing } }));
  };
  const onAnswered = (answer: Risk) => {
    setWrites((before) => {
      const held = before[id]?.answered;
      return held === undefined || held.lock_version < answer.lock_version
        ? { ...before, [id]: { writing: before[id]?.writing ?? false, answered: answer } }
        : before;
    });
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-start gap-2">
        <ModifyRiskShown
          key={`modify-${id}`}
          projectId={projectId}
          risk={shown}
          options={options}
          writing={write?.writing ?? false}
          onWriting={onWriting}
          onAnswered={onAnswered}
        />
        <ReviewRisk
          key={`review-${id}`}
          projectId={projectId}
          risk={shown}
          options={options}
          writing={write?.writing ?? false}
          onWriting={onWriting}
          onAnswered={onAnswered}
        />
      </div>
      <DeclareOccurrence key={`declare-${id}`} projectId={projectId} risk={shown} />
      <DeleteRisk key={`delete-${id}`} projectId={projectId} risk={shown} />
    </div>
  );
}

/** What the writes of a risk leave: whether one is under way, and the latest answer. */
interface Write {
  readonly writing: boolean;
  readonly answered?: Risk | undefined;
}

/** « Modifier » of the risk shown: its dialog and its status are its own, and end with it. */
function ModifyRiskShown({
  projectId,
  risk,
  options,
  writing,
  onWriting,
  onAnswered,
}: {
  readonly projectId: string;
  readonly risk: Risk;
  readonly options: ProvisionOptions | undefined;
  readonly writing: boolean;
  readonly onWriting: (writing: boolean) => void;
  readonly onAnswered: (answer: Risk) => void;
}) {
  const t = useTranslations("riskForm");
  const helps = useTranslations("commands");
  const unmet = useUnmet();
  const dialog = useRiskDialog({ writing, setWriting: onWriting });
  const [said, say] = useSaid();
  const { open, current } = dialog;
  const provision = findOffer(risk.available_commands, "update_provision");
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <Status said={said} />
        <OpensForm
          offer={findOffer(risk.available_commands, "update")}
          label={t("modify")}
          help={helps("modifyRisk.help")}
          icon={<Pencil aria-hidden="true" />}
          writing={dialog.writing}
          trigger={dialog.trigger}
          onOpen={dialog.opening}
        />
      </div>
      {open === undefined ? null : (
        <RiskForm
          key={open}
          projectId={projectId}
          risk={risk}
          provisionOpen={provision?.is_available === true}
          unmet={
            provision === undefined || provision.missing_conditions.length === 0
              ? undefined
              : unmet(provision)
          }
          options={options ?? NO_OPTIONS}
          onDone={(answer) => {
            onAnswered(answer);
            say(t("saved", { name: answer.label }), { object: answer.label });
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
