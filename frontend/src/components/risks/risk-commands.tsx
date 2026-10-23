// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the risks that open the form of a risk (US-0520, WF-IHM-0090): « Identifier un
 * risque » on the screen of the risks, and « Modifier » in the detail of a risk.
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
 * the screen it was sent from. The modification answered is shown in the detail while it is newer
 * than the risk read; the page is read anew.
 *
 * Every prop is data, never a function: a server component hands it over (défaut n° 12 de
 * `typescript.md`). The address of the estimate is the base the structure is added to.
 */
"use client";

import { Pencil } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactElement, type Ref, useEffect, useId, useRef, useState } from "react";

import type { components } from "@/api/generated/schema";
import { Command, useUnmet } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import { type CommandOffer, findOffer, UNAVAILABLE } from "@/components/commands/offer";
import { STRUCTURE_PARAMETER } from "@/components/context/structure";
import { filterHref } from "@/components/grid/filters";
import { useSaid } from "@/components/notices/said";
import { Reactivations } from "@/components/reference/reactivation";
import { WritingNote } from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";

import type { ProvisionOptions } from "./provision-choices";
import { RiskForm } from "./risk-form";

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
 * The form a command opens, and what it keeps of its openings: how many there were, which is open,
 * whether a write is under way, and the control to give the focus back to once it has closed.
 */
function useRiskDialog() {
  const [open, setOpen] = useState<number>();
  const [writing, setWriting] = useState(false);
  // How many times the form was opened: what tells an opening from the next.
  const openings = useRef(0);
  // The opening that is open, set as it opens and closes — never in an effect, which a late answer
  // would pass before.
  const current = useRef<number>(undefined);
  // Whether the screen the form was opened on is still shown, which a declaration answered leads from.
  const shown = useRef(true);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
  return {
    open,
    writing,
    setWriting,
    trigger,
    shown,
    current,
    opening: () => {
      if (writing) {
        return;
      }
      openings.current += 1;
      current.current = openings.current;
      setOpen(openings.current);
    },
    close: () => {
      current.current = undefined;
      setOpen(undefined);
    },
  };
}

/**
 * A command that opens a form, as its object lists it: nothing when absent; the plain unavailable
 * command with the conditions it lacks; available, a button that opens, inactive and described by
 * « Enregistrement en cours… » while a write of the form is under way.
 */
function OpensForm({
  offer,
  label,
  icon,
  writing,
  trigger,
  onOpen,
}: {
  readonly offer: CommandOffer | undefined;
  readonly label: string;
  readonly icon: ReactElement;
  readonly writing: boolean;
  readonly trigger: Ref<HTMLButtonElement>;
  readonly onOpen: () => void;
}) {
  const why = useId();
  if (offer === undefined) {
    return null;
  }
  if (!offer.is_available) {
    return <Command offer={offer} label={label} icon={icon} />;
  }
  return (
    <div className="space-y-1">
      <Button
        ref={trigger}
        type="button"
        variant="outline"
        size="sm"
        aria-disabled={writing ? true : undefined}
        aria-busy={writing}
        aria-describedby={writing ? why : undefined}
        className={UNAVAILABLE}
        onClick={onOpen}
      >
        {icon}
        {label}
      </Button>
      <WritingNote id={why} writing={writing} />
    </div>
  );
}

/** The status the last write of a command said, read out by a reader of the screen. */
function Status({
  said,
}: {
  readonly said: { readonly text: string; readonly count: number } | undefined;
}) {
  return (
    <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
      {said === undefined ? null : <span key={said.count}>{said.text}</span>}
    </p>
  );
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
 * « Modifier », in the detail of a risk, as the risk lists `update`, and its form; the category, the
 * sub-project and the task of its provision follow `update_provision`.
 */
export function ModifyRisk({
  projectId,
  risk,
  options,
}: {
  readonly projectId: string;
  readonly risk: Risk;
  /** What the provision is chosen among; read while the risk lists `update` available. */
  readonly options: ProvisionOptions | undefined;
}) {
  const t = useTranslations("riskForm");
  const unmet = useUnmet();
  const dialog = useRiskDialog();
  const [said, say] = useSaid();
  const [answered, setAnswered] = useState<Risk>();
  const { open, current } = dialog;
  // The answer is shown while newer than the risk read: a form opened again writes from its version.
  const shown =
    answered?.risk_id === risk.risk_id && answered.lock_version > risk.lock_version
      ? answered
      : risk;
  const provision = findOffer(shown.available_commands, "update_provision");
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <Status said={said} />
        <OpensForm
          offer={findOffer(shown.available_commands, "update")}
          label={t("modify")}
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
          risk={shown}
          provisionOpen={provision?.is_available === true}
          unmet={
            provision === undefined || provision.missing_conditions.length === 0
              ? undefined
              : unmet(provision)
          }
          options={options ?? NO_OPTIONS}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
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
