// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the cycle of the revisions that the screen of the revisions wires beside the
 * marking (US-0490): the opening of the current revision, which the project lists
 * (`create_revision`) and which leads to the revision created; the abandon of the current revision,
 * which the revision lists (`abandon`), with a confirmation that says the project returns to its
 * last marked revision and that nothing undoes it (WF-IHM-0110); the designation of a marked
 * revision as the reference, which the revision lists (`designate_reference`), with a confirmation
 * that says what it fixes and that the project goes in progress if it bears its code
 * (WF-CYC-0030). Each is offered as the server lists it, available or naming what it lacks
 * (WF-IHM-0090); the refusal the server may still oppose is told under it, naming the condition.
 * The page is read again once a write is answered, so that the state of the project, its banner and
 * the read only of the estimate follow what the server now renders.
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  abandonRevision,
  createRevision,
  designateReferenceRevision,
} from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";

import { Command } from "./command";
import { ConfirmedCommand } from "./confirmed-command";
import { commandIcon, PROJECT_COMMAND_ICONS, REVISION_COMMAND_ICONS } from "./icons";
import type { CommandOffer } from "./offer";
import type { ObjectNames } from "./outcome-notice";

/** A revision a command is about: where it is, and how the screen names it. */
export interface RevisionSubject {
  readonly projectId: string;
  readonly revisionId: string;
  readonly name: string;
}

/** The path of the screen of the revisions of a project, with a revision read, if one is named. */
function revisionsPath(projectId: string, revisionId?: string): string {
  const path = `/projects/${projectId}/revisions`;
  return revisionId === undefined ? path : `${path}?revision_id=${revisionId}`;
}

/**
 * Offer the opening of the current revision, as the project lists it; opened, the screen leads to
 * the revision created. The rate update the API proposes stays a proposal, applied from the revision.
 */
export function CreateRevisionCommand({
  offer,
  projectId,
  names,
}: {
  readonly offer: CommandOffer;
  readonly projectId: string;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("revisionCommands");
  const router = useRouter();
  return (
    <Command
      offer={offer}
      label={t("create")}
      icon={commandIcon(PROJECT_COMMAND_ICONS.create_revision)}
      names={names}
      subject={names[projectId]}
      action={async () => {
        const outcome: Outcome<{ readonly revision_id: string }> = await createRevision(projectId, {
          apply_rate_update: false,
        });
        if (outcome.kind === "done") {
          router.push(revisionsPath(projectId, outcome.data.revision_id));
        }
        return outcome;
      }}
    />
  );
}

/**
 * Offer the abandon of the current revision, confirmed; abandoned, the screen leaves the address of
 * the revision, which is no more, for the revisions of the project.
 */
export function AbandonCommand({
  offer,
  revision,
  names,
}: {
  readonly offer: CommandOffer;
  readonly revision: RevisionSubject;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("revisionCommands");
  const router = useRouter();
  const [left, setLeft] = useState(false);
  // After the status is told, and noted, in the same commit: its effect comes first.
  useEffect(() => {
    if (left) {
      router.replace(revisionsPath(revision.projectId));
    }
  }, [left, router, revision.projectId]);
  return (
    <ConfirmedCommand
      offer={offer}
      label={t("abandon.label")}
      icon={commandIcon(REVISION_COMMAND_ICONS.abandon)}
      statement={t("abandon.statement")}
      submit={t("abandon.submit")}
      names={names}
      subject={revision.name}
      run={() => abandonRevision(revision.projectId, revision.revisionId)}
      done={() => t("abandon.done")}
      onDone={() => {
        setLeft(true);
      }}
    />
  );
}

/** Offer the designation of a marked revision as the reference, confirmed. */
export function DesignateCommand({
  offer,
  revision,
  names,
}: {
  readonly offer: CommandOffer;
  readonly revision: RevisionSubject;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("revisionCommands");
  const state = useTranslations("enums.ProjectState");
  return (
    <ConfirmedCommand
      offer={offer}
      label={t("designate.label")}
      icon={commandIcon(REVISION_COMMAND_ICONS.designate_reference)}
      statement={t("designate.statement", { name: revision.name, state: state("in_progress") })}
      submit={t("designate.submit")}
      names={names}
      subject={revision.name}
      run={() => designateReferenceRevision(revision.projectId, revision.revisionId)}
      done={(project) => t("designate.done", { name: revision.name, state: state(project.state) })}
    />
  );
}
