// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of a project and of a revision, in the order the server lists them
 * (`available_commands`): only those the caller may exercise, each available or naming what it
 * lacks (WF-IHM-0090). A marked revision offers no command of modification: the server
 * lists each unavailable, lacking a draft revision (WF-IHM-0020).
 *
 * The marking of a revision is wired: it opens the entry of its version name, and hands the
 * background task it starts to the tracker of the shell (`MarkCommand`). The other commands
 * come with the lots of their screens — the exits of the lifecycle, the structures —, which
 * hand each command its server action; until then a command is shown, and pressing it does
 * nothing.
 */
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { Revision } from "@/components/context/read-only";
import type { Project } from "@/components/context/reading";

import { Command } from "./command";
import { commandIcon, PROJECT_COMMAND_ICONS, REVISION_COMMAND_ICONS } from "./icons";
import { MarkCommand } from "./mark-command";

/** A list of commands, named for what it is; nothing when the caller may exercise none. */
function CommandList({ children }: { readonly children: readonly ReactNode[] }) {
  const t = useTranslations("commands");
  return children.length === 0 ? null : (
    <section aria-label={t("label")}>
      <ul className="flex flex-wrap items-start gap-2">{children}</ul>
    </section>
  );
}

/** The commands of a project the caller may exercise. */
export function ProjectCommands({ project }: { readonly project: Project }) {
  const t = useTranslations("enums.ProjectCommand");
  const names = { [project.project_id]: project.label };
  return (
    <CommandList>
      {project.available_commands.map((offer) => (
        // Keyed by the project too: the outcome of a command never outlives its project.
        <li key={`${project.project_id}:${offer.command}`}>
          <Command
            offer={offer}
            label={t(offer.command)}
            icon={commandIcon(PROJECT_COMMAND_ICONS[offer.command])}
            names={names}
          />
        </li>
      ))}
    </CommandList>
  );
}

/** The commands of a revision the caller may exercise. */
export function RevisionCommands({ revision }: { readonly revision: Revision }) {
  const t = useTranslations();
  const names = {
    [revision.revision_id]: revision.version_name ?? t("contextBanner.currentRevision"),
  };
  return (
    <CommandList>
      {revision.available_commands.map((offer) => (
        <li key={`${revision.revision_id}:${offer.command}`}>
          {offer.command === "mark" ? (
            <MarkCommand offer={offer} revision={revision} names={names} />
          ) : (
            <Command
              offer={offer}
              label={t(`enums.RevisionCommand.${offer.command}`)}
              icon={commandIcon(REVISION_COMMAND_ICONS[offer.command])}
              names={names}
            />
          )}
        </li>
      ))}
    </CommandList>
  );
}
