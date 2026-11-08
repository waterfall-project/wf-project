// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The export of the image of the task tree (FBS-4.3.5, WF-PLA-0120), asked from the screen of the
 * tree itself, at the level it shows: the command `export_task_tree_image` of the revision read,
 * as the server lists it — absent when the caller may not exercise it, unavailable with the
 * conditions it lacks. The API gives the hand back at once with a background task (WF-ARC-0090),
 * handed to the tracker of the shell with the request, which runs it again if it fails; the image,
 * drawn by the worker and not kept, is downloaded from the tracker once the task has succeeded. An
 * image beyond one hundred million pixels fails the task, and the tracker tells it
 * (`TASK_TREE_IMAGE_TOO_LARGE`): the user then chooses a shallower level. A refusal of the request
 * is told under the command (`OutcomeNotice`).
 */
"use client";

import { useTranslations } from "next-intl";

import { type ExportRequest, requestFileExport } from "@/api/actions/exchanges";
import { Command } from "@/components/commands/command";
import { commandIcon, REVISION_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { useTrackTask } from "@/components/tasks/task-tracker";

/** What the export reads: the project, the revision, the level shown and the offer of the command. */
export interface TaskTreeExportProps {
  readonly projectId: string;
  readonly revisionId: string;
  /** The level the tree shows; the image stops there, and the first at least. */
  readonly depth: number;
  readonly offer: CommandOffer | undefined;
}

/** Ask for the image of the tree at the level shown, and hand its task over to the tracker. */
export function TaskTreeExport({ projectId, revisionId, depth, offer }: TaskTreeExportProps) {
  const t = useTranslations();
  const track = useTrackTask();
  const subject = t("enums.ExportKind.task_tree_image");
  const action = async () => {
    const request: ExportRequest = {
      kind: "task_tree_image",
      revision_id: revisionId,
      depth: Math.max(1, depth),
    };
    const command = () => requestFileExport(projectId, request);
    const result = await command();
    if (result.kind === "done") {
      track(result.data, { command, subject });
    }
    return result;
  };
  return (
    <Command
      offer={offer}
      label={t("enums.RevisionCommand.export_task_tree_image")}
      help={t("commands.revision.export_task_tree_image.help")}
      icon={commandIcon(REVISION_COMMAND_ICONS.export_task_tree_image)}
      action={action}
      subject={subject}
    />
  );
}
