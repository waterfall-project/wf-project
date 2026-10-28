// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exits of a project and the commands of a revision, in the order the server lists them
 * (`available_commands`): only those the caller may exercise, each available or naming what it
 * lacks (WF-IHM-0090). A marked revision offers no command of modification: the server
 * lists each unavailable, lacking a draft revision (WF-IHM-0020).
 *
 * The marking of a revision is wired: it opens the entry of its version name, and hands the
 * background task it starts to the tracker of the shell (`MarkCommand`); so are the exits of the
 * lifecycle of a project, which open their confirmation (`ExitCommand`), the opening of the
 * current revision and its abandon (`revision-commands.tsx`), the designation of the reference
 * being the history's, on the marked revision; the preparation of an amendment (`create_structure`),
 * which leads to its differential; the merge of an amendment (`merge_structure`) is its grid's, the
 * revision not saying which of its amendments it is about (US-0510). The other commands of a
 * revision come with the forms of their domain, which hand each command its server action; until
 * then a command is shown, and pressing it does nothing. The exports of a revision are the
 * screen of the imports and exports' to offer, where they are asked (`ExportForm`): the list of
 * the commands of a revision leaves them out. So does it the commands a screen of the revision
 * offers itself: its entries, which each grid takes as the revision lists them (`edit_planning`,
 * `edit_estimate`, `edit_remaining`, `edit_risks`), and the skeleton, which the empty grid of the
 * planning offers (EP-14/L44d).
 */
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";

import { Command } from "./command";
import { ExitCommands } from "./exit-command";
import { isExit } from "./exits";
import { commandIcon, REVISION_COMMAND_ICONS } from "./icons";
import { MarkCommand } from "./mark-command";
import { findOffer } from "./offer";
import {
  AbandonCommand,
  CreateRevisionCommand,
  PrepareAmendmentCommand,
} from "./revision-commands";

type RevisionCommand = components["schemas"]["RevisionCommand"];

/** A list of commands, named for what it is; nothing when the caller may exercise none. */
function CommandList({ children }: { readonly children: readonly ReactNode[] }) {
  const t = useTranslations("commands");
  return children.length === 0 ? null : (
    <section aria-label={t("label")}>
      <ul className="flex flex-wrap items-start gap-2">{children}</ul>
    </section>
  );
}

/**
 * The exits of the lifecycle of a project the caller may exercise, in the order of the server:
 * the one command of a project its screens exercise; the others — its settings, its
 * contributors, a revision to create — belong to the forms of their domain (US-0210).
 */
export function LifecycleCommands({ project }: { readonly project: Project }) {
  const exits = project.available_commands.flatMap(({ command, ...offer }) =>
    isExit(command) ? [{ command, offer }] : [],
  );
  return (
    <CommandList>
      {exits.length === 0
        ? []
        : [
            // Keyed by the project: the outcome of a command never outlives its project.
            <ExitCommands
              key={project.project_id}
              exits={exits}
              projectId={project.project_id}
              names={{ [project.project_id]: project.label }}
            />,
          ]}
    </CommandList>
  );
}

/** The commands of a revision an export, an entry of a grid or a screen of its own offers. */
type OfferedElsewhere =
  | `export_${string}`
  | `edit_${string}`
  | "generate_skeleton"
  | "merge_structure"
  | "designate_reference"
  | "apply_rate_update";

/** Whether a command of a revision is an export, which the screen of the exchanges offers. */
function isExport(command: RevisionCommand): boolean {
  return command.startsWith("export_");
}

/**
 * Whether a command of a revision is offered by a screen of its own — an entry, by its grid; the
 * skeleton, by the empty grid of the planning; the designation of the reference, by the history of
 * the revisions, on the marked revision it designates; the application of the rates, by the
 * proposal it applies —, which the list of the commands leaves out.
 */
function isOfferedByItsScreen(command: RevisionCommand): boolean {
  return (
    command.startsWith("edit_") ||
    command === "generate_skeleton" ||
    command === "merge_structure" ||
    command === "designate_reference" ||
    command === "apply_rate_update"
  );
}

/** Whether the list of the commands of a revision presents a command itself. */
export function isListed(
  command: RevisionCommand,
): command is Exclude<RevisionCommand, OfferedElsewhere> {
  return !isExport(command) && !isOfferedByItsScreen(command);
}

/** The command of a revision that has a form of its own, or the plain command it is. */
function RevisionCommandItem({
  offer,
  revision,
  name,
  names,
}: {
  readonly offer: Revision["available_commands"][number] & {
    readonly command: Exclude<RevisionCommand, OfferedElsewhere>;
  };
  readonly revision: Revision;
  readonly name: string;
  readonly names: Readonly<Record<string, string>>;
}) {
  const t = useTranslations();
  if (offer.command === "mark") {
    return <MarkCommand offer={offer} revision={revision} names={names} />;
  }
  if (offer.command === "abandon") {
    return (
      <AbandonCommand
        offer={offer}
        revision={{ projectId: revision.project_id, revisionId: revision.revision_id, name }}
        names={names}
      />
    );
  }
  if (offer.command === "create_structure") {
    return (
      <PrepareAmendmentCommand
        offer={offer}
        revision={{ projectId: revision.project_id, revisionId: revision.revision_id, name }}
        names={names}
      />
    );
  }
  return (
    <Command
      offer={offer}
      label={t(`enums.RevisionCommand.${offer.command}`)}
      help={t(`commands.revision.${offer.command}.help`)}
      icon={commandIcon(REVISION_COMMAND_ICONS[offer.command])}
      names={names}
      subject={name}
    />
  );
}

/**
 * The commands of a revision the caller may exercise, its exports and those its screens offer left
 * out; and, on the screen of the revisions, which gives its project, the opening of the current
 * revision the project lists, first — the revision being none, it is the only one.
 */
export function RevisionCommands({
  revision,
  project,
}: {
  readonly revision: Revision | undefined;
  readonly project?: Project | undefined;
}) {
  const t = useTranslations();
  const create =
    project === undefined ? undefined : findOffer(project.available_commands, "create_revision");
  const name = revision?.version_name ?? t("contextBanner.currentRevision");
  const names = {
    ...(project === undefined ? {} : { [project.project_id]: project.label }),
    ...(revision === undefined ? {} : { [revision.revision_id]: name }),
  };
  const commands =
    revision?.available_commands.flatMap((offer) =>
      isListed(offer.command) ? [{ ...offer, command: offer.command }] : [],
    ) ?? [];
  return (
    <CommandList>
      {[
        ...(project === undefined || create === undefined
          ? []
          : [
              <li key={`${project.project_id}:create_revision`}>
                <CreateRevisionCommand
                  offer={create}
                  projectId={project.project_id}
                  names={names}
                />
              </li>,
            ]),
        ...(revision === undefined
          ? []
          : commands.map((offer) => (
              <li key={`${revision.revision_id}:${offer.command}`}>
                <RevisionCommandItem offer={offer} revision={revision} name={name} names={names} />
              </li>
            ))),
      ]}
    </CommandList>
  );
}
